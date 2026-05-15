using System.Collections.Generic;
using EduChatbot.RazorPages.Models;

namespace EduChatbot.RazorPages.Models.ViewModels
{
    public class ChatViewModel
    {
        public ChatSession? CurrentSession { get; set; }
        public IEnumerable<Document>? CurrentDocuments { get; set; }
    }
}

