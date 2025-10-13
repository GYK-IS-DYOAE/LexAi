import { Outlet, useLocation } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

export default function PublicLayout() {
  const location = useLocation();
  const isAuthPage = location.pathname.includes("login") || location.pathname.includes("register");

  return (
    <div className="min-h-screen flex flex-col bg-[hsl(var(--background))] text-[hsl(var(--foreground))] transition-colors duration-300">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-[hsl(var(--border))]">
        <h1 className="text-xl font-bold text-[hsl(var(--lex-primary))]">LexAI</h1>
        <ThemeToggle />
      </header>

      {/* İçerik */}
      <main className={`flex-1 ${isAuthPage ? "flex items-center justify-center" : ""}`}>
        <div className={`${isAuthPage ? "max-w-md w-full p-6 border border-border rounded-2xl shadow bg-card" : ""} mx-auto`}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
