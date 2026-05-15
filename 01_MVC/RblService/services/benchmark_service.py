"""
Benchmark Service - So sánh embedding models, chunking strategies, và đánh giá RAGAS.
Phục vụ Module nghiên cứu (RBL) của đồ án.
"""
import json
import os
import time
import traceback
from datetime import datetime
from services.document_processor import DocumentProcessor
from services.rag_service import RagService

# Danh sách embedding models thực nghiệm
EMBEDDING_MODELS = {
    "multilingual-e5-base": {
        "name": "intfloat/multilingual-e5-base",
        "display": "Multilingual E5 Base",
        "type": "Free / Open-source",
        "params": "278M",
        "dim": 768
    },
    "bge-m3": {
        "name": "BAAI/bge-m3",
        "display": "BGE-M3 (BAAI)",
        "type": "Free / Open-source",
        "params": "568M",
        "dim": 1024
    }
}

# Danh sách chunking strategies
CHUNKING_STRATEGIES = [
    {"name": "small", "chunk_size": 500, "chunk_overlap": 100, "display": "Small (500/100)"},
    {"name": "medium", "chunk_size": 1000, "chunk_overlap": 200, "display": "Medium (1000/200)"},
    {"name": "large", "chunk_size": 2000, "chunk_overlap": 300, "display": "Large (2000/300)"},
]

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'benchmark_results')
TESTSET_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_set.json')


