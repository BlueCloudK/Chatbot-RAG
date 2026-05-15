using System;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using EduChatbot.Web.Data;
using EduChatbot.Web.Models;
using EduChatbot.Web.Models.ViewModels;
using EduChatbot.Web.Services;

namespace EduChatbot.Web.Controllers
{
    public class ChatController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly ProductRealtimeNotifier _notifier;

        public ChatController(ApplicationDbContext context, IHttpClientFactory httpClientFactory, ProductRealtimeNotifier notifier)
        {
            _context = context;
            _httpClientFactory = httpClientFactory;
            _notifier = notifier;
        }

        // GET: /Chat?subjectId=3
        public async Task<IActionResult> Index(int? subjectId)
        {
            if (subjectId == null)
                return RedirectToAction("Index", "Home");

            var subject = await _context.Subjects.FindAsync(subjectId.Value);
            if (subject == null)
                return RedirectToAction("Index", "Home");

            // Tìm hoặc tạo session cho subject (1 subject = 1 session)
            var session = await _context.ChatSessions
                .Include(s => s.Subject)
                .Include(s => s.Messages)
                .FirstOrDefaultAsync(s => s.SubjectId == subjectId.Value);

            if (session == null)
            {
                session = new ChatSession
                {
                    SubjectId = subjectId.Value,
                    CreatedAt = DateTime.UtcNow
                };
                _context.ChatSessions.Add(session);
                await _context.SaveChangesAsync();

                session = await _context.ChatSessions
                    .Include(s => s.Subject)
                    .Include(s => s.Messages)
                    .FirstAsync(s => s.Id == session.Id);
            }

            var documents = await _context.Documents
                .Where(d => d.SubjectId == subjectId.Value)
                .ToListAsync();

            var viewModel = new ChatViewModel
            {
                CurrentSession = session,
                CurrentDocuments = documents
            };

            return View(viewModel);
        }

