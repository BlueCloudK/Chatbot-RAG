# EduChatbot.Web - MVC

This is the ASP.NET Core MVC web application for EduChatbot.

## Solution

Open the parent solution:

```text
..\EduChatbot.MVC.sln
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

## Structure

```text
EduChatbot.Web/
|-- Controllers/
|-- Views/
|-- Models/
|-- Data/
|-- Services/
|-- wwwroot/
`-- Program.cs
```

## Run

1. Install dependencies for the sibling `AiService`:

```powershell
cd D:\Project\PRN222\01_MVC\AiService
pip install -r requirements.txt
```

2. Install the Ollama model:

```powershell
ollama pull qwen2.5:3b
```

3. Open `..\EduChatbot.MVC.sln` in Visual Studio 2022 and press `F5`.

The web app automatically starts the local Python AI service at `http://127.0.0.1:8000`.

SignalR, dashboard, and Worker Service features are intentionally kept in the ProductGroup variant only.
