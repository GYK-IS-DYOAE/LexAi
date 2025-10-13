import { Outlet } from "react-router-dom";
import SideBar from "./SideBar";
import ThemeToggle from "./ThemeToggle";

export default function PrivateLayout() {
  return (
    <div className="flex min-h-screen w-full bg-[hsl(var(--background))] text-[hsl(var(--foreground))]">
      <SideBar />

      <div className="flex-1 flex flex-col transition-all duration-300">
        <header className="sticky top-0 z-40 h-14 bg-[hsl(var(--card))] border-b border-[hsl(var(--border))] flex items-center justify-between px-6">
          <h1 className="text-base font-semibold text-[hsl(var(--lex-primary))] tracking-tight">
            LexAI Dashboard
          </h1>
          <ThemeToggle />
        </header>

        <main className="flex-1 overflow-y-auto px-10 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
