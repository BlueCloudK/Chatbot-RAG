# EduChatbot.Web - MVC

This is the ASP.NET Core MVC version of EduChatbot.

## Solution

Open this solution:

```text
EduChatbot.MVC.sln
```

Startup project:

```text
EduChatbot.Web
```

Default URL:

```text
http://localhost:5099
```

## Features

- Subject management.
- Upload PDF, DOCX, PPT, and PPTX files.
- Call `AiService` to chunk and embed documents.
- Chat and Q&A over indexed documents.
- Source citation from uploaded documents.
- Chat history.
- Overview dashboard.
- SignalR realtime updates for CRUD, upload, and chat events.
- Background Worker Service heartbeat.

## Structure

```text
01_MVC/
|-- EduChatbot.MVC.sln
|-- EduChatbot.Web/
|   |-- Controllers/
|   |-- Views/
|   |-- Models/
|   |-- Data/
|   |-- Services/
|   |-- wwwroot/
|   `-- Program.cs
|-- AiService/
`-- RblService/
```

## Run

1. Install dependencies for `AiService`:

```powershell
cd D:\Project\PRN222\01_MVC\AiService
pip install -r requirements.txt
```

2. Install the Ollama model:

```powershell
ollama pull qwen2.5:3b
```

3. Open `EduChatbot.MVC.sln` in Visual Studio 2022 and press `F5`.

The web app automatically starts the local Python AI service at `http://127.0.0.1:8000`.

`RblService` is included in this folder for standalone benchmark demos when needed.

Dashboard:

```text
http://localhost:5099/Dashboard
```
