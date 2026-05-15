using EduChatbot.Web.Data;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.Web.Services;

public class ProductWorkerService : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ProductRealtimeNotifier _notifier;
    private readonly ILogger<ProductWorkerService> _logger;

    public ProductWorkerService(
        IServiceScopeFactory scopeFactory,
        ProductRealtimeNotifier notifier,
        ILogger<ProductWorkerService> logger)
    {
        _scopeFactory = scopeFactory;
        _notifier = notifier;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = _scopeFactory.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

                var subjectCount = await db.Subjects.CountAsync(stoppingToken);
                var documentCount = await db.Documents.CountAsync(stoppingToken);
                var indexedCount = await db.Documents.CountAsync(d => d.IsIndexed, stoppingToken);
                var chatCount = await db.ChatMessages.CountAsync(stoppingToken);

                await _notifier.PublishAsync(
                    "WorkerHeartbeat",
                    "Worker Service",
                    $"Dang theo doi {subjectCount} mon, {indexedCount}/{documentCount} tai lieu da index, {chatCount} tin nhan.",
                    new { subjectCount, documentCount, indexedCount, chatCount });
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Product worker heartbeat failed.");
            }

            await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken);
        }
    }
}

