using System.Collections.Generic;
using EduChatbot.ProductGroup.Models;

namespace EduChatbot.ProductGroup.Models.ViewModels
{
    public class ChatViewModel
    {
        public ChatSession? CurrentSession { get; set; }
        public IEnumerable<Document>? CurrentDocuments { get; set; }
    }
}


