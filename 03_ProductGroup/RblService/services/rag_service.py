import os
import chromadb
import time
import re
from jinja2 import Template
from langchain_huggingface import HuggingFaceEmbeddings

class RagService:
    def __init__(self):
        # Khởi tạo kết nối Vector Database ChromaDB (lưu tại local thư mục chroma_db)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="edu_documents",
            metadata={"hnsw:space": "cosine"}  # Dùng cosine similarity thay vì L2
        )
        
        # Cache các embedding models (phục vụ Benchmark Override Model)
        self.embeddings = {}
        
        # Cache LLM instance (tránh khởi tạo lại mỗi lần gọi)
        self._llm = None
        
        # Load prompt template (Jinja2)
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'system_prompt.jinja')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = Template(f.read())

    def get_embedding_model(self, model_name="intfloat/multilingual-e5-base"):
        """Lazy load Embedding Model để tối ưu bộ nhớ"""
        if model_name not in self.embeddings:
            print(f"Loading embedding model: {model_name}...")
            self.embeddings[model_name] = HuggingFaceEmbeddings(model_name=model_name)
        return self.embeddings[model_name]

    def get_llm(self):
        """Lazy load & cache LLM instance"""
        if self._llm is None:
            from langchain_ollama import OllamaLLM
            # hiện trên máy có qwen2:1.5b và qwen2.5:3b
            self._llm = OllamaLLM(model="qwen2.5:3b", temperature=0.3)
        return self._llm

    def embed_and_store(self, chunks, subject_id, document_name, document_id, model_name="intfloat/multilingual-e5-base"):
        """
        Nhận mảng văn bản (chunks), thực hiện nhúng (embedding) và lưu vào VectorDB.
        Nếu document_id đã tồn tại, xóa cũ rồi thêm mới (upsert logic).
        """
        embedder = self.get_embedding_model(model_name)
        
        # Xóa chunks cũ nếu document đã tồn tại (tránh trùng lặp khi re-upload)
        try:
            existing = self.collection.get(where={"document_id": document_id})
            if existing and existing['ids']:
                self.collection.delete(ids=existing['ids'])
                print(f"  Deleted {len(existing['ids'])} old chunks for: {document_id}")
        except Exception:
            pass
        
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Bỏ qua chunks quá ngắn (ít thông tin)
            if len(chunk.strip()) < 20:
                continue
            documents.append(chunk)
            chunk_id = f"{document_id}_chunk{i}"
            ids.append(chunk_id)
            metadatas.append({
                "subject_id": subject_id,
                "document_name": document_name,
                "document_id": document_id,
                "chunk_index": i,
                "chunk_length": len(chunk)
            })

        if not documents:
            return 0

        # Gọi model để nhúng list văn bản thành các vector số
        print(f"  Embedding {len(documents)} chunks...")
        start = time.time()
        embeddings_list = []
        batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
        total = len(documents)

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_embeddings = embedder.embed_documents(documents[batch_start:batch_end])
            embeddings_list.extend(batch_embeddings)
            elapsed_batch = time.time() - start
            print(f"  Embedded {batch_end}/{total} chunks ({batch_end * 100 // total}%) in {elapsed_batch:.1f}s", flush=True)

        elapsed = time.time() - start
        print(f"  Embedding done in {elapsed:.1f}s")
        
        # Lưu vào CSDL vector
        self.collection.add(
            embeddings=embeddings_list,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return len(documents)

    def delete_document(self, document_id):
        """Delete all vector chunks that belong to one indexed document."""
        try:
            existing = self.collection.get(where={"document_id": document_id})
            ids = existing.get("ids", []) if existing else []
            if ids:
                self.collection.delete(ids=ids)
            return len(ids)
        except Exception as e:
            print(f"Error deleting document from ChromaDB: {e}")
            raise

    def retrieve_context(self, query, subject_id, model_name="intfloat/multilingual-e5-base", top_k=5, min_similarity=0.8):
        """
        Tìm kiếm các đoạn văn bản liên quan nhất từ VectorDB dựa trên câu hỏi.
        Trả về: (context_str, sources_list, retrieved_chunks_with_scores)
        """
        try:
            if self.collection.count() == 0:
                return "", [], []
                
            embedder = self.get_embedding_model(model_name)
            query_embedding = embedder.embed_query(query)
            
            # Tính toán n_results hợp lý
            valid_k = min(top_k, self.collection.count())
            if valid_k <= 0:
                return "", [], []

            # Query ChromaDB (chỉ lấy trong phạm vi môn học - subject_id)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=valid_k,
                where={"subject_id": subject_id},
                include=["documents", "metadatas", "distances"]
            )
            
            context_parts = []
            sources = set()
            chunks_with_scores = []
            
            if results and results.get('documents') and len(results['documents']) > 0 and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    meta = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    doc_name = meta.get('document_name', 'unknown')
                    doc_id = meta.get('document_id', 'unknown')
                    
                    # Cosine distance → similarity (1 - distance)
                    similarity = round(1 - distance, 4) if distance else 0
                    if similarity < min_similarity:
                        continue
                    
                    sources.add(doc_name)
                    context_parts.append(f"[Nguồn: {doc_name}] {doc}")
                    chunks_with_scores.append({
                        "content": doc[:200],
                        "source": doc_name,
                        "similarity": similarity,
                        "chunk_index": meta.get('chunk_index', i)
                    })
                    
            context_str = "\n\n".join(context_parts)
            return context_str, list(sources), chunks_with_scores
        except Exception as e:
            print(f"Error retrieving from ChromaDB: {e}")
            import traceback
            traceback.print_exc()
            return "", [], []

    def format_history(self, history, max_messages=6):
        """Format a compact conversation window for follow-up questions."""
        if not history:
            return ""

        lines = []
        for item in history[-max_messages:]:
            role = item.get("role", "User")
            content = item.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content[:800]}")
        return "\n".join(lines)

    def get_ordered_subject_chunks(self, subject_id):
        """Return indexed chunks for a subject ordered by document and chunk index."""
        try:
            results = self.collection.get(
                where={"subject_id": subject_id},
                include=["documents", "metadatas"]
            )
            rows = []
            for doc, meta in zip(results.get("documents", []), results.get("metadatas", [])):
                rows.append((doc, meta))

            return sorted(rows, key=lambda item: (
                str(item[1].get("document_id", "")),
                int(item[1].get("chunk_index", 0))
            ))
        except Exception as e:
            print(f"Error reading ordered chunks: {e}")
            return []

    def build_manual_context(self, rows):
        context_parts = []
        sources = set()
        chunks_with_scores = []

        for doc, meta in rows:
            doc_name = meta.get("document_name", "unknown")
            sources.add(doc_name)
            context_parts.append(f"[Nguồn: {doc_name}] {doc}")
            chunks_with_scores.append({
                "content": doc[:200],
                "source": doc_name,
                "similarity": 1,
                "chunk_index": meta.get("chunk_index", 0)
            })

        return "\n\n".join(context_parts), list(sources), chunks_with_scores

    def retrieve_outline_context(self, query, subject_id):
        """Handle outline questions like 'tai lieu co gi' or 'chuong 1 co gi'."""
        normalized = query.lower().strip()
        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return "", [], []

        chapter_match = re.search(r"(?:chương|chuong|chapter)\s*(\d+)", normalized)
        if chapter_match:
            chapter_number = chapter_match.group(1)
            chapter_pattern = re.compile(
                rf"(^|\s){chapter_number}\s+[A-Z][A-Za-z ]+|chapter\s+{chapter_number}\b",
                re.IGNORECASE
            )
            selected = []
            for doc, meta in rows:
                if chapter_pattern.search(doc):
                    selected.append((doc, meta))
                    doc_id = meta.get("document_id")
                    chunk_index = int(meta.get("chunk_index", 0))
                    selected.extend([
                        item for item in rows
                        if item[1].get("document_id") == doc_id
                        and chunk_index < int(item[1].get("chunk_index", 0)) <= chunk_index + 2
                    ])
                    break

            if selected:
                return self.build_manual_context(selected[:4])

        overview_terms = [
            "có gì", "co gi", "chứa gì", "chua gi", "nội dung", "noi dung",
            "tóm tắt", "tom tat", "mục lục", "muc luc", "overview", "summary",
            "contents", "contain", "about", "chương", "chuong", "chapter",
            "quan trọng", "quan trong", "important"
        ]
        if any(term in normalized for term in overview_terms):
            return self.build_manual_context(rows[:3])

        return "", [], []

    def extract_chapter_outline(self, subject_id):
        """Extract top-level chapter titles from table-of-contents chunks."""
        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return [], [], []

        chapters = []
        seen = set()
        selected_rows = rows[:3]
        toc_text = " ".join(doc for doc, _ in selected_rows)
        for match in re.finditer(r"(?<![\d.])(\d{1,2})\s+([A-Z][A-Za-z]+(?: [A-Za-z][A-Za-z]+){0,7})\s+\d+\b", toc_text):
            number = int(match.group(1))
            title = " ".join(match.group(2).split())
            title_lower = title.lower()
            if number in seen or number > 20:
                continue
            if title_lower.startswith(("why ", "what ", "sample ", "exercise ")):
                continue
            if "chapter review" in title_lower:
                continue
            seen.add(number)
            chapters.append((number, title))

        chapters.sort(key=lambda item: item[0])
        _, sources, chunks = self.build_manual_context(selected_rows)
        return chapters, sources, chunks

    def try_answer_outline_query(self, query, subject_id):
        normalized = query.lower().strip()
        wants_chapters = any(term in normalized for term in [
            "các chương", "cac chuong", "chương quan trọng", "chuong quan trong",
            "chapter list", "chapters", "mục lục", "muc luc",
            "ý chính", "y chinh", "main ideas", "key ideas"
        ])
        if not wants_chapters:
            return None

        chapters, sources, chunks = self.extract_chapter_outline(subject_id)
        if not chapters:
            return None

        chapter_notes = {
            1: "Nền tảng của kiểm thử: vì sao cần testing, testing là gì, các nguyên tắc, quy trình test cơ bản và yếu tố tâm lý khi kiểm thử.",
            2: "Testing trong vòng đời phát triển phần mềm: mô hình phát triển, các mức test, loại test và maintenance testing.",
            3: "Kỹ thuật tĩnh: review tài liệu/code, quy trình review và phân tích tĩnh bằng công cụ.",
            4: "Thiết kế test case: cách xác định điều kiện test, thiết kế test case và các nhóm kỹ thuật như black-box/specification-based.",
            5: "Quản lý kiểm thử: tổ chức test, lập kế hoạch, theo dõi/kiểm soát, quản lý rủi ro và xử lý incident.",
            6: "Công cụ hỗ trợ testing: các loại test tool, cách dùng hiệu quả và cách đưa tool vào tổ chức.",
            7: "Ôn thi ISTQB Foundation: phần tổng hợp, câu hỏi mẫu và định hướng chuẩn bị cho bài thi."
        }

        lines = [
            "Nếu nhìn theo mục lục, tài liệu này đi từ nền tảng testing đến thiết kế test, quản lý test, công cụ và ôn thi ISTQB.",
            "",
            "### Ý chính từng chương"
        ]
        for number, title in chapters:
            note = chapter_notes.get(number, f"Nội dung chính xoay quanh **{title}**.")
            lines.append(f"- **Chương {number} - {title}:** {note}")

        lines.extend([
            "",
            "### Cách học hợp lý",
            "- Học **Chương 1-2** trước để nắm testing là gì và testing nằm ở đâu trong vòng đời phần mềm.",
            "- Sau đó học **Chương 3-4** vì đây là phần kỹ thuật làm bài và thiết kế kiểm thử.",
            "- Cuối cùng học **Chương 5-7** để hiểu quản lý test, công cụ và ôn thi/chốt kiến thức."
        ])

        return {
            "answer": "\n".join(lines),
            "sources": sources,
            "contexts": chunks
        }

    def try_answer_system_or_out_of_scope_query(self, query):
        normalized = query.lower().strip()

        model_terms = ["model gì", "model gi", "mô hình gì", "mo hinh gi", "llm gì", "llm gi"]
        if any(term in normalized for term in model_terms):
            return {
                "answer": "Mình là EduChatbot AI trong web app này. Phần sinh câu trả lời đang chạy local bằng **qwen2.5:3b** qua Ollama; phần tìm tài liệu dùng embedding **intfloat/multilingual-e5-base**.",
                "sources": [],
                "contexts": []
            }

        capability_terms = ["bạn có thể làm gì", "ban co the lam gi", "làm được gì", "lam duoc gi", "giúp gì", "giup gi"]
        if any(term in normalized for term in capability_terms):
            return {
                "answer": "Mình có thể hỗ trợ hỏi đáp trong phạm vi tài liệu đã tải lên:\n\n### Mình làm được\n- Tóm tắt nội dung tài liệu.\n- Giải thích khái niệm trong tài liệu.\n- Liệt kê ý chính theo chương/phần.\n- Trích nguồn từ tài liệu đã index.\n\n### Giới hạn\n- Mình không trả lời tin tức, ngày giờ, thời tiết hoặc kiến thức ngoài tài liệu môn học.",
                "sources": [],
                "contexts": []
            }

        out_of_scope_terms = [
            "hôm nay", "hom nay", "ngày mấy", "ngay may", "thứ mấy", "thu may",
            "mấy giờ", "may gio", "thời tiết", "thoi tiet", "tin tức", "tin tuc"
        ]
        if any(term in normalized for term in out_of_scope_terms):
            return {
                "answer": "Câu hỏi này nằm ngoài phạm vi tài liệu môn học. Mình chỉ trả lời dựa trên các tài liệu đã upload và index trong môn hiện tại.",
                "sources": [],
                "contexts": []
            }

        return None

    def generate_answer(self, query, subject_id, model_name="intfloat/multilingual-e5-base", history=None):
        """
        Luồng RAG hoàn chỉnh: Lấy Context -> Đưa vào Prompt -> Gọi LLM -> Trả về kết quả và Nguồn.
        """
        # Bước 1: Lấy context (Build Context)
        system_answer = self.try_answer_system_or_out_of_scope_query(query)
        if system_answer:
            return system_answer

        direct_answer = self.try_answer_outline_query(query, subject_id)
        if direct_answer:
            return direct_answer

        context_str, sources, chunks = self.retrieve_outline_context(query, subject_id)
        if not context_str:
            context_str, sources, chunks = self.retrieve_context(query, subject_id, model_name=model_name, top_k=8)
        
        if not context_str:
            return {
                "answer": "Xin lỗi, tôi không tìm thấy tài liệu nào trong môn học này chứa thông tin để trả lời câu hỏi của bạn.",
                "sources": [],
                "contexts": []
            }

        # Bước 2: Ghép ngữ cảnh vào Jinja Prompt Template
        prompt = self.prompt_template.render(context=context_str)
        history_text = self.format_history(history or [])
        history_block = f"\n\nConversation history:\n{history_text}" if history_text else ""
        full_prompt = f"{prompt}{history_block}\n\nCâu hỏi: {query}\nTrả lời:"
        
        # Bước 3: Gọi LLM (Local bằng Ollama)
        try:
            llm = self.get_llm()
            print(f"[RAG] Query: {query[:60]}... | Sources: {len(sources)} | Chunks: {len(chunks)}")
            start = time.time()
            answer = llm.invoke(full_prompt)
            elapsed = time.time() - start
            print(f"[RAG] LLM response in {elapsed:.1f}s")
        except Exception as e:
            answer = f"⚠️ Lỗi kết nối AI: {str(e)}\n\n(Bạn cần cài đặt Ollama và chạy: 'ollama run qwen2.5:3b')."
        
        return {
            "answer": answer,
            "sources": sources,
            "contexts": chunks
        }
