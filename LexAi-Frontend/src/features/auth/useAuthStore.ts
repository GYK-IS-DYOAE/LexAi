import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_admin?: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  fetchUser: (token: string) => Promise<void>;
  setAuth: (user: User, token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,

      login: async (email, password) => {
        try {
          const formData = new URLSearchParams();
          formData.append("username", email);
          formData.append("password", password);

          const res = await fetch("http://localhost:8000/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData.toString(),
          });

          if (!res.ok) {
            console.error("Login failed:", res.status, await res.text());
            return false;
          }

          const data = await res.json();
          const token = data.access_token ?? null;
          if (!token) return false;

          localStorage.setItem("token", token);

          // token'ı kaydet
          set({ token });

          // user bilgisini ayrı endpoint’ten çek
          await get().fetchUser(token);

          return true;
        } catch (err) {
          console.error("Login error:", err);
          return false;
        }
      },

      // Kullanıcı bilgilerini al
      fetchUser: async (token: string) => {
        try {
          const res = await fetch("http://localhost:8000/auth/me", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (res.ok) {
            const userData = await res.json();
            set({ user: userData });
          } else {
            console.error("Fetch user failed:", res.status);
          }
        } catch (err) {
          console.error("Fetch user error:", err);
        }
      },

      logout: () => {
        set({ user: null, token: null });
        localStorage.removeItem("auth-storage");
      },

      setAuth: (user, token) => {
        set({ user, token });
      },
    }),
    { name: "auth-storage" }
  )
);
