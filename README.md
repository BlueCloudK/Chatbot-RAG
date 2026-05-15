# EduChatbot - PRN222

EduChatbot la repo demo he thong hoi dap tai lieu hoc tap bang RAG. Repo nay gom 3 du an web cung mot chu de, tach rieng de so sanh cau truc ASP.NET Core trong Visual Studio 2022.

## 3 du an chinh

| Du an | Solution | Port | Mo ta |
| --- | --- | --- | --- |
| MVC | `EduChatbot.MVC.sln` | `5099` | Ban ASP.NET Core MVC: controllers, views, models. |
| Razor Pages | `EduChatbot.RazorPages.sln` | `5101` | Ban Razor Pages cung chuc nang nen voi MVC. |
| ProductGroup | `EduChatbot.Group.sln` | `5102` | Ban Razor Pages mo rong: SignalR realtime, Worker Service, dashboard. |

Ca 3 ban deu dung chung `AiService` de upload, chunk, embed va chat voi tai lieu.

## Chuc nang

- Quan ly mon hoc.
- Upload PDF, DOCX, PPT, PPTX.
- Tu dong chunk va embed tai lieu.
- Chat hoi dap trong pham vi tai lieu da index.
- Trich dan nguon tai lieu.
- Luu lich su chat theo mon/phien.
- ProductGroup co them SignalR realtime va Worker Service.

## Cau truc repo

```text
PRN222/
|-- 01_MVC/
|   `-- EduChatbot.Web/              # Du an 1: MVC
|-- 02_RazorPages/
|   `-- EduChatbot.RazorPages/       # Du an 2: Razor Pages
|-- 03_ProductGroup/
|   `-- EduChatbot.ProductGroup/     # Du an 3: ProductGroup + SignalR + Worker
|-- AiService/                   # Python FastAPI RAG service, port 8000
|-- RblService/                  # Python FastAPI RBL/benchmark, port 8010
|-- scripts/                     # Script don port dev
|-- EduChatbot.MVC.sln
|-- EduChatbot.RazorPages.sln
|-- EduChatbot.Group.sln
|-- RUN_VISUAL_STUDIO_2022.md
`-- README.md
```

## Yeu cau moi truong

- Visual Studio 2022.
- .NET SDK tuong thich voi `net10.0`.
- SQL Server LocalDB.
- Python 3.10+.
- Ollama.

## Cai dependencies Python

```powershell
cd D:\Project\PRN222\AiService
pip install -r requirements.txt
```

Neu muon chay RBL/benchmark:

```powershell
cd D:\Project\PRN222\RblService
pip install -r requirements.txt
```

## Cai model local

Mac dinh nen dung:

```powershell
ollama pull qwen2.5:3b
```

May VRAM thap co the doi sang model nhe hon trong `AiService/services/rag_service.py`.

## Chay bang Visual Studio 2022

Mo mot trong cac solution sau:

- `EduChatbot.MVC.sln` de chay ban MVC.
- `EduChatbot.RazorPages.sln` de chay ban Razor Pages.
- `EduChatbot.Group.sln` de chay ban ProductGroup.

Sau do right click project web tuong ung, chon `Set as Startup Project`, bam `F5` hoac `Ctrl+F5`.

Moi ban web se tu khoi dong `AiService` o `http://127.0.0.1:8000` neu service chua chay.

## URL mac dinh

- MVC: `http://localhost:5099`
- Razor Pages: `http://localhost:5101`
- ProductGroup: `http://localhost:5102`
- ProductGroup dashboard: `http://localhost:5102/Dashboard`
- AI health check: `http://127.0.0.1:8000`
- RBL dashboard: `http://127.0.0.1:8010`

## Don port khi bi ket

```powershell
cd D:\Project\PRN222
powershell -ExecutionPolicy Bypass -File .\scripts\Stop-EduChatbotDev.ps1
```

## Ghi chu GitHub

Repo da co `.gitignore` de khong day cac thu muc build/cache/local data nhu `.vs`, `bin`, `obj`, `chroma_db`, `wwwroot/uploads`.

Moi du an web co README rieng:

- `01_MVC/EduChatbot.Web/README.md`
- `02_RazorPages/EduChatbot.RazorPages/README.md`
- `03_ProductGroup/EduChatbot.ProductGroup/README.md`
