# EduChatbot.RazorPages

Day la ban EduChatbot dung ASP.NET Core Razor Pages. Chuc nang nen giong ban MVC, nhung logic duoc dat trong tung PageModel thay vi controller.

## Solution

Mo solution:

```text
EduChatbot.RazorPages.sln
```

Startup project:

```text
EduChatbot.RazorPages
```

URL mac dinh:

```text
http://localhost:5101
```

## Chuc nang

- Quan ly mon hoc bang Razor Pages.
- Upload PDF, DOCX, PPT, PPTX.
- Goi `AiService` de chunk va embed tai lieu.
- Chat hoi dap theo tai lieu da index.
- Luu lich su chat.
- Dashboard tong quan.
- SignalR realtime cho CRUD/upload/chat.
- Worker Service gui heartbeat dinh ky.

## Cau truc

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
AiService/
RblService/
```

## Chay

1. Cai dependencies cho `AiService`:

```powershell
cd D:\Project\PRN222\02_RazorPages\AiService
pip install -r requirements.txt
```

2. Cai model Ollama:

```powershell
ollama pull qwen2.5:3b
```

3. Mo `EduChatbot.RazorPages.sln` bang Visual Studio 2022 va bam `F5`.

Web app se tu khoi dong Python AI service tai `http://127.0.0.1:8000`.

`RblService` da duoc copy trong folder nay de demo benchmark rieng khi can.

Dashboard:

```text
http://localhost:5101/Dashboard
```
