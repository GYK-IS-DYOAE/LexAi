import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { ShieldCheck, Users, MessageSquare } from "lucide-react";

export default function AdminDashboard() {
  const navigate = useNavigate();

  const cards = [
    {
      title: "Kullanıcı Yönetimi",
      description: "Sistemdeki kullanıcıları görüntüle, admin yetkisi ver veya kaldır.",
      icon: Users,
      path: "/admin/users",
    },
    {
      title: "Geri Bildirimler",
      description: "Kullanıcıların bıraktığı yorumları ve oyları görüntüle.",
      icon: MessageSquare,
      path: "/admin/feedbacks",
    },
  ];

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-[hsl(var(--lex-primary))] flex items-center gap-2 mb-8">
        <ShieldCheck className="w-6 h-6" />
        Admin Dashboard
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cards.map(({ title, description, icon: Icon, path }) => (
          <Card
            key={path}
            onClick={() => navigate(path)}
            className="p-6 cursor-pointer rounded-2xl bg-[hsl(var(--card))] border border-[hsl(var(--border))] shadow-md hover:shadow-[0_0_8px_rgba(185,28,28,0.4)] transition-all hover:-translate-y-1"
          >
            <div className="flex items-center gap-3 mb-2">
              <Icon className="w-5 h-5 text-[hsl(var(--lex-primary))]" />
              <h2 className="text-lg font-semibold">{title}</h2>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">{description}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
