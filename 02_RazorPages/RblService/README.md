# EduChatbot RBL Service

This is the standalone research/benchmark service for the RBL module.

## Purpose

- Benchmark embedding models.
- Benchmark chunking strategies.
- Display RAGAS/proxy metric results.
- Use a 50-question test set with human-prepared ground truth.

## Run Standalone

```powershell
cd D:\Project\PRN222\02_RazorPages\RblService
pip install -r requirements.txt
python -B -m uvicorn main:app --host 127.0.0.1 --port 8010
```

Dashboard:

```text
http://127.0.0.1:8010/
```

This service is separate from the main chatbot web app and `AiService`. The chatbot does not depend on the RBL service at runtime.
