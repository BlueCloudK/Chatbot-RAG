using EduChatbot.ProductGroup.Data;
using EduChatbot.ProductGroup.Hubs;
using EduChatbot.ProductGroup.Models;
using EduChatbot.ProductGroup.Services;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorPages();
builder.Services.AddSignalR();
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

builder.Services.AddHttpClient("AiService", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiService:BaseUrl"] ?? "http://127.0.0.1:8000");
    client.Timeout = TimeSpan.FromMinutes(30);
});

builder.Services.AddHostedService<PythonAIServiceRunner>();
builder.Services.AddSingleton<ProductActivityFeed>();
builder.Services.AddSingleton<ProductRealtimeNotifier>();
builder.Services.AddHostedService<ProductWorkerService>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
}

app.UseRouting();
app.UseAuthorization();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    db.Database.EnsureCreated();
    EnsureDocumentIndexColumns(db);
    SeedSubjects(db);
}

app.MapStaticAssets();
app.MapHub<ProductHub>("/hubs/product");
app.MapRazorPages()
   .WithStaticAssets();

app.Run();

static void EnsureDocumentIndexColumns(ApplicationDbContext db)
{
    var sql = @"
IF COL_LENGTH('Documents', 'IndexStatus') IS NULL
    ALTER TABLE [Documents] ADD [IndexStatus] nvarchar(50) NOT NULL CONSTRAINT DF_Documents_IndexStatus DEFAULT N'Pending';
IF COL_LENGTH('Documents', 'IndexMessage') IS NULL
    ALTER TABLE [Documents] ADD [IndexMessage] nvarchar(1000) NULL;
IF COL_LENGTH('Documents', 'IndexedAt') IS NULL
    ALTER TABLE [Documents] ADD [IndexedAt] datetime2 NULL;
IF COL_LENGTH('Documents', 'ChunkCount') IS NULL
    ALTER TABLE [Documents] ADD [ChunkCount] int NOT NULL CONSTRAINT DF_Documents_ChunkCount DEFAULT 0;";

    try
    {
        db.Database.ExecuteSqlRaw(sql);
    }
    catch (SqlException)
    {
    }
}

static void SeedSubjects(ApplicationDbContext db)
{
    if (db.Subjects.Any())
        return;

    db.Subjects.AddRange(
        new Subject { Name = "Software Testing", Code = "SWT" },
        new Subject { Name = "Algorithms", Code = "ALG" });
    db.SaveChanges();
}
