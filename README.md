# EduChatbot - PRN222

EduChatbot is a demo RAG-based learning assistant for asking questions over uploaded course documents. The repository contains three self-contained ASP.NET Core variants with the same core feature set, separated so they can be opened and reviewed independently in Visual Studio 2022.

## Main Projects

| Variant | Solution | Port | Description |
| --- | --- | --- | --- |
| MVC | `01_MVC/EduChatbot.MVC.sln` | `5099` | ASP.NET Core MVC version using controllers, views, and models. |
| Razor Pages | `02_RazorPages/EduChatbot.RazorPages.sln` | `5101` | Razor Pages version with the same core features. |
| ProductGroup | `03_ProductGroup/EduChatbot.Group.sln` | `5102` | Extended Razor Pages version for group/product demo features. |

Each folder is a standalone package with its own solution, web app, `AiService`, and `RblService`. Some code is intentionally duplicated to make each variant easy to open, run, and grade on its own.

## Features

- Subject management.
- Upload PDF, DOCX, PPT, and PPTX files.
- Automatic document chunking and embedding.
- Chat and Q&A over indexed documents.
- Source citation from uploaded documents.
- Chat history by subject/session.
- Dashboard, SignalR realtime updates, and a background Worker Service in all three variants.

## Repository Structure

```text
PRN222/
|-- 01_MVC/
|   |-- EduChatbot.MVC.sln
|   |-- EduChatbot.Web/              # Variant 1: MVC
|   |-- AiService/                   # Dedicated AI service copy for MVC
|   `-- RblService/                  # Dedicated RBL service copy for MVC
|-- 02_RazorPages/
|   |-- EduChatbot.RazorPages.sln
|   |-- EduChatbot.RazorPages/       # Variant 2: Razor Pages
|   |-- AiService/                   # Dedicated AI service copy for Razor Pages
|   `-- RblService/                  # Dedicated RBL service copy for Razor Pages
|-- 03_ProductGroup/
|   |-- EduChatbot.Group.sln
|   |-- EduChatbot.ProductGroup/     # Variant 3: ProductGroup + SignalR + Worker
|   |-- AiService/                   # Dedicated AI service copy for ProductGroup
|   `-- RblService/                  # Dedicated RBL service copy for ProductGroup
|-- RUN_VISUAL_STUDIO_2022.md
`-- README.md
```

## Requirements

- Visual Studio 2022.
- .NET SDK 8.0 or newer. The web projects target `net8.0`.
- SQL Server LocalDB.
- Python 3.10+.
- Ollama.

## Install Python Dependencies

Example for the MVC variant:

```powershell
cd D:\Project\PRN222\01_MVC\AiService
pip install -r requirements.txt
```

For the RBL benchmark service:

```powershell
cd D:\Project\PRN222\01_MVC\RblService
pip install -r requirements.txt
```

Repeat the same steps inside `02_RazorPages` or `03_ProductGroup` if you run those variants.

## Install Local Model

Recommended default:

```powershell
ollama pull qwen2.5:3b
```

On lower VRAM machines, you can switch to a smaller model in the `AiService/services/rag_service.py` file inside the variant you are running.

## Run with Visual Studio 2022

Open one of these solutions:

- `01_MVC/EduChatbot.MVC.sln` for the MVC version.
- `02_RazorPages/EduChatbot.RazorPages.sln` for the Razor Pages version.
- `03_ProductGroup/EduChatbot.Group.sln` for the ProductGroup version.

Then right-click the matching web project, choose `Set as Startup Project`, and press `F5` or `Ctrl+F5`.

Each web app starts the `AiService` located in the same folder if the service is not already running on `http://127.0.0.1:8000`.

## Default URLs

- MVC: `http://localhost:5099`
- Razor Pages: `http://localhost:5101`
- ProductGroup: `http://localhost:5102`
- MVC dashboard: `http://localhost:5099/Dashboard`
- Razor Pages dashboard: `http://localhost:5101/Dashboard`
- ProductGroup dashboard: `http://localhost:5102/Dashboard`
- AI health check: `http://127.0.0.1:8000`
- RBL dashboard: `http://127.0.0.1:8010`

## GitHub Notes

The repository includes a `.gitignore` for build output, local caches, uploaded files, databases, Python caches, and environment files.

Each standalone variant also has its own README:

- `01_MVC/README.md`
- `02_RazorPages/README.md`
- `03_ProductGroup/README.md`
