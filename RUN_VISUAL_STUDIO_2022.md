# Chay du an bang Visual Studio 2022

Co 3 solution rieng de mo bang Visual Studio 2022:

- `EduChatbot.MVC.sln`: ban chatbot MVC chinh hien tai.
- `EduChatbot.RazorPages.sln`: ban Razor Pages rieng, cung chuc nang nen voi MVC.
- `EduChatbot.Group.sln`: ban ProductGroup bang Razor Pages, cung chuc nang nen va them SignalR + Worker Service + dashboard/demo nhom.

Neu chi can chay san pham chinh, mo `EduChatbot.MVC.sln`. Neu can demo ba cau truc, mo tung solution rieng:

- MVC: `EduChatbot.MVC.sln`, port `5099`
- Razor Pages: `EduChatbot.RazorPages.sln`, port `5101`
- ProductGroup: `EduChatbot.Group.sln`, port `5102`

## Rieng ban ProductGroup

Ban `EduChatbot.Group.sln` demo them cac phan sau:

- SignalR hub: `/hubs/product`
- Realtime CRUD mon hoc: them/sua/xoa se hien trong trang `Subjects` va `Dashboard`
- Realtime tai lieu/chat: upload, index xong/loi, xoa tai lieu, chatbot tra loi se day event len dashboard
- Worker Service: `ProductWorkerService` chay nen va gui heartbeat dinh ky len SignalR feed
- Dashboard: `http://localhost:5102/Dashboard`

## Cau truc can quan tam

- `01_MVC/EduChatbot.Web`: ASP.NET Core MVC web app. Day la startup project cua `EduChatbot.MVC.sln`.
- `02_RazorPages/EduChatbot.RazorPages`: ASP.NET Core Razor Pages project rieng, co quan ly mon, upload/index va chat.
- `03_ProductGroup/EduChatbot.ProductGroup`: ASP.NET Core Razor Pages product/group app, co them dashboard van hanh, SignalR realtime va Worker Service.
- `AiService`: FastAPI service cho RAG, upload/index va chat.
- `RblService`: FastAPI project rieng cho module nghien cuu RBL/benchmark, chay o port 8010.
- `temp_open_notebook`: chi de tham khao opensource, khong can chay trong Visual Studio.

## Chuan bi mot lan

1. Cai .NET SDK phu hop voi `TargetFramework` trong `01_MVC/EduChatbot.Web/EduChatbot.Web.csproj`.
2. Cai Python dependencies:

```powershell
cd D:\Project\PRN222\AiService
pip install -r requirements.txt
```

3. Tao database LocalDB:

```powershell
cd D:\Project\PRN222
dotnet ef database update --project 01_MVC\EduChatbot.Web\EduChatbot.Web.csproj
```

4. Cai Ollama va model local:

```powershell
ollama pull qwen2:1.5b
```

## Chay trong Visual Studio

1. Mo `EduChatbot.MVC.sln`.
2. Right click `EduChatbot.Web` -> `Set as Startup Project`.
3. Chon launch profile `http`.
4. Bam `F5` hoac `Ctrl+F5`.
5. Web se mo tai `http://localhost:5099`.
6. Python AI service se duoc web app tu khoi dong tai `http://127.0.0.1:8000`.

Neu Python khong nam trong PATH, sua:

```json
"AiService": {
  "BaseUrl": "http://127.0.0.1:8000",
  "PythonExecutable": "C:\\Path\\To\\python.exe"
}
```

trong `01_MVC\EduChatbot.Web\appsettings.Development.json`.

## Test nhanh

- Web: `http://localhost:5099`
- RBL dashboard: chay project `RblService`, sau do mo `http://127.0.0.1:8010`
- AI health check: `http://127.0.0.1:8000`

Neu upload/chat loi, xem Output window cua Visual Studio. Log cua Python AI service se hien voi prefix `[AiService]`.
Neu benchmark loi, chay rieng `RblService` va xem terminal/output cua project do.

## Don port khi Visual Studio bi ket

Thong thuong khi dung web, `AiService` se tu tat theo `EduChatbot.Web`. Neu Visual Studio hoac Windows van giu port tu lan chay cu, chay lenh nay tai thu muc `D:\Project\PRN222`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Stop-EduChatbotDev.ps1
```

Script chi dung de don cac port dev cua du an: `5099` cho MVC, `5101` cho Razor Pages, `5102` cho ProductGroup, `8000` cho AI, va `8010` cho RBL.
