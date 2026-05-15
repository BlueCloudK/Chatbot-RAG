# EduChatbot.ProductGroup

Day la ban ProductGroup cua EduChatbot. Project nay van dung Razor Pages va giu chuc nang chatbot/tai lieu, nhung co them cac feature rieng de demo nhom.

## Solution

Mo solution:

```text
EduChatbot.Group.sln
```

Startup project:

```text
EduChatbot.ProductGroup
```

URL mac dinh:

```text
http://localhost:5102
```

Dashboard:

```text
http://localhost:5102/Dashboard
```

## Chuc nang nen

- Quan ly mon hoc.
- Upload PDF, DOCX, PPT, PPTX.
- Goi `AiService` de chunk va embed tai lieu.
- Chat hoi dap theo tai lieu da index.
- Luu lich su chat.

## Chuc nang rieng

- SignalR realtime hub tai `/hubs/product`.
- Them/sua/xoa mon hoc co hien realtime.
- Upload/index/xoa tai lieu day event realtime len dashboard.
- Chatbot tra loi xong day event realtime len dashboard.
- Worker Service `ProductWorkerService` chay nen va gui heartbeat dinh ky.
- Dashboard tong quan trang thai AI, so mon, so tai lieu, so tin nhan va live feed.

## Cau truc

```text
EduChatbot.ProductGroup/
|-- Hubs/
|   `-- ProductHub.cs
|-- Services/
|   |-- ProductActivityFeed.cs
|   |-- ProductRealtimeNotifier.cs
|   |-- ProductWorkerService.cs
|   `-- PythonAIServiceRunner.cs
|-- Pages/
|   |-- Chat/
|   |-- Subjects/
|   |-- Dashboard.cshtml
|   `-- Index.cshtml
|-- Models/
|-- Data/
|-- wwwroot/
`-- Program.cs
```

## Chay

1. Cai dependencies cho `AiService`:

```powershell
cd D:\Project\PRN222\AiService
pip install -r requirements.txt
```

2. Cai model Ollama:

```powershell
ollama pull qwen2.5:3b
```

3. Mo `EduChatbot.Group.sln` bang Visual Studio 2022 va bam `F5`.

4. Mo dashboard:

```text
http://localhost:5102/Dashboard
```

Neu SignalR hoat dong, dashboard se hien `SignalR online` va live feed se nhan event tu CRUD/chat/upload/worker.
