using EduChatbot.RazorPages.Data;
using EduChatbot.RazorPages.Services;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.RazorPages.Pages;

public class DashboardModel : PageModel
{
    private readonly ApplicationDbContext _context;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ProductActivityFeed _activityFeed;

    public DashboardModel(ApplicationDbContext context, IHttpClientFactory httpClientFactory, ProductActivityFeed activityFeed)
    {
        _context = context;
        _httpClientFactory = httpClientFactory;
        _activityFeed = activityFeed;
    }

    public int SubjectCount { get; private set; }
    public int DocumentCount { get; private set; }
    public int IndexedCount { get; private set; }
    public int ChatCount { get; private set; }
    public bool AiReady { get; private set; }
    public IReadOnlyList<ProductActivity> Activities { get; private set; } = [];

    public async Task OnGetAsync()
    {
        SubjectCount = await _context.Subjects.CountAsync();
        DocumentCount = await _context.Documents.CountAsync();
        IndexedCount = await _context.Documents.CountAsync(d => d.IsIndexed);
        ChatCount = await _context.ChatMessages.CountAsync();

        try
        {
            using var client = _httpClientFactory.CreateClient("AiService");
            using var response = await client.GetAsync("/");
            AiReady = response.IsSuccessStatusCode;
        }
        catch
        {
            AiReady = false;
        }

        Activities = _activityFeed.Latest();
    }
}

