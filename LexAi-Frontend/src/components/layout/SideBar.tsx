import { useState, Fragment } from "react";
import { NavLink } from "react-router-dom";
import { MessageSquare, Scale, Shield, LogOut, Menu, X, Clock } from "lucide-react";
import { useAuthStore } from "@/features/auth/useAuthStore";

export default function SideBar() {
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const primaryItems = [
    { name: "Yeni Sohbet", path: "/chat", icon: MessageSquare },
    { name: "Benzer Davalar", path: "/similar", icon: Scale },
  ];
  if (user?.is_admin)
    primaryItems.push({ name: "Admin Paneli", path: "/admin", icon: Shield });

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  return (
    <aside
      className={`h-screen bg-[hsl(var(--card))] border-r border-[hsl(var(--border))] transition-[width] duration-300 ease-in-out
      ${collapsed ? "w-16" : "w-72"} flex flex-col`}
    >
      {/* Üst Kısım: Logo ve Menü */}
      <div className="h-14 px-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
        {!collapsed && (
            <span
            onClick={() => (window.location.href = "/home")}
            className="text-lg font-extrabold text-[hsl(var(--lex-primary))] cursor-pointer hover:opacity-90 transition"
            title="Ana Sayfaya Git"
            >
            LexAI
            </span>
        )}
        <button
            onClick={() => setCollapsed((s) => !s)}
            className="p-2 rounded-md hover:bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]"
            aria-label="Menüyü daralt"
        >
            {collapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
        </div>


      {/* Menü */}
      <nav className="py-4">
        <ul className="space-y-1">
          {primaryItems.map(({ name, path, icon: Icon }) => (
            <li key={path}>
              <NavLink
                to={path}
                className={({ isActive }) =>
                  `mx-2 flex items-center ${
                    collapsed ? "justify-center" : "gap-3 px-3"
                  } py-2 rounded-xl text-sm font-medium transition
                   ${
                     isActive
                       ? "bg-[hsl(var(--lex-primary))] text-white"
                       : "text-[hsl(var(--foreground))] hover:bg-[hsl(var(--muted))]"
                   }`
                }
              >
                <Icon size={18} />
                {!collapsed && <span>{name}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Geçmiş */}
      {!collapsed && (
        <div className="px-3 mt-3">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <Clock size={16} className="text-[hsl(var(--muted-foreground))]" />
            <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase">
              Geçmiş
            </span>
          </div>
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <Fragment key={i}>
                <div
                  className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]/60 hover:bg-[hsl(var(--muted))] cursor-pointer transition h-10 px-3 flex items-center text-sm text-[hsl(var(--muted-foreground))]"
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
            <div className="flex items-center gap-2 select-none">
            <img
                src={`https://api.dicebear.com/8.x/initials/svg?seed=${
                user?.first_name || "U"
                }${user?.last_name || "S"}&backgroundColor=b91c1c&textColor=ffffff`}
                alt="avatar"
                className="w-8 h-8 rounded-full ring-2 ring-[hsl(var(--lex-primary))]/50"
            />
            <div>
                <p className="text-sm font-medium leading-tight">
                {`${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() ||
                    "Kullanıcı"}
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Aktif</p>
            </div>
            </div>
        )}

        <button
            onClick={handleLogout}
            className="p-2 rounded-lg bg-[hsl(var(--lex-primary))] text-white hover:brightness-110"
            aria-label="Çıkış"
        >
            <LogOut size={16} />
        </button>
        </div>

    </aside>
  );
}
