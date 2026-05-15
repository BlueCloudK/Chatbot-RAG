using System.Collections.Concurrent;

namespace EduChatbot.ProductGroup.Services;

public record ProductActivity(
    DateTimeOffset Time,
    string Kind,
    string Title,
    string Message);

public class ProductActivityFeed
{
    private readonly ConcurrentQueue<ProductActivity> _activities = new();

    public IReadOnlyList<ProductActivity> Latest(int count = 20)
    {
        return _activities
            .Reverse()
            .Take(count)
            .ToList();
    }

    public ProductActivity Add(string kind, string title, string message)
    {
        var activity = new ProductActivity(DateTimeOffset.Now, kind, title, message);
        _activities.Enqueue(activity);

        while (_activities.Count > 80 && _activities.TryDequeue(out _))
        {
        }

        return activity;
    }
}
