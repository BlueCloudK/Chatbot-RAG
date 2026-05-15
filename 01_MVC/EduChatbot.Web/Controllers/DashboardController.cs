using EduChatbot.Web.Data;
using EduChatbot.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.Web.Controllers;

public class DashboardController : Controller
{
    private readonly ApplicationDbContext _context;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ProductActivityFeed _activityFeed;

    public DashboardController(
        ApplicationDbContext context,
        IHttpClientFactory httpClientFactory,
        ProductActivityFeed activityFeed)
    {
        _context = context;
        _httpClientFactory = httpClientFactory;
        _activityFeed = activityFeed;
    }

    public async Task<IActionResult> Index()
    {
        var model = new DashboardViewModel
        {
            SubjectCount = await _context.Subjects.CountAsync(),
            DocumentCount = await _context.Documents.CountAsync(),
            IndexedCount = await _context.Documents.CountAsync(d => d.IsIndexed),
            ChatCount = await _context.ChatMessages.CountAsync(),
            Activities = _activityFeed.Latest()
        };

        try
        {
            using var client = _httpClientFactory.CreateClient("AiService");
            using var response = await client.GetAsync("/");
            model.AiReady = response.IsSuccessStatusCode;
        }
        catch
        {
            model.AiReady = false;
        }

        return View(model);
    }
}

public class DashboardViewModel
{
    public int SubjectCount { get; set; }
    public int DocumentCount { get; set; }
    public int IndexedCount { get; set; }
    public int ChatCount { get; set; }
    public bool AiReady { get; set; }
    public IReadOnlyList<ProductActivity> Activities { get; set; } = [];
}
