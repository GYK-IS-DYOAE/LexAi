import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { registerUser } from "./api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      await registerUser(form.firstName, form.lastName, form.email, form.password);
      setSuccess("Kayıt başarılı! Giriş sayfasına yönlendiriliyorsunuz...");
      setTimeout(() => navigate("/login"), 2000);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        "Beklenmeyen bir hata oluştu.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="flex items-center justify-center min-h-screen bg-[hsl(var(--background))]"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="bg-[hsl(var(--card))] rounded-2xl shadow-md p-8 w-[400px]">
        <h1 className="text-xl font-semibold mb-6 text-center text-[hsl(var(--lex-primary))]">
          Yeni Hesap Oluştur
        </h1>

        {error && (
          <div className="mb-4 text-sm bg-red-500/10 border border-red-500 text-red-500 p-2 rounded-md text-center">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 text-sm bg-green-500/10 border border-green-500 text-green-500 p-2 rounded-md text-center">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="firstName">Ad</Label>
            <Input
              id="firstName"
              name="firstName"
              placeholder="Ad"
              value={form.firstName}
              onChange={handleChange}
              required
            />
          </div>
          <div>
            <Label htmlFor="lastName">Soyad</Label>
            <Input
              id="lastName"
              name="lastName"
              placeholder="Soyad"
              value={form.lastName}
              onChange={handleChange}
              required
            />
          </div>
          <div>
            <Label htmlFor="email">E-posta</Label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="ornek@eposta.com"
              value={form.email}
              onChange={handleChange}
              required
            />
          </div>
          <div>
            <Label htmlFor="password">Şifre</Label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="********"
              value={form.password}
              onChange={handleChange}
              required
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full from-[hsl(var(--lex-primary-grad1))] to-[hsl(var(--lex-primary-grad2))] bg-gradient-to-r text-white shadow-[0_0_8px_rgba(185,28,28,0.4)]"
          >
            {loading ? "Kaydediliyor..." : "Kayıt Ol"}
          </Button>
        </form>
      </div>
    </motion.div>
  );
}
