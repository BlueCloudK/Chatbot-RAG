using System.Text;
using System.Text.Json;
using EduChatbot.RazorPages.Data;
using EduChatbot.RazorPages.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.RazorPages.Pages.Chat;

public class IndexModel : PageModel
{
    private readonly ApplicationDbContext _context;
    private readonly IWebHostEnvironment _environment;
    private readonly IHttpClientFactory _httpClientFactory;

    public IndexModel(ApplicationDbContext context, IWebHostEnvironment environment, IHttpClientFactory httpClientFactory)
    {
        _context = context;
        _environment = environment;
        _httpClientFactory = httpClientFactory;
    }

    public Subject CurrentSubject { get; private set; } = new();
    public ChatSession CurrentSession { get; private set; } = new();
    public IList<Document> Documents { get; private set; } = new List<Document>();

    public async Task<IActionResult> OnGetAsync(int subjectId)
    {
        var loaded = await LoadSubjectAsync(subjectId);
        return loaded ? Page() : RedirectToPage("/Index");
    }

    public async Task<IActionResult> OnGetAiStatusAsync()
    {
        try
        {
            using var client = _httpClientFactory.CreateClient("AiService");
            using var response = await client.GetAsync("/");
            return new JsonResult(new
            {
                ready = response.IsSuccessStatusCode,
                status = response.IsSuccessStatusCode ? "ready" : "error",
                message = response.IsSuccessStatusCode ? "AI Engine san sang" : $"AI Engine HTTP {(int)response.StatusCode}"
            })
            { StatusCode = response.IsSuccessStatusCode ? 200 : StatusCodes.Status503ServiceUnavailable };
        }
        catch (Exception ex)
        {
            return new JsonResult(new { ready = false, status = "starting", message = "AI Engine chua san sang: " + ex.Message })
            { StatusCode = StatusCodes.Status503ServiceUnavailable };
        }
    }

    public async Task<IActionResult> OnPostSendMessageAsync(int subjectId, string content)
    {
        if (string.IsNullOrWhiteSpace(content))
            return BadRequest(new { success = false, message = "Vui long nhap cau hoi." });

        var session = await _context.ChatSessions
            .Include(s => s.Messages)
            .FirstOrDefaultAsync(s => s.SubjectId == subjectId);
        if (session == null)
            return NotFound(new { success = false, message = "Khong tim thay phien chat." });

        var hasIndexedDocuments = await _context.Documents.AnyAsync(d => d.SubjectId == subjectId && d.IsIndexed);
        var processingDocuments = await _context.Documents.CountAsync(d => d.SubjectId == subjectId && !d.IsIndexed && d.IndexStatus != "Failed");
        if (!hasIndexedDocuments)
        {
            var message = processingDocuments > 0
                ? $"Tai lieu van dang doc va tao embedding ({processingDocuments} file dang xu ly). Doi den khi trang thai chuyen sang Da chunk & embed roi hoi lai."
                : "Mon nay chua co tai lieu nao da index xong. Hay tai tai lieu len truoc khi chat.";
            return new JsonResult(new { success = false, message }) { StatusCode = StatusCodes.Status409Conflict };
        }

        var recentHistory = (session.Messages ?? Enumerable.Empty<ChatMessage>())
            .OrderBy(m => m.Timestamp)
            .TakeLast(6)
            .Select(m => new { role = m.Role, content = m.Content })
            .ToList();

        var payload = JsonSerializer.Serialize(new
        {
            session_id = session.Id,
            subject_id = subjectId,
            query = content,
            history = recentHistory
        });

        string answer;
        string sourceDocs = "";
        try
        {
            using var client = _httpClientFactory.CreateClient("AiService");
            using var response = await client.PostAsync("/api/chat/ask", new StringContent(payload, Encoding.UTF8, "application/json"));
            response.EnsureSuccessStatusCode();

            using var jsonDoc = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            answer = jsonDoc.RootElement.GetProperty("answer").GetString() ?? "Phan hoi rong.";
            if (jsonDoc.RootElement.TryGetProperty("sources", out var sourcesEl))
            {
                sourceDocs = string.Join(", ", sourcesEl.EnumerateArray()
                    .Select(s => s.GetString())
                    .Where(s => !string.IsNullOrWhiteSpace(s)));
            }
        }
        catch
        {
            return new JsonResult(new { success = false, message = "AI Engine chua san sang hoac dang bi loi. Vui long thu lai sau." })
            { StatusCode = StatusCodes.Status503ServiceUnavailable };
        }

        var userMsg = new ChatMessage { SessionId = session.Id, Role = "User", Content = content, SourceDocuments = "", Timestamp = DateTime.UtcNow };
        var botMsg = new ChatMessage { SessionId = session.Id, Role = "Bot", Content = answer, SourceDocuments = sourceDocs, Timestamp = DateTime.UtcNow };
        _context.ChatMessages.AddRange(userMsg, botMsg);
        await _context.SaveChangesAsync();

        return new JsonResult(new
        {
            success = true,
            user = new { id = userMsg.Id, content = userMsg.Content },
            bot = new { id = botMsg.Id, content = botMsg.Content, sourceDocuments = botMsg.SourceDocuments }
        });
    }

