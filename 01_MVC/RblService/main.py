import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from services.benchmark_service import BenchmarkService

app = FastAPI(title="EduChatbot RBL Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

benchmark_service = BenchmarkService()


class BenchmarkRequest(BaseModel):
    subject_id: int = 1
    max_questions: int = Field(default=10, ge=1, le=50)
    benchmark_type: str = "embedding"


@app.get("/")
def dashboard():
    return FileResponse("dashboard.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "EduChatbot RBL Service"}


@app.post("/api/benchmark/run")
async def run_benchmark(request: BenchmarkRequest):
    try:
        if request.benchmark_type == "embedding":
            result = benchmark_service.run_embedding_benchmark(
                request.subject_id, request.max_questions
            )
        elif request.benchmark_type == "chunking":
            result = benchmark_service.run_chunking_benchmark(
                request.subject_id, None, request.max_questions
            )
        else:
            return {"status": "error", "message": "Invalid benchmark_type. Use 'embedding' or 'chunking'."}

        return {"status": "success", "data": result}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/api/benchmark/results")
async def get_benchmark_results():
    try:
        results = benchmark_service.get_latest_results()
        return {"status": "success", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/benchmark/test-set")
async def get_test_set():
    try:
        test_cases = benchmark_service.load_test_set()
        return {"status": "success", "count": len(test_cases), "data": test_cases}
    except Exception as e:
        return {"status": "error", "message": str(e)}

