using EduChatbot.Web.Data;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllersWithViews();
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

// HttpClient cho gọi Python AI API (tránh socket exhaustion)
builder.Services.AddHttpClient("AiService", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiService:BaseUrl"] ?? "http://127.0.0.1:8000");
    client.Timeout = TimeSpan.FromMinutes(10);
});

// Tự động khởi chạy Python AI Backend khi Web App khởi động
builder.Services.AddHostedService<EduChatbot.Web.Services.PythonAIServiceRunner>();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    db.Database.Migrate();
    db.Database.ExecuteSqlRaw("""
        IF COL_LENGTH('Documents', 'ChunkCount') IS NULL
            ALTER TABLE Documents ADD ChunkCount int NOT NULL CONSTRAINT DF_Documents_ChunkCount DEFAULT 0;
        IF COL_LENGTH('Documents', 'IndexStatus') IS NULL
            ALTER TABLE Documents ADD IndexStatus nvarchar(50) NOT NULL CONSTRAINT DF_Documents_IndexStatus DEFAULT N'Pending';
        IF COL_LENGTH('Documents', 'IndexMessage') IS NULL
            ALTER TABLE Documents ADD IndexMessage nvarchar(1000) NULL;
        IF COL_LENGTH('Documents', 'IndexedAt') IS NULL
            ALTER TABLE Documents ADD IndexedAt datetime2 NULL;
    """);
}

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();

app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");


app.Run();
