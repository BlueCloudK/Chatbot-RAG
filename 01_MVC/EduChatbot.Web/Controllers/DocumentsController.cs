using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using EduChatbot.Web.Data;
using EduChatbot.Web.Models;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.Web.Controllers
{
    public class DocumentsController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly IWebHostEnvironment _webHostEnvironment;
        private readonly IHttpClientFactory _httpClientFactory;

        public DocumentsController(ApplicationDbContext context, IWebHostEnvironment webHostEnvironment, IHttpClientFactory httpClientFactory)
        {
            _context = context;
            _webHostEnvironment = webHostEnvironment;
            _httpClientFactory = httpClientFactory;
        }

        public async Task<IActionResult> Index()
        {
            var documents = await _context.Documents.Include(d => d.Subject).ToListAsync();
            return View(documents);
        }

        public IActionResult Create()
        {
            ViewData["SubjectId"] = new SelectList(_context.Subjects, "Id", "Name");
            return View();
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Create(int subjectId, IFormFile file, string? returnUrl = null)
        {
            if (file == null || file.Length == 0)
            {
                ModelState.AddModelError("file", "Vui lòng chọn một file hợp lệ.");
                if (IsAjaxRequest())
                {
                    Response.StatusCode = StatusCodes.Status400BadRequest;
                    return Json(new { status = "Failed", indexed = false, chunks = 0, message = "Vui lòng chọn một file hợp lệ." });
                }

                if (!string.IsNullOrEmpty(returnUrl)) return LocalRedirect(returnUrl);
                ViewData["SubjectId"] = new SelectList(_context.Subjects, "Id", "Name", subjectId);
                return View();
            }

            var allowedExtensions = new[] { ".pdf", ".docx", ".pptx", ".ppt" };
            var extension = Path.GetExtension(file.FileName).ToLowerInvariant();

            if (!allowedExtensions.Contains(extension))
            {
                ModelState.AddModelError("file", "Chỉ hỗ trợ file PDF, DOCX, PPTX.");
                if (IsAjaxRequest())
                {
                    Response.StatusCode = StatusCodes.Status400BadRequest;
                    return Json(new { status = "Failed", indexed = false, chunks = 0, message = "Chỉ hỗ trợ file PDF, DOCX, PPTX." });
                }

                if (!string.IsNullOrEmpty(returnUrl)) return LocalRedirect(returnUrl);
                ViewData["SubjectId"] = new SelectList(_context.Subjects, "Id", "Name", subjectId);
                return View();
            }

            string uploadsFolder = Path.Combine(_webHostEnvironment.WebRootPath, "uploads");
            Directory.CreateDirectory(uploadsFolder);

            string uniqueFileName = Guid.NewGuid() + "_" + file.FileName;
            string filePath = Path.Combine(uploadsFolder, uniqueFileName);

            using (var fileStream = new FileStream(filePath, FileMode.Create))
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
                IndexMessage = "Đang upload và đọc tài liệu..."
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

                using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read);
                var fileContent = new StreamContent(fs);
                fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(file.ContentType);
                content.Add(fileContent, "file", file.FileName);

                var response = await client.PostAsync("/api/documents/index", content);
                if (response.IsSuccessStatusCode)
                {
                    var responseStr = await response.Content.ReadAsStringAsync();
                    using var jsonDoc = JsonDocument.Parse(responseStr);

                    if (jsonDoc.RootElement.TryGetProperty("chunks", out var chunksProp) && chunksProp.TryGetInt32(out var chunks))
                    {
                        document.ChunkCount = chunks;
                    }

                    if (jsonDoc.RootElement.TryGetProperty("indexed", out var indexedProp) && indexedProp.GetBoolean())
                    {
                        document.IsIndexed = true;
                        document.IndexStatus = "Indexed";
                        document.IndexedAt = DateTime.UtcNow;
                        document.IndexMessage = $"Đã đọc và nhúng {document.ChunkCount} đoạn nội dung.";
                    }
                    else
                    {
                        document.IsIndexed = false;
                        document.IndexStatus = "Failed";
                        document.IndexMessage = jsonDoc.RootElement.TryGetProperty("message", out var messageProp)
                            ? messageProp.GetString()
                            : "Python AI Service không index được tài liệu.";
                    }
                }
                else
                {
                    document.IsIndexed = false;
                    document.IndexStatus = "Failed";
                    document.IndexMessage = $"AI Service trả lỗi HTTP {(int)response.StatusCode}.";
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("AI API Error: " + ex.Message);
                document.IsIndexed = false;
                document.IndexStatus = "Failed";
                document.IndexMessage = "Không kết nối được AI Service: " + ex.Message;
            }

            _context.Update(document);
            await _context.SaveChangesAsync();

            if (IsAjaxRequest())
            {
                return Json(new
                {
                    status = document.IndexStatus,
                    indexed = document.IsIndexed,
                    chunks = document.ChunkCount,
                    message = document.IndexMessage,
                    documentId = document.Id,
                    fileName = document.FileName,
                    returnUrl = string.IsNullOrEmpty(returnUrl) ? Url.Action(nameof(Index)) : returnUrl
                });
            }

            if (!string.IsNullOrEmpty(returnUrl)) return LocalRedirect(returnUrl);
            return RedirectToAction(nameof(Index));
        }

        public async Task<IActionResult> Delete(int? id)
        {
            if (id == null) return NotFound();
            var document = await _context.Documents
                .Include(d => d.Subject)
                .FirstOrDefaultAsync(m => m.Id == id);
            if (document == null) return NotFound();

            return View(document);
        }

        [HttpPost, ActionName("Delete")]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> DeleteConfirmed(int id, string? returnUrl = null)
        {
            var document = await _context.Documents.FindAsync(id);
            if (document != null)
            {
                string fullPath = Path.Combine(_webHostEnvironment.WebRootPath, document.FilePath.TrimStart('/'));
                if (System.IO.File.Exists(fullPath))
                {
                    System.IO.File.Delete(fullPath);
                }

                try
                {
                    using var client = _httpClientFactory.CreateClient("AiService");
                    await client.DeleteAsync($"/api/documents/{document.Id}");
                    await client.DeleteAsync($"/api/documents/{Uri.EscapeDataString(document.FileName)}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine("AI API Delete Error: " + ex.Message);
                }

                _context.Documents.Remove(document);
                await _context.SaveChangesAsync();
            }

            if (!string.IsNullOrEmpty(returnUrl)) return LocalRedirect(returnUrl);
            return RedirectToAction(nameof(Index));
        }

        private bool IsAjaxRequest()
        {
            return string.Equals(Request.Headers["X-Requested-With"], "XMLHttpRequest", StringComparison.OrdinalIgnoreCase)
                || Request.Headers.Accept.Any(h => h?.Contains("application/json", StringComparison.OrdinalIgnoreCase) == true);
        }
    }
}
