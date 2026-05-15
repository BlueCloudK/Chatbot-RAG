using EduChatbot.RazorPages.Data;
using EduChatbot.RazorPages.Models;
using EduChatbot.RazorPages.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.RazorPages.Pages.Subjects;

public class IndexModel : PageModel
{
    private readonly ApplicationDbContext _context;
    private readonly ProductRealtimeNotifier _notifier;

    public IndexModel(ApplicationDbContext context, ProductRealtimeNotifier notifier)
    {
        _context = context;
        _notifier = notifier;
    }

    public IList<Subject> Subjects { get; private set; } = new List<Subject>();

    [BindProperty]
    public Subject Input { get; set; } = new();

    public async Task OnGetAsync()
    {
        Subjects = await _context.Subjects
            .Include(s => s.Documents)
            .OrderBy(s => s.Name)
            .ToListAsync();
    }

    public async Task<IActionResult> OnPostCreateAsync()
    {
        if (!ModelState.IsValid)
        {
            await OnGetAsync();
            return Page();
        }

        _context.Subjects.Add(Input);
        await _context.SaveChangesAsync();
        await _notifier.PublishAsync(
            "SubjectCreated",
            "Them mon hoc",
            $"Da them mon {Input.Name} ({Input.Code}).",
            new { Input.Id, Input.Name, Input.Code });

        return RedirectToPage();
    }

    public async Task<IActionResult> OnPostEditAsync(int id, string name, string code)
    {
        var subject = await _context.Subjects.FindAsync(id);
        if (subject == null)
            return RedirectToPage();

        subject.Name = name.Trim();
        subject.Code = code.Trim();
        await _context.SaveChangesAsync();
        await _notifier.PublishAsync(
            "SubjectUpdated",
            "Sua mon hoc",
            $"Da cap nhat mon {subject.Name} ({subject.Code}).",
            new { subject.Id, subject.Name, subject.Code });

        return RedirectToPage();
    }

    public async Task<IActionResult> OnPostDeleteAsync(int id)
    {
        var subject = await _context.Subjects
            .Include(s => s.Documents)
            .Include(s => s.ChatSessions!)
                .ThenInclude(s => s.Messages)
            .FirstOrDefaultAsync(s => s.Id == id);

        if (subject != null)
        {
            _context.Subjects.Remove(subject);
            await _context.SaveChangesAsync();
            await _notifier.PublishAsync(
                "SubjectDeleted",
                "Xoa mon hoc",
                $"Da xoa mon {subject.Name} ({subject.Code}).",
                new { subject.Id, subject.Name, subject.Code });
        }

        return RedirectToPage();
    }
}