class BenchmarkService:
    def __init__(self):
        self.rag_service = RagService()
        os.makedirs(RESULTS_DIR, exist_ok=True)

    def load_test_set(self):
        """Đọc test set 50 câu hỏi + ground truth"""
        with open(TESTSET_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['test_cases']

    def compute_similarity(self, text1, text2, model_name="intfloat/multilingual-e5-base"):
        """Tính cosine similarity giữa 2 đoạn text bằng embedding"""
        try:
            embedder = self.rag_service.get_embedding_model(model_name)
            v1 = embedder.embed_query(text1)
            v2 = embedder.embed_query(text2)
            import numpy as np
            v1, v2 = np.array(v1), np.array(v2)
            sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            return float(sim)
        except:
            return 0.0

    def evaluate_retrieval(self, question, ground_truth, subject_id, model_name, top_k=3):
        """
        Đánh giá retrieval quality cho 1 câu hỏi:
        - Context Relevancy: context lấy được có liên quan đến câu hỏi không
        - Answer Similarity: câu trả lời RAG có giống ground truth không
        - Faithfulness: câu trả lời có dựa trên context không (proxy metric)
        """
        hf_model = EMBEDDING_MODELS.get(model_name, {}).get("name", model_name)
        
        # Lấy context
        context_str, sources, chunks = self.rag_service.retrieve_context(
            question, subject_id, model_name=hf_model, top_k=top_k
        )
        
        if not context_str:
            return {
                "context_relevancy": 0.0,
                "answer_similarity": 0.0,
                "faithfulness": 0.0,
                "context": "",
                "answer": "Không tìm thấy context",
                "sources": [],
                "has_context": False
            }
        
        # Tính Context Relevancy (cosine sim giữa question và context)
        context_relevancy = self.compute_similarity(question, context_str[:500], hf_model)
        
        # Gọi LLM để trả lời
        result = self.rag_service.generate_answer(question, subject_id, model_name=hf_model)
        answer = result.get("answer", "")
        
        # Tính Answer Similarity (cosine sim giữa answer và ground truth)
        answer_similarity = self.compute_similarity(answer, ground_truth, hf_model)
        
        # Tính Faithfulness proxy (cosine sim giữa answer và context)
        faithfulness = self.compute_similarity(answer, context_str[:500], hf_model)
        
        return {
            "context_relevancy": round(context_relevancy, 4),
            "answer_similarity": round(answer_similarity, 4),
            "faithfulness": round(faithfulness, 4),
            "context": context_str[:300],
            "answer": answer[:500],
            "sources": sources,
            "has_context": True
        }

    def run_embedding_benchmark(self, subject_id, max_questions=10):
        """
        Benchmark so sánh các Embedding Models.
        Chạy N câu hỏi từ test set với mỗi model, tính metrics trung bình.
        """
        test_cases = self.load_test_set()[:max_questions]
        results = {}
        
        for model_key, model_info in EMBEDDING_MODELS.items():
            print(f"\n{'='*60}")
            print(f"Benchmarking model: {model_info['display']}")
            print(f"{'='*60}")
            
            model_results = {
                "model_name": model_info["display"],
                "model_key": model_key,
                "hf_name": model_info["name"],
                "type": model_info["type"],
                "params": model_info["params"],
                "dim": model_info["dim"],
                "scores": [],
                "avg_context_relevancy": 0,
                "avg_answer_similarity": 0,
                "avg_faithfulness": 0,
                "total_time": 0,
                "questions_evaluated": 0
            }
            
            start_time = time.time()
            
            for i, tc in enumerate(test_cases):
                try:
                    print(f"  [{i+1}/{len(test_cases)}] {tc['question'][:50]}...")
                    score = self.evaluate_retrieval(
                        tc['question'], tc['ground_truth'], subject_id, model_key
                    )
                    score['question'] = tc['question']
                    score['ground_truth'] = tc['ground_truth']
                    model_results['scores'].append(score)
                except Exception as e:
                    print(f"  Error: {e}")
                    traceback.print_exc()
            
            elapsed = time.time() - start_time
            model_results['total_time'] = round(elapsed, 2)
            
            if model_results['scores']:
                n = len(model_results['scores'])
                model_results['questions_evaluated'] = n
                model_results['avg_context_relevancy'] = round(
                    sum(s['context_relevancy'] for s in model_results['scores']) / n, 4
                )
                model_results['avg_answer_similarity'] = round(
                    sum(s['answer_similarity'] for s in model_results['scores']) / n, 4
                )
                model_results['avg_faithfulness'] = round(
                    sum(s['faithfulness'] for s in model_results['scores']) / n, 4
                )
            
            results[model_key] = model_results
            print(f"  Done in {elapsed:.1f}s | CtxRel={model_results['avg_context_relevancy']:.4f} | AnsSim={model_results['avg_answer_similarity']:.4f} | Faith={model_results['avg_faithfulness']:.4f}")
        
        # Lưu kết quả
        output = {
            "benchmark_type": "embedding_models",
            "timestamp": datetime.now().isoformat(),
            "subject_id": subject_id,
            "max_questions": max_questions,
            "results": results
        }
        path = os.path.join(RESULTS_DIR, "embedding_benchmark.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output

    def run_chunking_benchmark(self, subject_id, file_path, max_questions=10):
        """
        Benchmark so sánh các Chunking Strategies.
        Re-index cùng 1 file với các chunk_size khác nhau, rồi đánh giá.
        """
        test_cases = self.load_test_set()[:max_questions]
        results = {}
        
        for strategy in CHUNKING_STRATEGIES:
            print(f"\n{'='*60}")
            print(f"Chunking strategy: {strategy['display']}")
            print(f"{'='*60}")
            
            # Re-process document with different chunking
            dp = DocumentProcessor(
                chunk_size=strategy['chunk_size'],
                chunk_overlap=strategy['chunk_overlap']
            )
            
            strat_results = {
                "strategy_name": strategy['display'],
                "chunk_size": strategy['chunk_size'],
                "chunk_overlap": strategy['chunk_overlap'],
                "num_chunks": 0,
                "scores": [],
                "avg_context_relevancy": 0,
                "avg_answer_similarity": 0,
                "avg_faithfulness": 0,
                "total_time": 0
            }
            
            if file_path and os.path.exists(file_path):
                try:
                    chunks = dp.process_file(file_path)
                    strat_results['num_chunks'] = len(chunks)
                    print(f"  Generated {len(chunks)} chunks")
                    
                    # Index vào collection riêng
                    temp_collection_name = f"benchmark_chunk_{strategy['name']}"
                    try:
                        self.rag_service.chroma_client.delete_collection(temp_collection_name)
                    except:
                        pass
                    
                    # Dùng collection chính vì chỉ demo
                    self.rag_service.embed_and_store(
                        chunks, subject_id, f"benchmark_{strategy['name']}", f"bench_{strategy['name']}"
                    )
                except Exception as e:
                    print(f"  Chunking error: {e}")
            
            start_time = time.time()
            for i, tc in enumerate(test_cases):
                try:
                    print(f"  [{i+1}/{len(test_cases)}] {tc['question'][:50]}...")
                    score = self.evaluate_retrieval(
                        tc['question'], tc['ground_truth'], subject_id, "multilingual-e5-base"
                    )
                    score['question'] = tc['question']
                    score['ground_truth'] = tc['ground_truth']
                    strat_results['scores'].append(score)
                except Exception as e:
                    print(f"  Error: {e}")
            
            elapsed = time.time() - start_time
            strat_results['total_time'] = round(elapsed, 2)
            
            if strat_results['scores']:
                n = len(strat_results['scores'])
                strat_results['avg_context_relevancy'] = round(
                    sum(s['context_relevancy'] for s in strat_results['scores']) / n, 4
                )
                strat_results['avg_answer_similarity'] = round(
                    sum(s['answer_similarity'] for s in strat_results['scores']) / n, 4
                )
                strat_results['avg_faithfulness'] = round(
                    sum(s['faithfulness'] for s in strat_results['scores']) / n, 4
                )
            
            results[strategy['name']] = strat_results
        
        output = {
            "benchmark_type": "chunking_strategies",
            "timestamp": datetime.now().isoformat(),
            "subject_id": subject_id,
            "results": results
        }
        path = os.path.join(RESULTS_DIR, "chunking_benchmark.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output

    def get_latest_results(self):
        """Đọc kết quả benchmark gần nhất"""
        results = {}
        for fname in ['embedding_benchmark.json', 'chunking_benchmark.json']:
            path = os.path.join(RESULTS_DIR, fname)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    results[fname.replace('.json', '')] = json.load(f)
        return results
