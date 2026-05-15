# EduChatbot.ProductGroup

This is the ProductGroup version of EduChatbot. It uses Razor Pages and includes the full feature set from the other two variants, plus dashboard, SignalR, and Worker Service demo features for the group/product requirement.

## Solution

Open this solution:

```text
EduChatbot.Group.sln
```

Startup project:

```text
EduChatbot.ProductGroup
```

Default URL:

```text
http://localhost:5102
```

Dashboard:

```text
http://localhost:5102/Dashboard
```

## Core Features

- Subject management.
- Upload PDF, DOCX, PPT, and PPTX files.
- Call `AiService` to chunk and embed documents.
- Chat and Q&A over indexed documents.
- Chat history.

## Group/Product Features

- SignalR realtime hub at `/hubs/product`.
- Realtime subject create/update/delete events.
- Realtime document upload, index success/failure, and delete events on the dashboard.
- Realtime chatbot reply events on the dashboard.
- Background `ProductWorkerService` heartbeat.
- Dashboard showing AI status, subject count, document count, message count, and a live feed.

## Structure

```text
03_ProductGroup/
|-- EduChatbot.Group.sln
|-- EduChatbot.ProductGroup/
|   |-- Hubs/
|   |   `-- ProductHub.cs
|   |-- Services/
|   |   |-- ProductActivityFeed.cs
|   |   |-- ProductRealtimeNotifier.cs
|   |   |-- ProductWorkerService.cs
|   |   `-- PythonAIServiceRunner.cs
|   |-- Pages/
|   |   |-- Chat/
|   |   |-- Subjects/
|   |   |-- Dashboard.cshtml
|   |   `-- Index.cshtml
|   |-- Models/
|   |-- Data/
|   |-- wwwroot/
|   `-- Program.cs
|-- AiService/
`-- RblService/
```

## Run

1. Install dependencies for `AiService`:

```powershell
cd D:\Project\PRN222\03_ProductGroup\AiService
pip install -r requirements.txt
```

2. Install the Ollama model:

```powershell
ollama pull qwen2.5:3b
```

3. Open `EduChatbot.Group.sln` in Visual Studio 2022 and press `F5`.

4. Open the dashboard:

```text
http://localhost:5102/Dashboard
```

When SignalR is working, the dashboard shows `SignalR online` and the live feed receives events from CRUD actions, chat, upload/indexing, and the worker service.
