# Running the Project with Visual Studio 2022

There are three separate solutions that can be opened with Visual Studio 2022:

- `01_MVC/EduChatbot.MVC.sln`: MVC chatbot version.
- `02_RazorPages/EduChatbot.RazorPages.sln`: Razor Pages version.
- `03_ProductGroup/EduChatbot.Group.sln`: ProductGroup Razor Pages version.

All three variants include subject management, document upload/indexing, RAG chat, a dashboard, SignalR realtime updates, and a background Worker Service.

If you only need to run the main product, open `01_MVC/EduChatbot.MVC.sln`. If you need to demo all three structures, open each solution separately:

- MVC: `01_MVC/EduChatbot.MVC.sln`, port `5099`
- Razor Pages: `02_RazorPages/EduChatbot.RazorPages.sln`, port `5101`
- ProductGroup: `03_ProductGroup/EduChatbot.Group.sln`, port `5102`

## Dashboard, SignalR, and Worker Service

Each solution demonstrates:

- SignalR hub at `/hubs/product`.
- Realtime subject CRUD events shown on the `Subjects` page and `Dashboard`.
- Realtime document/chat events for upload, index success/failure, document deletion, and chatbot replies.
- `ProductWorkerService`, which runs in the background and sends heartbeat events to the SignalR feed.
- MVC Dashboard: `http://localhost:5099/Dashboard`
- Razor Pages Dashboard: `http://localhost:5101/Dashboard`
- ProductGroup Dashboard: `http://localhost:5102/Dashboard`

## Important Structure

- `01_MVC`: standalone MVC package with `EduChatbot.MVC.sln`, `EduChatbot.Web`, `AiService`, and `RblService`.
- `02_RazorPages`: standalone Razor Pages package with `EduChatbot.RazorPages.sln`, the web app, `AiService`, and `RblService`.
- `03_ProductGroup`: standalone ProductGroup package with `EduChatbot.Group.sln`, the web app, `AiService`, and `RblService`.
- `AiService` inside each folder: FastAPI service for RAG, upload/indexing, and chat.
- `RblService` inside each folder: FastAPI service for the RBL/benchmark module, running on port `8010`.

## One-Time Setup

1. Install a .NET SDK compatible with the project target framework. The web projects currently target `net8.0`.
2. Install Python dependencies. Example for MVC:

```powershell
cd D:\Project\PRN222\01_MVC\AiService
pip install -r requirements.txt
```

3. Create/update the LocalDB database:

```powershell
cd D:\Project\PRN222
dotnet ef database update --project 01_MVC\EduChatbot.Web\EduChatbot.Web.csproj
```

4. Install Ollama and a local model:

```powershell
ollama pull qwen2.5:3b
```

## Run in Visual Studio

1. Open `01_MVC\EduChatbot.MVC.sln`.
2. Right-click `EduChatbot.Web` and select `Set as Startup Project`.
3. Choose the `http` launch profile.
4. Press `F5` or `Ctrl+F5`.
5. The web app opens at `http://localhost:5099`.
6. The Python AI service is started automatically at `http://127.0.0.1:8000`.

If Python is not available in `PATH`, update this setting:

```json
"AiService": {
  "BaseUrl": "http://127.0.0.1:8000",
  "PythonExecutable": "C:\\Path\\To\\python.exe"
}
```

in `01_MVC\EduChatbot.Web\appsettings.Development.json`.

## Quick Test

- Web: `http://localhost:5099`
- RBL dashboard: run the `RblService` project, then open `http://127.0.0.1:8010`
- AI health check: `http://127.0.0.1:8000`

If upload or chat fails, check the Visual Studio Output window. Python AI logs use the `[AiService]` prefix. If benchmarking fails, run `RblService` separately and check its terminal/output logs.
