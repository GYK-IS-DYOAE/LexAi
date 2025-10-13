import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "@/features/auth/useAuthStore";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await login(email, password);
    if (success) navigate("/home");
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold text-center mb-6 text-[hsl(var(--lex-primary))]">
        Hesabınıza Giriş Yapın
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">E-posta</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--lex-primary))]/60 transition"
            placeholder="ornek@eposta.com"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Şifre</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--lex-primary))]/60 transition"
            placeholder="********"
          />
        </div>

        <button
          type="submit"
          className="w-full bg-[hsl(var(--lex-primary))] text-white rounded-lg py-2 font-medium hover:brightness-110 transition"
        >
          Giriş Yap
        </button>
      </form>

      <p className="text-sm text-center text-[hsl(var(--muted-foreground))] mt-4">
        Henüz hesabınız yok mu?{" "}
        <Link to="/register" className="text-[hsl(var(--lex-primary))] font-semibold hover:underline">
          Kayıt Ol
        </Link>
      </p>
    </div>
  );
}
