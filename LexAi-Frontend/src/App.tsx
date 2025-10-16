import { BrowserRouter, Routes, Route } from "react-router-dom";

// Layouts
import PublicLayout from "@/components/layout/PublicLayout";
import ChatLayout from "@/components/layout/ChatLayout"; // ✅ BURADA!

// Pages
import LandingPage from "@/features/landing/LandingPage";
import Login from "@/features/auth/Login";
import Register from "@/features/auth/Register";
import HomePage from "@/features/home/HomePage";
import ChatPage from "@/features/chat/ChatPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth/login" element={<Login />} />
          <Route path="/auth/register" element={<Register />} />
        </Route>

        {/* Protected Routes */}
        <Route path="/home" element={<HomePage />} />

        {/* Chat artık ChatLayout içinde */}
        <Route element={<ChatLayout />}>
          <Route path="/chat" element={<ChatPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
