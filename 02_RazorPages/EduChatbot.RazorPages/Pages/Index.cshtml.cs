using EduChatbot.RazorPages.Data;
using EduChatbot.RazorPages.Models;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace EduChatbot.RazorPages.Pages;

public class IndexModel : PageModel
{
    private readonly ApplicationDbContext _context;

    public IndexModel(ApplicationDbContext context)
    {
        _context = context;
    }

    public IList<Subject> Subjects { get; private set; } = new List<Subject>();

    public async Task OnGetAsync()
    {
        Subjects = await _context.Subjects
            .Include(s => s.Documents)
            .OrderBy(s => s.Name)
            .ToListAsync();
    }
}
