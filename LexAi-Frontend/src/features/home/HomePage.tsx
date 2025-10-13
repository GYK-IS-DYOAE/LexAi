import { useAuthStore } from "@/features/auth/useAuthStore";
import { MessageSquare, Scale, Shield } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function HomePage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const features = [
    {
      title: "Sohbet",
      desc: "Vaka özetinizi anlatın, yönlendirme ve argüman önerileri alın.",
      icon: <MessageSquare size={24} />,
      path: "/chat",
    },
    {
      title: "Benzer Davalar",
      desc: "Emsal kararları ve ilgili kanun maddelerini görün.",
      icon: <Scale size={24} />,
      path: "/similar",
    },
  ];

  // admin ise admin kartını da ekle
  if (user?.is_admin) {
    features.push({
      title: "Admin Paneli",
      desc: "Kullanıcıları yönetin, geri bildirimleri görüntüleyin.",
      icon: <Shield size={24} />,
      path: "/admin",
    });
  }

  return (
    <div className="max-w-5xl mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">Hoş geldiniz</h1>
      <p className="text-sm text-muted-foreground mb-10">
        Başlamak için bir özellik seçin. LexAI, hızlı ve doğru hukuk asistanınızdır.
      </p>

      <div className="grid md:grid-cols-3 gap-6">
        {features.map((item) => (
          <div
            key={item.title}
            onClick={() => navigate(item.path)}
            className="cursor-pointer rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 hover:border-[hsl(var(--lex-primary))]/50 hover:shadow-md transition"
          >
            <div className="flex items-center gap-3 mb-4 text-[hsl(var(--lex-primary))]">
              {item.icon}
              <h2 className="text-lg font-semibold">{item.title}</h2>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {item.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
