using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;

namespace EduChatbot.RazorPages.Models
{
    public class Subject
    {
        [Key]
        public int Id { get; set; }

        [Required]
        [MaxLength(100)]
        public string Name { get; set; } = string.Empty;

        [Required]
        [MaxLength(20)]
        public string Code { get; set; } = string.Empty;

        public ICollection<Document>? Documents { get; set; }
        public ICollection<ChatSession>? ChatSessions { get; set; }
    }
}


