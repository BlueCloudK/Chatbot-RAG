# EduChatbot - PRN222

EduChatbot la repo demo he thong hoi dap tai lieu hoc tap bang RAG. Repo nay gom 3 du an web cung mot chu de, tach rieng de so sanh cau truc ASP.NET Core trong Visual Studio 2022.

## 3 du an chinh

| Du an | Solution | Port | Mo ta |
| --- | --- | --- | --- |
| MVC | `01_MVC/EduChatbot.MVC.sln` | `5099` | Ban ASP.NET Core MVC: controllers, views, models. |
| Razor Pages | `02_RazorPages/EduChatbot.RazorPages.sln` | `5101` | Ban Razor Pages cung chuc nang nen voi MVC. |
| ProductGroup | `03_ProductGroup/EduChatbot.Group.sln` | `5102` | Ban Razor Pages mo rong cho nhom, cung day du feature. |

Moi folder la mot goi doc lap: co solution rieng, web app rieng, `AiService` rieng va `RblService` rieng. Code co bi lap lai mot chut de de mo/chay/cham bai.

## Chuc nang

- Quan ly mon hoc.
- Upload PDF, DOCX, PPT, PPTX.
- Tu dong chunk va embed tai lieu.
- Chat hoi dap trong pham vi tai lieu da index.
- Trich dan nguon tai lieu.
- Luu lich su chat theo mon/phien.
- Ca 3 ban deu co Dashboard, SignalR realtime va Worker Service.

## Cau truc repo

```text
PRN222/
|-- 01_MVC/
|   |-- EduChatbot.MVC.sln
|   |-- EduChatbot.Web/              # Du an 1: MVC
|   |-- AiService/                   # Ban copy rieng cho MVC
|   `-- RblService/                  # Ban copy rieng cho MVC
|-- 02_RazorPages/
|   |-- EduChatbot.RazorPages.sln
|   |-- EduChatbot.RazorPages/       # Du an 2: Razor Pages
|   |-- AiService/                   # Ban copy rieng cho Razor Pages
|   `-- RblService/                  # Ban copy rieng cho Razor Pages
|-- 03_ProductGroup/
|   |-- EduChatbot.Group.sln
|   |-- EduChatbot.ProductGroup/     # Du an 3: ProductGroup + SignalR + Worker
|   |-- AiService/                   # Ban copy rieng cho ProductGroup
|   `-- RblService/                  # Ban copy rieng cho ProductGroup
|-- scripts/                     # Script don port dev
|-- RUN_VISUAL_STUDIO_2022.md
`-- README.md
```

## Yeu cau moi truong

- Visual Studio 2022.
- .NET SDK 8.0 tro len. Cac web project dang target `net8.0` de chay on dinh tren Visual Studio 2022.
- SQL Server LocalDB.
- Python 3.10+.
- Ollama.

## Cai dependencies Python

```powershell
cd D:\Project\PRN222\01_MVC\AiService
pip install -r requirements.txt
```

Neu muon chay RBL/benchmark:

```powershell
cd D:\Project\PRN222\01_MVC\RblService
pip install -r requirements.txt
```

## Cai model local

Mac dinh nen dung:

```powershell
ollama pull qwen2.5:3b
```

May VRAM thap co the doi sang model nhe hon trong `AiService/services/rag_service.py` cua folder ban dang chay, vi moi ban co `AiService` rieng.

## Chay bang Visual Studio 2022

Mo mot trong cac solution sau:

- `01_MVC/EduChatbot.MVC.sln` de chay ban MVC.
- `02_RazorPages/EduChatbot.RazorPages.sln` de chay ban Razor Pages.
- `03_ProductGroup/EduChatbot.Group.sln` de chay ban ProductGroup.

Sau do right click project web tuong ung, chon `Set as Startup Project`, bam `F5` hoac `Ctrl+F5`.

Moi ban web se tu khoi dong `AiService` trong cung folder cua no o `http://127.0.0.1:8000` neu service chua chay.

## URL mac dinh

- MVC: `http://localhost:5099`
- Razor Pages: `http://localhost:5101`
- ProductGroup: `http://localhost:5102`
- MVC dashboard: `http://localhost:5099/Dashboard`
- Razor Pages dashboard: `http://localhost:5101/Dashboard`
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

- `01_MVC/README.md`
- `02_RazorPages/README.md`
- `03_ProductGroup/README.md`
