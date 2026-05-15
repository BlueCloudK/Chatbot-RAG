using EduChatbot.RazorPages.Data;
using EduChatbot.RazorPages.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.RazorPages.Pages.Subjects;

public class IndexModel : PageModel
{
    private readonly ApplicationDbContext _context;

    public IndexModel(ApplicationDbContext context)
    {
        _context = context;
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
        }

        return RedirectToPage();
    }
}
