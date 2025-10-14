import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
  },
});

// 🔹 Token varsa otomatik ekle (hiç hata fırlatmaz)
api.interceptors.request.use((config) => {
  try {
    // Zustand persist edilen token'ı oku
    const stored = localStorage.getItem("auth-storage");
    if (stored) {
      const parsed = JSON.parse(stored);
      const token = parsed?.state?.token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  } catch (err) {
    console.warn("Token eklenemedi:", err);
  }
  return config;
});

export default api;