        [HttpPost]
        public async Task<IActionResult> SendMessage(int subjectId, string content)
        {
            if (string.IsNullOrWhiteSpace(content))
            {
                if (IsAjaxRequest())
                {
                    Response.StatusCode = 400;
                    return Json(new { success = false, message = "Vui lòng nhập câu hỏi." });
                }

                return RedirectToAction("Index", new { subjectId });
            }

            var session = await _context.ChatSessions
                .Include(s => s.Messages)
                .FirstOrDefaultAsync(s => s.SubjectId == subjectId);

            if (session == null)
            {
                if (IsAjaxRequest())
                {
                    Response.StatusCode = 404;
                    return Json(new { success = false, message = "Không tìm thấy phiên chat." });
                }

                return RedirectToAction("Index", new { subjectId });
            }

            var hasIndexedDocuments = await _context.Documents.AnyAsync(d => d.SubjectId == subjectId && d.IsIndexed);
            var processingDocuments = await _context.Documents.CountAsync(d =>
                d.SubjectId == subjectId &&
                !d.IsIndexed &&
                d.IndexStatus != "Failed");

            if (!hasIndexedDocuments)
            {
                var waitMessage = processingDocuments > 0
                    ? $"Tài liệu vẫn đang được đọc và tạo embedding ({processingDocuments} file đang xử lý). Chờ trạng thái chuyển sang 'Đã chunk & embed' rồi hãy hỏi lại nhé."
                    : "Môn này chưa có tài liệu nào đã index xong. Hãy tải tài liệu lên và chờ xử lý hoàn tất trước khi chat.";

                if (IsAjaxRequest())
                {
                    Response.StatusCode = StatusCodes.Status409Conflict;
                    return Json(new { success = false, message = waitMessage });
                }

                return RedirectToAction("Index", new { subjectId });
            }

            // Prepare messages, but only persist them after the AI request succeeds.
            var recentHistory = (session.Messages ?? Enumerable.Empty<ChatMessage>())
                .OrderBy(m => m.Timestamp)
                .TakeLast(6)
                .Select(m => new
                {
                    role = m.Role,
                    content = m.Content
                })
                .ToList();

            var userMsg = new ChatMessage
            {
                SessionId = session.Id,
                Role = "User",
                Content = content,
                SourceDocuments = "",
                Timestamp = DateTime.UtcNow
            };
            // Call Python AI API
            string answer = "Lỗi kết nối tới AI Engine. Hãy chắc chắn Python FastAPI đang chạy ở port 8000.";
            string sourceDocs = "";
            try
            {
                var payload = new
                {
                    session_id = session.Id,
                    subject_id = subjectId,
                    query = content,
                    history = recentHistory
                };
                var json = System.Text.Json.JsonSerializer.Serialize(payload);
                var stringContent = new System.Net.Http.StringContent(json, System.Text.Encoding.UTF8, "application/json");

                using var client = _httpClientFactory.CreateClient("AiService");
                var response = await client.PostAsync("/api/chat/ask", stringContent);

                if (response.IsSuccessStatusCode)
                {
                    var responseString = await response.Content.ReadAsStringAsync();
                    using var jsonDoc = System.Text.Json.JsonDocument.Parse(responseString);
                    answer = jsonDoc.RootElement.GetProperty("answer").GetString() ?? "Phản hồi rỗng";
                    
                    if (jsonDoc.RootElement.TryGetProperty("sources", out var sourcesEl))
                    {
                        var sourcesList = sourcesEl.EnumerateArray()
                            .Select(s => s.GetString())
                            .Where(s => !string.IsNullOrEmpty(s));
                        sourceDocs = string.Join(", ", sourcesList);
                    }
                }
                else
                {
                    throw new HttpRequestException($"AI Engine returned HTTP {(int)response.StatusCode}.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("AI Chat Error: " + ex.Message);
                if (IsAjaxRequest())
                {
                    Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
                    return Json(new
                    {
                        success = false,
                        message = "AI Engine chua san sang hoac dang bi loi. Vui long cho trang thai AI san sang roi gui lai."
                    });
                }
            }

            var botMsg = new ChatMessage
            {
                SessionId = session.Id,
                Role = "Bot",
                Content = answer,
                SourceDocuments = sourceDocs ?? "",
                Timestamp = DateTime.UtcNow
            };
            _context.ChatMessages.Add(userMsg);
            _context.ChatMessages.Add(botMsg);
            await _context.SaveChangesAsync();
            await _notifier.PublishAsync(
                "ChatAnswered",
                "Chatbot tra loi",
                $"Da tra loi cau hoi trong mon #{subjectId}.",
                new { subjectId, userMessageId = userMsg.Id, botMessageId = botMsg.Id });

            if (IsAjaxRequest())
            {
                return Json(new
                {
                    success = true,
                    user = new
                    {
                        id = userMsg.Id,
                        content = userMsg.Content
                    },
                    bot = new
                    {
                        id = botMsg.Id,
                        content = botMsg.Content,
                        sourceDocuments = botMsg.SourceDocuments
                    }
                });
            }

            return RedirectToAction("Index", new { subjectId });
        }

        [HttpGet]
        public async Task<IActionResult> AiStatus()
        {
            try
            {
                using var client = _httpClientFactory.CreateClient("AiService");
                using var response = await client.GetAsync("/");
                if (response.IsSuccessStatusCode)
                {
                    return Json(new
                    {
                        ready = true,
                        status = "ready",
                        message = "AI Engine san sang"
                    });
                }

                return StatusCode(StatusCodes.Status503ServiceUnavailable, new
                {
                    ready = false,
                    status = "error",
                    message = $"AI Engine tra ve HTTP {(int)response.StatusCode}"
                });
            }
            catch (Exception ex)
            {
                return StatusCode(StatusCodes.Status503ServiceUnavailable, new
                {
                    ready = false,
                    status = "starting",
                    message = "AI Engine chua san sang: " + ex.Message
                });
            }
        }

        private bool IsAjaxRequest()
        {
            return string.Equals(Request.Headers["X-Requested-With"], "XMLHttpRequest", StringComparison.OrdinalIgnoreCase)
                || Request.Headers.Accept.Any(h => h?.Contains("application/json", StringComparison.OrdinalIgnoreCase) == true);
        }
    }
}
