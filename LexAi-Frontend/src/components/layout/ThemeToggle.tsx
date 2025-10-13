import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const enableDark = saved ? saved === "dark" : prefersDark;
    setIsDark(enableDark);
    document.documentElement.classList.toggle("dark", enableDark);
  }, []);

  const toggle = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  return (
    <button
      onClick={toggle}
      className="relative flex items-center justify-center w-10 h-10 rounded-xl border border-gray-600/50 
      bg-gradient-to-br from-[#2a2b2e] to-[#1a1b1e] hover:brightness-110 shadow-inner transition-all duration-300"
      aria-label="Tema Değiştir"
    >
      {isDark ? (
        <Sun className="text-yellow-400 w-5 h-5 drop-shadow-[0_0_4px_rgba(255,255,150,0.6)] transition-all" />
      ) : (
        <Moon className="text-[#7A1622] w-5 h-5 drop-shadow-[0_0_4px_rgba(122,22,34,0.4)] transition-all" />
      )}
    </button>
  );
}
