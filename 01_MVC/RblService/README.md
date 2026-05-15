# EduChatbot RBL Service

Project rieng cho phan nghien cuu RBL:

- Benchmark embedding models.
- Benchmark chunking strategies.
- Xem bang ket qua RAGAS/proxy metrics.
- Xem test set 50 cau hoi + ground truth.

## Chay rieng

```powershell
cd D:\Project\PRN222\RblService
pip install -r requirements.txt
python -B -m uvicorn main:app --host 127.0.0.1 --port 8010
```

Dashboard:

```text
http://127.0.0.1:8010/
```

Luu y: project nay tach khoi `EduChatbot.Web` va `AiService`. Chatbot chinh khong phu thuoc vao RBL.
