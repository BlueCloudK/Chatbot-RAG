# EduChatbot.RazorPages

This is the ASP.NET Core Razor Pages web application for EduChatbot. It provides the same core features as the MVC version, but places page logic in PageModel classes instead of controllers.

## Solution

Open the parent solution:

```text
..\EduChatbot.RazorPages.sln
```

Startup project:

```text
EduChatbot.RazorPages
```

Default URL:

```text
http://localhost:5101
```

## Features

- Subject management with Razor Pages.
- Upload PDF, DOCX, PPT, and PPTX files.
- Call `AiService` to chunk and embed documents.
- Chat and Q&A over indexed documents.
- Chat history.

## Structure

```text
EduChatbot.RazorPages/
|-- Pages/
|   |-- Chat/
|   |-- Subjects/
|   `-- Index.cshtml
|-- Models/
|-- Data/
|-- Services/
|-- wwwroot/
`-- Program.cs
```

## Run

1. Install dependencies for the sibling `AiService`:

```powershell
cd D:\Project\PRN222\02_RazorPages\AiService
pip install -r requirements.txt
```

2. Install the Ollama model:

```powershell
ollama pull qwen2.5:3b
```

3. Open `..\EduChatbot.RazorPages.sln` in Visual Studio 2022 and press `F5`.

The web app automatically starts the local Python AI service at `http://127.0.0.1:8000`.

SignalR, dashboard, and Worker Service features are intentionally kept in the ProductGroup variant only.
