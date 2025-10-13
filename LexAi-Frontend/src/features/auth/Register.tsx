import { useState } from "react";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Register:", form);
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh] bg-[hsl(var(--background))]">
      <form
        onSubmit={handleSubmit}
        className="bg-white shadow-lg rounded-2xl p-8 w-full max-w-md space-y-6 border border-gray-100"
      >
        <h2 className="text-2xl font-bold text-center text-[hsl(var(--primary))]">
          Yeni Hesap Oluştur
        </h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Ad Soyad</label>
          <input
            name="name"
            type="text"
            placeholder="Ad Soyad"
            className="w-full border border-gray-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            onChange={handleChange}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">E-posta</label>
          <input
            name="email"
            type="email"
            placeholder="ornek@eposta.com"
            className="w-full border border-gray-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            onChange={handleChange}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Şifre</label>
          <input
            name="password"
            type="password"
            placeholder="********"
            className="w-full border border-gray-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            onChange={handleChange}
          />
        </div>

        <button
          type="submit"
          className="w-full bg-[hsl(var(--primary))] text-white py-3 rounded-xl font-semibold hover:bg-[hsl(var(--primary)/0.9)] transition"
        >
          Kayıt Ol
        </button>
      </form>
    </div>
  );
}
