import { Outlet, useLocation } from "react-router-dom";
import SideBar from "./SideBar";
import ThemeToggle from "./ThemeToggle";

export default function PrivateLayout() {
  const location = useLocation();

  const isAdminRoute = location.pathname.startsWith("/admin");
  const isSimilarRoute = location.pathname.startsWith("/similar");
  const isChatRoute = location.pathname.startsWith("/chat");

  // Varsayılan başlık
  let pageTitle = "LexAI";

  // Admin sayfaları
  if (isAdminRoute) {
    pageTitle = "Admin Paneli";
  }
  // Benzer davalar
  else if (isSimilarRoute) {
    pageTitle = "Benzer Davalar";
  }
  // Sohbet sayfası
  else if (isChatRoute) {
    const params = new URLSearchParams(location.search);
    const chatId = params.get("id");

    if (chatId) {
      const chats = JSON.parse(localStorage.getItem("chat_history") || "[]");
      const currentChat = chats.find((c: any) => c.id === chatId);
      pageTitle = currentChat?.title || "Yeni Sohbet";
    } else {
      pageTitle = "Yeni Sohbet";
    }
  }

  return (
    <div className="flex min-h-screen w-full bg-[hsl(var(--background))] text-[hsl(var(--foreground))]">
      {/*Sidebar sabit */}
      <div className="sticky top-0 h-screen flex-shrink-0">
        <SideBar />
      </div>

      {/*İçerik kısmı */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Üst bar */}
        <header className="sticky top-0 z-40 h-14 bg-[hsl(var(--card))] border-b border-[hsl(var(--border))] flex items-center justify-between px-6">
          <h1 className="text-base font-semibold text-[hsl(var(--lex-primary))] tracking-tight truncate max-w-[60%]">
            {pageTitle}
          </h1>
          <ThemeToggle />
        </header>

        {/*Ana içerik */}
        <main
          className="
            flex-1 min-w-0 
            overflow-x-auto overflow-y-auto 
            px-10 py-6
            scrollbar-thin 
            scrollbar-thumb-[hsl(var(--muted-foreground)/0.4)]
            scrollbar-track-[hsl(var(--background))] 
            scrollbar-thumb-rounded-lg
          "
        >
          {location.pathname.startsWith("/chat") ? (
            <div className="h-[calc(100vh-3.5rem)] -mx-10 -my-6 flex flex-col">
              <Outlet />
            </div>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  );
}