    public async Task<IActionResult> OnPostUploadAsync(int subjectId, IFormFile file)
    {
        if (file == null || file.Length == 0)
            return BadRequest(new { status = "Failed", indexed = false, chunks = 0, message = "Vui long chon file hop le." });

        var extension = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (!new[] { ".pdf", ".docx", ".pptx", ".ppt" }.Contains(extension))
            return BadRequest(new { status = "Failed", indexed = false, chunks = 0, message = "Chi ho tro PDF, DOCX, PPTX." });

        var uploadsFolder = Path.Combine(_environment.WebRootPath, "uploads");
        Directory.CreateDirectory(uploadsFolder);
        var uniqueFileName = Guid.NewGuid() + "_" + file.FileName;
        var filePath = Path.Combine(uploadsFolder, uniqueFileName);

        await using (var fileStream = new FileStream(filePath, FileMode.Create))
        {
            await file.CopyToAsync(fileStream);
        }

        var document = new Document
        {
            FileName = file.FileName,
            FilePath = "/uploads/" + uniqueFileName,
            SubjectId = subjectId,
            UploadedAt = DateTime.UtcNow,
            IsIndexed = false,
            ChunkCount = 0,
            IndexStatus = "Processing",
            IndexMessage = "Dang upload va doc tai lieu..."
        };
        _context.Documents.Add(document);
        await _context.SaveChangesAsync();

        try
        {
            using var client = _httpClientFactory.CreateClient("AiService");
            using var content = new MultipartFormDataContent();
            content.Add(new StringContent(subjectId.ToString()), "subject_id");
            content.Add(new StringContent(document.Id.ToString()), "document_id");
            content.Add(new StringContent(document.FileName), "document_name");

            await using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read);
            content.Add(new StreamContent(fs), "file", file.FileName);
            using var response = await client.PostAsync("/api/documents/index", content);

            if (response.IsSuccessStatusCode)
            {
                using var jsonDoc = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                document.ChunkCount = jsonDoc.RootElement.TryGetProperty("chunks", out var chunksProp) && chunksProp.TryGetInt32(out var chunks) ? chunks : 0;
                document.IsIndexed = jsonDoc.RootElement.TryGetProperty("indexed", out var indexedProp) && indexedProp.GetBoolean();
                document.IndexStatus = document.IsIndexed ? "Indexed" : "Failed";
                document.IndexedAt = document.IsIndexed ? DateTime.UtcNow : null;
                document.IndexMessage = document.IsIndexed
                    ? $"Da doc va nhung {document.ChunkCount} doan noi dung."
                    : "Python AI Service khong index duoc tai lieu.";
            }
            else
            {
                document.IndexStatus = "Failed";
                document.IndexMessage = $"AI Service tra loi HTTP {(int)response.StatusCode}.";
            }
        }
        catch (Exception ex)
        {
            document.IndexStatus = "Failed";
            document.IndexMessage = "Khong ket noi duoc AI Service: " + ex.Message;
        }

        await _context.SaveChangesAsync();
        return new JsonResult(new
        {
            status = document.IndexStatus,
            indexed = document.IsIndexed,
            chunks = document.ChunkCount,
            message = document.IndexMessage,
            documentId = document.Id,
            fileName = document.FileName
        });
    }

    public async Task<IActionResult> OnPostDeleteDocumentAsync(int id, int subjectId)
    {
        var document = await _context.Documents.FindAsync(id);
        if (document != null)
        {
            var fullPath = Path.Combine(_environment.WebRootPath, document.FilePath.TrimStart('/'));
            if (System.IO.File.Exists(fullPath))
                System.IO.File.Delete(fullPath);

            try
            {
                using var client = _httpClientFactory.CreateClient("AiService");
                await client.DeleteAsync($"/api/documents/{document.Id}");
                await client.DeleteAsync($"/api/documents/{Uri.EscapeDataString(document.FileName)}");
            }
            catch
            {
                // Local database cleanup should still work if AI service is offline.
            }

            _context.Documents.Remove(document);
            await _context.SaveChangesAsync();
        }

        return RedirectToPage(new { subjectId });
    }

    private async Task<bool> LoadSubjectAsync(int subjectId)
    {
        var subject = await _context.Subjects.FindAsync(subjectId);
        if (subject == null)
            return false;

        CurrentSubject = subject;
        CurrentSession = await _context.ChatSessions
            .Include(s => s.Messages)
            .FirstOrDefaultAsync(s => s.SubjectId == subjectId)
            ?? new ChatSession { SubjectId = subjectId, CreatedAt = DateTime.UtcNow };

        if (CurrentSession.Id == 0)
        {
            _context.ChatSessions.Add(CurrentSession);
            await _context.SaveChangesAsync();
        }

        Documents = await _context.Documents
            .Where(d => d.SubjectId == subjectId)
            .OrderByDescending(d => d.UploadedAt)
            .ToListAsync();

        CurrentSession = await _context.ChatSessions
            .Include(s => s.Messages)
            .FirstAsync(s => s.Id == CurrentSession.Id);

        return true;
    }
}
