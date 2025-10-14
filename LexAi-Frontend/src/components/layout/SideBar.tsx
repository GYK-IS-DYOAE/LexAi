import { useState, Fragment } from "react";
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
} from "lucide-react";
import { useAuthStore } from "@/features/auth/useAuthStore";

export default function SideBar() {
  const { user, logout } = useAuthStore();

  // Menü genişliği kullanıcı tercihi (kalıcı)
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("lexai_sb_collapsed") === "1";
  });

  const location = useLocation();

  const isAdmin = !!user?.is_admin;
  const onAdminPage = /^\/admin(?:\/|$)/.test(location.pathname); // /admin ve alt yollar

  const toggleCollapse = () =>
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("lexai_sb_collapsed", next ? "1" : "0");
      return next;
    });

  // Menüler
  const userMenu = [
    { name: "Yeni Sohbet", path: "/chat", icon: MessageSquare },
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

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

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
      <nav className="py-4">
        <ul className="space-y-1">
          {primaryItems.map(({ name, path, icon: Icon }) => (
            <li key={path} className="px-2">
              <NavLink
                to={path}
                end={path === "/admin"} // /admin için exact
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

      {/* Geçmiş (admin panelinde gizli) */}
      {!collapsed && !onAdminPage && (
        <div className="px-3 mt-3">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <Clock size={16} className="text-[hsl(var(--muted-foreground))]" />
            <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase">
              Geçmiş
            </span>
          </div>

          <div className="space-y-1 mt-2">
            {[1, 2, 3, 4].map((i) => (
              <Fragment key={i}>
                <div
                  className={`rounded-lg px-3 py-2 text-sm cursor-pointer select-none
                    text-[hsl(var(--muted-foreground))] transition-all duration-200
                    border border-transparent
                    hover:border-[hsl(var(--lex-primary))/0.3]
                    hover:bg-[hsl(var(--lex-primary))/0.08]
                    hover:text-[hsl(var(--foreground))]`}
                >
                  Örnek sohbet başlığı {i}
                </div>
              </Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Alt Kısım: Kullanıcı */}
      <div className="mt-auto border-t border-[hsl(var(--border))] p-3 flex items-center justify-between">
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
