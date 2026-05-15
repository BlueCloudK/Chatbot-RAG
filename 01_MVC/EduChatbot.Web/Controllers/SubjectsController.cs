using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using EduChatbot.Web.Data;
using EduChatbot.Web.Models;
using EduChatbot.Web.Services;

namespace EduChatbot.Web.Controllers
{
    public class SubjectsController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly ProductRealtimeNotifier _notifier;

        public SubjectsController(ApplicationDbContext context, ProductRealtimeNotifier notifier)
        {
            _context = context;
            _notifier = notifier;
        }

        // GET: Subjects
        public async Task<IActionResult> Index()
        {
            return View(await _context.Subjects.ToListAsync());
        }

        // GET: Subjects/Create
        public IActionResult Create()
        {
            return View();
        }

        // POST: Subjects/Create
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Create([Bind("Id,Name,Code")] Subject subject)
        {
            if (ModelState.IsValid)
            {
                _context.Add(subject);
                await _context.SaveChangesAsync();
                await _notifier.PublishAsync(
                    "SubjectCreated",
                    "Them mon hoc",
                    $"Da them mon {subject.Name} ({subject.Code}).",
                    new { subject.Id, subject.Name, subject.Code });
                return RedirectToAction("Index", "Home");
            }
            return RedirectToAction("Index", "Home");
        }

        // GET: Subjects/Edit/5
        public async Task<IActionResult> Edit(int? id)
        {
            if (id == null) return NotFound();
            var subject = await _context.Subjects.FindAsync(id);
            if (subject == null) return NotFound();
            return View(subject);
        }

        // POST: Subjects/Edit/5
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Edit(int id, [Bind("Id,Name,Code")] Subject subject)
        {
            if (id != subject.Id) return NotFound();

            if (ModelState.IsValid)
            {
                try
                {
                    _context.Update(subject);
                    await _context.SaveChangesAsync();
                    await _notifier.PublishAsync(
                        "SubjectUpdated",
                        "Sua mon hoc",
                        $"Da cap nhat mon {subject.Name} ({subject.Code}).",
                        new { subject.Id, subject.Name, subject.Code });
                }
                catch (DbUpdateConcurrencyException)
                {
                    if (!SubjectExists(subject.Id)) return NotFound();
                    else throw;
                }
                return RedirectToAction(nameof(Index));
            }
            return View(subject);
        }

        // GET: Subjects/Delete/5
        public async Task<IActionResult> Delete(int? id)
        {
            if (id == null) return NotFound();
            var subject = await _context.Subjects.FirstOrDefaultAsync(m => m.Id == id);
            if (subject == null) return NotFound();
            return View(subject);
        }

        // POST: Subjects/Delete/5
        [HttpPost, ActionName("Delete")]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> DeleteConfirmed(int id)
        {
            var subject = await _context.Subjects.FindAsync(id);
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
            return RedirectToAction(nameof(Index));
        }

        private bool SubjectExists(int id)
        {
            return _context.Subjects.Any(e => e.Id == id);
        }
    }
}
