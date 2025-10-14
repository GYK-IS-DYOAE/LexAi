import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  MessageSquare,
  Scale,
  Shield,
  ShieldCheck,
  Users,
  MessageCircle,
  LogOut,
  Menu,
  X,
  Clock,
  MoreVertical,
  Trash2,
} from "lucide-react";
import { useAuthStore } from "@/features/auth/useAuthStore";

export default function SideBar() {
  const { user, logout } = useAuthStore();

  // Menü genişliği
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("lexai_sb_collapsed") === "1";
  });

  // Sohbet geçmişi
  const [chatHistory, setChatHistory] = useState<
    { id: number; title: string }[]
  >([]);

  // Silme menüsü için açık olan sohbet id’si
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);

  useEffect(() => {
    const saved = JSON.parse(localStorage.getItem("chat_history") || "[]");
    setChatHistory(saved);
  }, []);

  const location = useLocation();
  const isAdmin = !!user?.is_admin;
  const onAdminPage = /^\/admin(?:\/|$)/.test(location.pathname);

  const toggleCollapse = () =>
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("lexai_sb_collapsed", next ? "1" : "0");
      return next;
    });

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  // ✅ Sohbet silme fonksiyonu
  const handleDeleteChat = (id: number) => {
    const full = JSON.parse(localStorage.getItem("chat_history_full") || "[]");
    const short = JSON.parse(localStorage.getItem("chat_history") || "[]");

    const updatedFull = full.filter((chat: any) => chat.id !== id);
    const updatedShort = short.filter((chat: any) => chat.id !== id);

    localStorage.setItem("chat_history_full", JSON.stringify(updatedFull));
    localStorage.setItem("chat_history", JSON.stringify(updatedShort));

    setChatHistory(updatedShort);
    setOpenMenuId(null);

    // Eğer silinen sohbet açık olan sohbetse, ana sayfaya yönlendir
    if (window.location.search.includes(`id=${id}`)) {
      window.history.replaceState(null, "", "/chat");
      window.location.reload();
    }
  };

  // ✅ Yeni sohbet başlatma — ortada bile tıklansa çalışır
  const handleNewChatClick = () => {
    try {
      const messages = JSON.parse(
        sessionStorage.getItem("lexai_current_messages") || "[]"
      );

      // Eğer mevcut sohbette mesaj varsa önce kaydet
      if (messages.length > 0) {
        const fullChats =
          JSON.parse(localStorage.getItem("chat_history_full") || "[]") || [];
        const title =
          (messages[0]?.content || "Yeni sohbet")
            .trim()
            .split(/\s+/)
            .slice(0, 3)
            .join(" ") + "...";
        const newChat = {
          id: Date.now(),
          title,
          messages,
        };
        const updatedAll = [...fullChats, newChat];
        localStorage.setItem("chat_history_full", JSON.stringify(updatedAll));

        const shortList = updatedAll.map((c) => ({
          id: c.id,
          title: c.title,
        }));
        localStorage.setItem("chat_history", JSON.stringify(shortList));
      }
    } catch (err) {
      console.error("Sohbet kaydedilirken hata:", err);
    }

    // ✅ Yeni sohbet başlat
    const newId = Date.now();
    window.history.pushState(null, "", `/chat?id=${newId}`);
    window.location.reload(); // 💥 garantili yeniden yükleme
  };

  const userMenu = [
    {
      name: "Yeni Sohbet",
      path: "#",
      icon: MessageSquare,
      onClick: handleNewChatClick,
    },
    { name: "Benzer Davalar", path: "/similar", icon: Scale },
  ];

  const adminMenu = [
    { name: "Admin Dashboard", path: "/admin", icon: ShieldCheck },
    { name: "Kullanıcılar", path: "/admin/users", icon: Users },
    { name: "Geri Bildirimler", path: "/admin/feedbacks", icon: MessageCircle },
  ];

  const primaryItems =
    isAdmin && onAdminPage
      ? adminMenu
      : isAdmin
      ? [...userMenu, { name: "Admin Paneli", path: "/admin", icon: Shield }]
      : userMenu;

  return (
    <aside
      className={`h-screen bg-[hsl(var(--card))] border-r border-[hsl(var(--border))] transition-[width] duration-300 ease-in-out
      ${collapsed ? "w-16" : "w-72"} flex flex-col flex-none shrink-0 overflow-hidden`}
    >
      {/* Üst Kısım */}
      <div className="h-14 px-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
        {!collapsed && (
          <span
            onClick={() => (window.location.href = "/home")}
            className="text-lg font-extrabold text-[hsl(var(--lex-primary))] cursor-pointer hover:opacity-90 transition select-none whitespace-nowrap"
            title="Ana Sayfaya Git"
          >
            LexAI
          </span>
        )}
        <button
          onClick={toggleCollapse}
          className="p-2 rounded-md hover:bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] transition"
          aria-label="Menüyü daralt"
        >
          {collapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
      </div>

      {/* Menü */}
      <nav className="py-4 flex-none">
        <ul className="space-y-1">
          {primaryItems.map(({ name, path, icon: Icon, onClick }) => (
            <li key={name} className="px-2">
              <NavLink
                to={path === "#" ? "#" : path}
                end={path === "/admin"}
                onClick={(e) => {
                  if (onClick) {
                    e.preventDefault();
                    onClick();
                  }
                }}
                className={({ isActive }) =>
                  `flex h-10 items-center ${
                    collapsed ? "justify-center" : "gap-3 px-3"
                  } rounded-xl text-sm font-medium transition-all duration-200 whitespace-nowrap
                  border ${
                    isActive
                      ? "border-[hsl(var(--lex-primary))] bg-[hsl(var(--lex-primary))] text-white shadow-[0_0_8px_rgba(185,28,28,0.4)]"
                      : "border-transparent text-[hsl(var(--foreground))] hover:border-[hsl(var(--lex-primary))] hover:bg-[hsl(var(--lex-primary))/0.12] hover:text-[hsl(var(--lex-primary))]"
                  }`
                }
              >
                <Icon size={18} className="flex-none" />
                {!collapsed && <span className="truncate">{name}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* ✅ Geçmiş Sohbetler (scrollable) */}
      {!collapsed && !onAdminPage && (
        <div className="px-3 mt-3 flex flex-col flex-1 overflow-hidden">
          <div className="flex items-center gap-2 px-2 py-1.5 flex-none">
            <Clock size={16} className="text-[hsl(var(--muted-foreground))]" />
            <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase">
              Geçmiş
            </span>
          </div>

          {/* 🔽 Kaydırılabilir geçmiş listesi */}
          <div
            className="flex-1 overflow-y-auto pr-1 mt-2 space-y-1
                       scrollbar-thin scrollbar-thumb-[hsl(var(--muted-foreground))/0.3]
                       scrollbar-thumb-rounded-full scrollbar-track-transparent
                       hover:scrollbar-thumb-[hsl(var(--muted-foreground))/0.5]"
          >
            {chatHistory.length > 0 ? (
              chatHistory.map((chat) => (
                <div
                  key={chat.id}
                  className="group relative flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer select-none
                      text-[hsl(var(--muted-foreground))] transition-all duration-200
                      border border-transparent hover:border-[hsl(var(--lex-primary))/0.3]
                      hover:bg-[hsl(var(--lex-primary))/0.08] hover:text-[hsl(var(--foreground))]"
                >
                  <div
                    className="truncate pr-6"
                    onClick={() =>
                      (window.location.href = `/chat?id=${chat.id}`)
                    }
                  >
                    {chat.title}
                  </div>

                  {/* Üç Nokta Menüsü */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpenMenuId((prev) =>
                        prev === chat.id ? null : chat.id
                      );
                    }}
                    className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-[hsl(var(--muted))]"
                  >
                    <MoreVertical size={16} />
                  </button>

                  {/* Silme Menüsü */}
                  {openMenuId === chat.id && (
                    <div
                      className="absolute right-6 top-1/2 -translate-y-1/2 bg-[hsl(var(--popover))] border border-[hsl(var(--border))]
                      rounded-md shadow-md z-50"
                    >
                      <button
                        onClick={() => handleDeleteChat(chat.id)}
                        className="flex items-center gap-2 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 w-full text-left"
                      >
                        <Trash2 size={12} /> Sil
                      </button>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="text-xs text-[hsl(var(--muted-foreground))] px-2">
                Henüz sohbet yok.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Alt Kısım */}
      <div className="mt-auto border-t border-[hsl(var(--border))] p-3 flex items-center justify-between flex-none">
        {!collapsed && (
          <div className="flex items-center gap-2 px-2 py-1 rounded-lg transition hover:bg-[hsl(var(--lex-primary))/0.15] select-none">
            <img
              src={`https://api.dicebear.com/8.x/initials/svg?seed=${
                user?.first_name || "U"
              }${user?.last_name || "S"}&backgroundColor=b91c1c&textColor=ffffff`}
              alt="avatar"
              className="w-8 h-8 rounded-full ring-2 ring-[hsl(var(--lex-primary))]/40 shadow-sm"
            />
            <div className="min-w-0">
              <p className="text-sm font-medium leading-tight truncate">
                {`${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() ||
                  "Kullanıcı"}
              </p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Aktif
              </p>
            </div>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="p-2 rounded-lg bg-[hsl(var(--lex-primary))] text-white hover:brightness-110 transition"
          aria-label="Çıkış"
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
