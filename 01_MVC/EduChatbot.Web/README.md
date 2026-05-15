# EduChatbot.Web - MVC

Day la ban EduChatbot dung ASP.NET Core MVC.

## Solution

Mo solution:

```text
EduChatbot.MVC.sln
```

Startup project:

```text
EduChatbot.Web
```

URL mac dinh:

```text
http://localhost:5099
```

## Chuc nang

- Quan ly mon hoc.
- Upload PDF, DOCX, PPT, PPTX.
- Goi `AiService` de chunk va embed tai lieu.
- Chat hoi dap theo tai lieu da index.
- Trich dan nguon tai lieu.
- Luu lich su chat.
- Dashboard tong quan.
- SignalR realtime cho CRUD/upload/chat.
- Worker Service gui heartbeat dinh ky.

## Cau truc

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

3. Mo `EduChatbot.MVC.sln` bang Visual Studio 2022 va bam `F5`.

Web app se tu khoi dong Python AI service tai `http://127.0.0.1:8000`.

Dashboard:

```text
http://localhost:5099/Dashboard
```
