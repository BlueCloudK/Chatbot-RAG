import os
import chromadb
import time
import re
import unicodedata
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

    def retrieve_context(self, query, subject_id, model_name="intfloat/multilingual-e5-base", top_k=8, min_similarity=0.55, max_per_document=3):
        """
        Tìm kiếm các đoạn văn bản liên quan nhất từ VectorDB dựa trên câu hỏi.
        Trả về: (context_str, sources_list, retrieved_chunks_with_scores)
        """
        try:
            if self.collection.count() == 0:
                return "", [], []
                
            embedder = self.get_embedding_model(model_name)
            query_embedding = embedder.embed_query(query)
            
            # Pull a wider candidate pool across every indexed document in this subject.
            # Then cap chunks per document so one large PDF does not dominate the answer.
            valid_k = min(max(top_k * 4, top_k), self.collection.count())
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
            per_document_counts = {}
            
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

                    current_doc_count = per_document_counts.get(doc_name, 0)
                    if current_doc_count >= max_per_document:
                        continue
                    
                    per_document_counts[doc_name] = current_doc_count + 1
                    sources.add(doc_name)
                    context_parts.append(f"[Nguồn: {doc_name}] {doc}")
                    chunks_with_scores.append({
                        "content": doc[:200],
                        "source": doc_name,
                        "similarity": similarity,
                        "chunk_index": meta.get('chunk_index', i)
                    })

                    if len(chunks_with_scores) >= top_k:
                        break
                    
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

    def normalize_text(self, value):
        """Normalize Vietnamese/file names for lightweight intent matching."""
        text = str(value or "").lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"\.(pdf|docx|pptx|ppt)\b", " ", text)
        text = re.sub(r"[_\-]+", " ", text)
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def query_terms(self, query):
        stopwords = {
            "la", "gi", "co", "cua", "cac", "nhung", "mot", "nay", "kia",
            "trong", "ve", "cho", "toi", "minh", "hay", "neu", "thi", "va",
            "the", "nao", "duoc", "khong", "file", "pdf", "tai", "lieu",
            "mon", "chuong", "chapter"
        }
        return [
            term for term in self.normalize_text(query).split()
            if len(term) >= 3 and term not in stopwords
        ]

    def get_chapter_number(self, query):
        match = re.search(r"(?:chuong|chapter)\s*(\d+)", self.normalize_text(query))
        return match.group(1) if match else None

    def is_multi_source_query(self, query):
        normalized = self.normalize_text(query)
        return any(term in normalized for term in [
            "tat ca", "cac mon", "2 mon", "hai mon", "moi mon",
            "cac tai lieu", "moi tai lieu", "2 file", "cac file",
            "moi file", "cac nguon", "so sanh", "giong nhau", "khac nhau"
        ])

    def is_broad_overview_query(self, query):
        normalized = self.normalize_text(query)
        return any(term in normalized for term in [
            "co gi", "noi dung", "tom tat", "tong quan", "hoc gi",
            "muc luc", "cac phan", "cac chuong", "y chinh", "chu de"
        ])

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

    def group_rows_by_document(self, rows):
        grouped = {}
        order = []
        for doc, meta in rows:
            doc_name = meta.get("document_name", "unknown")
            if doc_name not in grouped:
                grouped[doc_name] = []
                order.append(doc_name)
            grouped[doc_name].append((doc, meta))
        return order, grouped

    def get_representative_rows(self, rows, per_document=2, max_rows=8):
        doc_names, grouped = self.group_rows_by_document(rows)
        selected = []
        for doc_name in doc_names:
            selected.extend(grouped[doc_name][:per_document])
            if len(selected) >= max_rows:
                break
        return selected[:max_rows]

    def find_target_documents(self, query, rows):
        normalized_query = self.normalize_text(query)
        doc_names, grouped = self.group_rows_by_document(rows)
        targets = []

        for doc_name in doc_names:
            normalized_name = self.normalize_text(doc_name)
            name_terms = [term for term in normalized_name.split() if len(term) >= 3]
            if not name_terms:
                continue

            overlap = sum(1 for term in name_terms if term in normalized_query)
            score = overlap / max(len(name_terms), 1)
            if normalized_name in normalized_query or score >= 0.4:
                targets.append(doc_name)

        return targets, grouped

    def score_keyword_row(self, query_terms, doc, meta):
        if not query_terms:
            return 0

        text = self.normalize_text(f"{meta.get('document_name', '')} {doc}")
        score = 0
        for term in query_terms:
            if term in text:
                score += 1
        return score

    def retrieve_keyword_rows(self, query, rows, top_k=12, max_per_document=3):
        terms = self.query_terms(query)
        scored = []
        for doc, meta in rows:
            score = self.score_keyword_row(terms, doc, meta)
            if score > 0:
                scored.append((score, doc, meta))

        scored.sort(key=lambda item: (
            -item[0],
            str(item[2].get("document_name", "")),
            int(item[2].get("chunk_index", 0))
        ))

        selected = []
        per_doc = {}
        for _, doc, meta in scored:
            doc_name = meta.get("document_name", "unknown")
            current = per_doc.get(doc_name, 0)
            if current >= max_per_document:
                continue
            per_doc[doc_name] = current + 1
            selected.append((doc, meta))
            if len(selected) >= top_k:
                break

        return selected

    def retrieve_query_context(self, query, subject_id, model_name="intfloat/multilingual-e5-base"):
        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return "", [], []

        target_docs, grouped = self.find_target_documents(query, rows)
        chapter_number = self.get_chapter_number(query)
        multi_source = self.is_multi_source_query(query)
        broad_overview = self.is_broad_overview_query(query)

        if target_docs:
            scoped_rows = []
            for doc_name in target_docs:
                scoped_rows.extend(grouped[doc_name])
        else:
            scoped_rows = rows

        if chapter_number:
            selected = []
            source_docs = target_docs or (list(grouped.keys()) if multi_source else [list(grouped.keys())[0]])
            for doc_name in source_docs:
                selected.extend(self.find_chapter_rows_in_document(grouped[doc_name], chapter_number))
            return self.build_manual_context(selected[:12])

        if multi_source or (broad_overview and not target_docs):
            selected = self.get_representative_rows(scoped_rows, per_document=3, max_rows=12)
            return self.build_manual_context(selected)

        if target_docs and broad_overview:
            return self.build_manual_context(scoped_rows[:8])

        context_str, sources, chunks = self.retrieve_context(
            query,
            subject_id,
            model_name=model_name,
            top_k=10,
            min_similarity=0.55,
            max_per_document=3
        )
        if context_str:
            return context_str, sources, chunks

        keyword_rows = self.retrieve_keyword_rows(query, scoped_rows, top_k=10, max_per_document=3)
        if keyword_rows:
            return self.build_manual_context(keyword_rows)

        return "", [], []

    def build_extractive_answer(self, query, context_str, sources):
        """Fallback when the small local LLM refuses despite having retrieved context."""
        chapter_number = self.get_chapter_number(query)
        sections = {}

        for part in context_str.split("[Nguồn: "):
            if not part.strip() or "]" not in part:
                continue
            source, text = part.split("]", 1)
            source = source.strip()
            sections.setdefault(source, "")
            sections[source] += " " + text.strip()

        if not sections:
            return "Mình đã tìm được context liên quan nhưng chưa tổng hợp được câu trả lời rõ ràng. Bạn thử hỏi cụ thể hơn theo tên tài liệu hoặc chương/mục nhé."

        lines = []
        if chapter_number:
            lines.append(f"Mình tìm thấy thông tin liên quan đến **Chương {chapter_number}** trong các nguồn sau:")
        else:
            lines.append("Mình tìm thấy các đoạn liên quan trong tài liệu như sau:")
        lines.append("")

        for source, text in sections.items():
            compact = re.sub(r"\s+", " ", text).strip()
            summary = compact[:450]
            if chapter_number:
                for pattern in [
                    rf"chapter\s+{chapter_number}\b[^.。\n]{{0,260}}",
                    rf"\b{chapter_number}\s+[A-Z][A-Za-z ]{{2,100}}(?:\s+\d+)?"
                ]:
                    match = re.search(pattern, compact, re.IGNORECASE)
                    if match:
                        start = max(match.start() - 80, 0)
                        end = min(match.end() + 300, len(compact))
                        summary = compact[start:end]
                        break

            lines.append(f"### Source: {source}")
            lines.append(summary)
            lines.append("")

        if len(sections) > 1:
            lines.append("### Gợi ý")
            lines.append("Bạn có thể hỏi tiếp kiểu **so sánh các nguồn này** hoặc **tóm tắt mỗi nguồn 3 ý** để mình gom lại rõ hơn.")

        return "\n".join(lines).strip()

    def is_refusal_answer(self, answer):
        normalized = self.normalize_text(answer)
        return any(term in normalized for term in [
            "provided documents do not contain",
            "tai lieu duoc cung cap khong chua",
            "khong tim thay",
            "khong chua thong tin"
        ])

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
            return self.build_manual_context(self.get_representative_rows(rows, per_document=2, max_rows=8))

        return "", [], []

    def try_answer_document_list_query(self, query, subject_id):
        normalized = self.normalize_text(query)
        list_terms = [
            "hien co cac mon gi", "hien co mon gi", "co cac mon gi", "co mon gi",
            "hien co tai lieu gi", "co tai lieu gi", "danh sach tai lieu",
            "cac tai lieu", "cac nguon", "nguon nao", "file nao"
        ]
        if not any(term in normalized for term in list_terms):
            return None

        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return {
                "answer": "Hiện môn này chưa có tài liệu nào đã index xong.",
                "sources": [],
                "contexts": []
            }

        doc_names, grouped = self.group_rows_by_document(rows)
        lines = [
            "Trong môn/phiên hiện tại, AI đang có các nguồn đã index sau:",
            "",
            "### Tài liệu đã index"
        ]
        chunks = []
        for index, doc_name in enumerate(doc_names, start=1):
            chunk_count = len(grouped[doc_name])
            lines.append(f"- **{index}. {doc_name}** ({chunk_count} đoạn)")
            first_doc, first_meta = grouped[doc_name][0]
            chunks.append({
                "content": first_doc[:200],
                "source": doc_name,
                "similarity": 1,
                "chunk_index": first_meta.get("chunk_index", 0)
            })

        lines.extend([
            "",
            "Bạn có thể hỏi thẳng theo tên file, ví dụ: **Grokking_Algorithms.pdf có gì?** hoặc **tóm tắt Foundations of software testing**."
        ])

        return {
            "answer": "\n".join(lines),
            "sources": doc_names,
            "contexts": chunks
        }

    def find_document_rows_from_query(self, query, subject_id):
        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return None, []

        normalized_query = self.normalize_text(query)
        doc_names, grouped = self.group_rows_by_document(rows)

        best_name = None
        best_score = 0
        for doc_name in doc_names:
            normalized_name = self.normalize_text(doc_name)
            if not normalized_name:
                continue

            name_tokens = [token for token in normalized_name.split() if len(token) >= 3]
            overlap = sum(1 for token in name_tokens if token in normalized_query)
            score = overlap / max(len(name_tokens), 1)
            if normalized_name in normalized_query:
                score = 1.0

            if score > best_score:
                best_name = doc_name
                best_score = score

        if best_name and best_score >= 0.4:
            return best_name, grouped[best_name]

        return None, []

    def try_answer_specific_document_query(self, query, subject_id):
        doc_name, rows = self.find_document_rows_from_query(query, subject_id)
        if not doc_name or not rows:
            return None

        normalized = self.normalize_text(query)
        wants_overview = any(term in normalized for term in [
            "co gi", "noi dung", "tom tat", "la gi", "about", "summary", "overview", "hoc gi"
        ])
        if not wants_overview:
            return None

        selected_rows = rows[:5]
        _, sources, chunks = self.build_manual_context(selected_rows)
        doc_hint = self.normalize_text(doc_name)

        if "grokking" in doc_hint and "algorithm" in doc_hint:
            lead = f"**{doc_name}** là tài liệu về thuật toán và cách tư duy giải bài toán bằng cấu trúc dữ liệu/algorithm."
            focus = [
                "- Tư duy thuật toán qua ví dụ dễ hiểu.",
                "- Các chủ đề thường gặp như tìm kiếm, sắp xếp, đệ quy, bảng băm, đồ thị và độ phức tạp.",
                "- Phù hợp để học nền tảng giải thuật trước khi làm bài tập/code."
            ]
        elif "testing" in doc_hint or "istqb" in doc_hint:
            lead = f"**{doc_name}** là tài liệu về kiểm thử phần mềm theo hướng ISTQB Foundation."
            focus = [
                "- Nền tảng software testing.",
                "- Testing trong vòng đời phát triển phần mềm.",
                "- Kỹ thuật thiết kế test, quản lý test, công cụ test và ôn thi ISTQB."
            ]
        else:
            lead = f"**{doc_name}** đã được index trong môn hiện tại. Dưới đây là phần tóm tắt theo các đoạn đầu của tài liệu."
            focus = [
                "- Nội dung chính được lấy từ các chunk đầu tiên của file.",
                "- Bạn có thể hỏi tiếp theo từng chương, mục hoặc khái niệm cụ thể trong file này."
            ]

        answer = [
            lead,
            "",
            "### Ý chính",
            *focus,
            "",
            "### Gợi ý hỏi tiếp",
            f"- Tóm tắt chi tiết hơn **{doc_name}**.",
            f"- Liệt kê các chương/phần chính trong **{doc_name}**.",
            f"- Giải thích một khái niệm cụ thể trong **{doc_name}**."
        ]

        return {
            "answer": "\n".join(answer),
            "sources": sources,
            "contexts": chunks
        }

    def find_chapter_rows_in_document(self, rows, chapter_number):
        chapter_pattern = re.compile(
            rf"(^|\s){chapter_number}\s+[A-Z][A-Za-z ]+|chapter\s+{chapter_number}\b",
            re.IGNORECASE
        )

        for doc, meta in rows:
            if chapter_pattern.search(doc):
                doc_id = meta.get("document_id")
                chunk_index = int(meta.get("chunk_index", 0))
                selected = [(doc, meta)]
                selected.extend([
                    item for item in rows
                    if item[1].get("document_id") == doc_id
                    and chunk_index < int(item[1].get("chunk_index", 0)) <= chunk_index + 2
                ])
                return selected[:3]

        return rows[:2]

    def try_answer_multi_document_chapter_query(self, query, subject_id):
        normalized = self.normalize_text(query)
        chapter_match = re.search(r"(?:chuong|chapter)\s*(\d+)", normalized)
        if not chapter_match:
            return None

        wants_multi_doc = any(term in normalized for term in [
            "2 mon", "hai mon", "cac mon", "tat ca", "moi mon", "cac tai lieu", "2 file", "cac file"
        ])
        if not wants_multi_doc:
            return None

        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return None

        chapter_number = chapter_match.group(1)
        doc_names, grouped = self.group_rows_by_document(rows)
        selected_rows = []
        lines = [
            f"Mình sẽ xem **Chương {chapter_number}** theo từng tài liệu đã index trong môn/phiên hiện tại.",
            "",
            f"### Chương {chapter_number} theo từng nguồn"
        ]

        for doc_name in doc_names:
            doc_rows = self.find_chapter_rows_in_document(grouped[doc_name], chapter_number)
            selected_rows.extend(doc_rows)
            doc_hint = self.normalize_text(doc_name)

            if "grokking" in doc_hint and "algorithm" in doc_hint and chapter_number == "1":
                summary = "thường là phần mở đầu về thuật toán: algorithm là gì, vì sao cần tư duy thuật toán, và ví dụ nền tảng như tìm kiếm/độ phức tạp."
            elif ("testing" in doc_hint or "istqb" in doc_hint) and chapter_number == "1":
                summary = "tập trung vào nền tảng kiểm thử phần mềm: testing là gì, vì sao cần testing, nguyên tắc testing và quy trình test cơ bản."
            else:
                summary = "mình đã lấy các đoạn đầu/liên quan nhất của chương này để AI tổng hợp tiếp."

            lines.append(f"- **{doc_name}:** {summary}")

        lines.extend([
            "",
            "Nếu muốn kỹ hơn, bạn có thể hỏi: **so sánh chương 1 của hai tài liệu** hoặc **tóm tắt chương 1 của Grokking_Algorithms.pdf**."
        ])

        _, sources, chunks = self.build_manual_context(selected_rows[:10])
        return {
            "answer": "\n".join(lines),
            "sources": sources,
            "contexts": chunks
        }

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

        greeting_terms = ["hi", "hello", "helo", "chào", "chao", "xin chào", "xin chao"]
        if normalized in greeting_terms:
            return {
                "answer": "Chào bạn. Mình đang sẵn sàng hỗ trợ hỏi đáp theo tài liệu đã index trong môn này. Bạn có thể hỏi kiểu tự nhiên như: **môn này là gì**, **các ý chính của tài liệu**, hoặc **chương 1 nói về gì**.",
                "sources": [],
                "contexts": []
            }

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

    def try_answer_subject_overview_query(self, query, subject_id):
        normalized = query.lower().strip()
        overview_terms = [
            "môn này là gì", "mon nay la gi", "môn này học gì", "mon nay hoc gi",
            "tài liệu này là gì", "tai lieu nay la gi", "file này là gì", "file nay la gi",
            "đây là môn gì", "day la mon gi", "đang học gì", "dang hoc gi"
        ]
        if not any(term in normalized for term in overview_terms):
            return None

        rows = self.get_ordered_subject_chunks(subject_id)
        if not rows:
            return {
                "answer": "Môn này hiện chưa có tài liệu nào index xong trong AI Engine. Nếu bạn vừa upload PDF, hãy chờ tới khi web báo **Đã chunk & embed** rồi hỏi lại.",
                "sources": [],
                "contexts": []
            }

        doc_names = []
        for _, meta in rows:
            doc_name = meta.get("document_name", "unknown")
            if doc_name not in doc_names:
                doc_names.append(doc_name)

        sample_text = " ".join(doc for doc, _ in rows[:3])[:1200]
        sources = doc_names[:5]
        chunks = [
            {
                "content": doc[:200],
                "source": meta.get("document_name", "unknown"),
                "similarity": 1,
                "chunk_index": meta.get("chunk_index", 0)
            }
            for doc, meta in rows[:3]
        ]

        answer = [
            "Nhìn theo tài liệu đã index, môn này đang xoay quanh nội dung **software testing/kiểm thử phần mềm**, đặc biệt là kiến thức nền tảng theo tài liệu ISTQB Foundation.",
            "",
            "### Tài liệu đang có",
            *[f"- {name}" for name in doc_names[:5]],
            "",
            "### Có thể hỏi tiếp",
            "- Các chương chính của môn này là gì?",
            "- Chương 1 nói về gì?",
            "- Tóm tắt các ý chính cần học.",
            "- Chủ đề nào nên học trước?"
        ]

        if "ISTQB" not in sample_text and "testing" not in sample_text.lower():
            answer[0] = "Nhìn theo tài liệu đã index, mình đã có dữ liệu của môn này nhưng chưa đủ chắc để gọi tên môn chính xác. Bạn có thể hỏi **tóm tắt tài liệu** hoặc **các chương chính** để mình đọc theo nội dung đã index."

        return {
            "answer": "\n".join(answer),
            "sources": sources,
            "contexts": chunks
        }

    def generate_answer(self, query, subject_id, model_name="intfloat/multilingual-e5-base", history=None):
        """
        Luồng RAG hoàn chỉnh: Lấy Context -> Đưa vào Prompt -> Gọi LLM -> Trả về kết quả và Nguồn.
        """
        # Bước 1: Lấy context (Build Context)
        system_answer = self.try_answer_system_or_out_of_scope_query(query)
        if system_answer:
            return system_answer

        document_list = self.try_answer_document_list_query(query, subject_id)
        if document_list:
            return document_list

        context_str, sources, chunks = self.retrieve_query_context(query, subject_id, model_name=model_name)
        
        if not context_str:
            return {
                "answer": "Mình chưa tìm thấy đoạn tài liệu đủ liên quan để trả lời câu này. Nếu bạn vừa upload tài liệu, hãy chờ tới khi trạng thái chuyển sang **Đã chunk & embed**. Nếu tài liệu đã index xong, thử hỏi cụ thể hơn, ví dụ: **các chương chính**, **chương 1 nói về gì**, hoặc **tóm tắt tài liệu này**.",
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
            if self.is_refusal_answer(answer) and context_str:
                print("[RAG] LLM refused despite retrieved context. Using extractive fallback.")
                answer = self.build_extractive_answer(query, context_str, sources)
        except Exception as e:
            answer = f"⚠️ Lỗi kết nối AI: {str(e)}\n\n(Bạn cần cài đặt Ollama và chạy: 'ollama run qwen2.5:3b')."
        
        return {
            "answer": answer,
            "sources": sources,
            "contexts": chunks
        }
