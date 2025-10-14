import { Outlet } from "react-router-dom";
import SideBar from "@/components/layout/SideBar";

export default function ChatLayout() {
  return (
    <div className="flex h-screen bg-[hsl(var(--background))]">
      {/* ✅ Gerçek Sidebar buraya yerleştirildi */}
      <SideBar />

      {/* ✅ Sağ taraf - Chat içeriği */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
