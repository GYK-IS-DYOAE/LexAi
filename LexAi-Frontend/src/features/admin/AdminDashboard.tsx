import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { ShieldCheck, Users, MessageSquare } from "lucide-react";

export default function AdminDashboard() {
  const navigate = useNavigate();

  const cards = [
    {
      title: "Kullanıcı Yönetimi",
      description: "Sistemdeki kullanıcıları görüntüle, admin yetkisi ver veya kaldır.",
      icon: <Users size={24} />,
      path: "/admin/users",
    },
    {
      title: "Geri Bildirimler",
      description: "Kullanıcıların bıraktığı yorumları ve oyları görüntüle.",
      icon: <MessageSquare size={24} />,
      path: "/admin/feedbacks",
    },
  ];

  return (
    <div className="max-w-5xl mx-auto py-10 px-8 w-full">
      <h1 className="text-2xl font-bold text-[hsl(var(--lex-primary))] flex items-center gap-2 mb-8">
        <ShieldCheck className="w-6 h-6" />
        Admin Dashboard
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cards.map((item) => (
          <Card
            key={item.title}
            onClick={() => navigate(item.path)}
            className="cursor-pointer rounded-2xl border border-[hsl(var(--border))] 
                       bg-[hsl(var(--card))] p-6 
                       hover:border-[hsl(var(--lex-primary))]/50 
                       transition"
          >
            <div className="flex items-center gap-3 mb-4 text-[hsl(var(--lex-primary))]">
              {item.icon}
              <h2 className="text-lg font-semibold text-[hsl(var(--foreground))]">
                {item.title}
              </h2>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))] leading-relaxed">
              {item.description}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
