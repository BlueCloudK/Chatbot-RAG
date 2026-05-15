using System.Collections.Generic;
using EduChatbot.Web.Models;

namespace EduChatbot.Web.Models.ViewModels
{
    public class ChatViewModel
    {
        public ChatSession? CurrentSession { get; set; }
        public IEnumerable<Document>? CurrentDocuments { get; set; }
    }
}
