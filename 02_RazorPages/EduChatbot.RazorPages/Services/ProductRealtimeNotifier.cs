using EduChatbot.RazorPages.Hubs;
using Microsoft.AspNetCore.SignalR;

namespace EduChatbot.RazorPages.Services;

public class ProductRealtimeNotifier
{
    private readonly IHubContext<ProductHub> _hubContext;
    private readonly ProductActivityFeed _feed;

    public ProductRealtimeNotifier(IHubContext<ProductHub> hubContext, ProductActivityFeed feed)
    {
        _hubContext = hubContext;
        _feed = feed;
    }

    public async Task PublishAsync(string kind, string title, string message, object? payload = null)
    {
        var activity = _feed.Add(kind, title, message);
        await _hubContext.Clients.All.SendAsync("ReceiveActivity", new
        {
            time = activity.Time.ToString("HH:mm:ss"),
            activity.Kind,
            activity.Title,
            activity.Message,
            Payload = payload
        });
    }
}

