using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;

namespace EduChatbot.Web.Models
{
    public class Subject
    {
        [Key]
        public int Id { get; set; }

        [Required]
        [MaxLength(100)]
        public string Name { get; set; }

        [Required]
        [MaxLength(20)]
        public string Code { get; set; }

        public ICollection<Document>? Documents { get; set; }
        public ICollection<ChatSession>? ChatSessions { get; set; }
    }
}
