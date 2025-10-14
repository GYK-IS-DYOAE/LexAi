import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ShieldCheck, ShieldOff, Trash2, Loader2 } from "lucide-react";

interface User {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  is_admin: boolean;
}

export default function UserList() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [actingId, setActingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/auth/users");
      setUsers(res.data);
    } catch {
      setError("Kullanıcılar yüklenemedi ❌");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) =>
      [u.first_name, u.last_name, u.email, u.is_admin ? "admin" : "user"]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [users, query]);

  const handleMakeAdmin = async (id: string) => {
    setActingId(id);
    try {
      await api.patch(`/auth/users/${id}/make-admin`);
      await fetchUsers();
    } finally {
      setActingId(null);
    }
  };

  const handleRemoveAdmin = async (id: string) => {
    setActingId(id);
    try {
      await api.patch(`/auth/users/${id}/remove-admin`);
      await fetchUsers();
    } finally {
      setActingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bu kullanıcıyı silmek istediğinizden emin misiniz?")) return;
    setDeletingId(id);
    try {
      await api.delete(`/auth/delete/${id}`);
      await fetchUsers();
    } finally {
      setDeletingId(null);
    }
  };

  const total = users.length;
  const shown = filtered.length;

  return (
    <div className="p-8 w-full h-full overflow-x-auto hide-scrollbar">
      {/* Başlık + Arama */}
      <div className="min-w-[1100px] mb-8 flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-[hsl(var(--lex-primary))]">
          Kullanıcılar{" "}
          <span className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
            ({shown}{shown !== total ? ` / ${total}` : ""})
          </span>
        </h1>

        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ara: ad, e-posta, rol…"
          className="h-9 w-64 rounded-xl bg-[hsl(var(--card))] border border-[hsl(var(--border))]
                     px-3 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--lex-primary))/0.35]
                     placeholder:text-[hsl(var(--muted-foreground))]"
        />
      </div>

      {/* Hata / Yükleniyor durumları */}
      {loading ? (
        <div className="flex justify-center items-center py-12 text-[hsl(var(--muted-foreground))]">
          <Loader2 className="w-5 h-5 mr-2 animate-spin" />
          Yükleniyor...
        </div>
      ) : error ? (
        <div className="flex justify-center items-center py-12 text-red-500 font-medium">
          {error}
        </div>
      ) : (
        <div className="min-w-[1100px]">
          <Card className="border border-border/40 rounded-2xl bg-[hsl(var(--card))] overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-[2fr_2fr_1fr_1.7fr_0.8fr] px-6 py-3 text-[15px] font-semibold text-muted-foreground border-b border-border/40">
              <span className="text-left">Ad Soyad</span>
              <span className="text-left">E-posta</span>
              <span className="text-center">Rol</span>
              <span className="text-center">İşlemler</span>
              <span></span>
            </div>

            {/* Rows */}
            {filtered.map((u) => (
              <div
                key={u.id}
                className="grid grid-cols-[2fr_2fr_1fr_1.7fr_0.8fr] items-center px-6 py-3 text-[15px] hover:bg-muted/10 transition"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={`https://api.dicebear.com/8.x/initials/svg?seed=${encodeURIComponent(
                      `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() || u.email
                    )}&backgroundColor=b91c1c&textColor=ffffff`}
                    alt="avatar"
                    className="w-7 h-7 rounded-full ring-2 ring-[hsl(var(--lex-primary))]/30"
                  />
                  <span className="font-medium whitespace-nowrap">{`${u.first_name} ${u.last_name}`}</span>
                </div>

                <span className="truncate text-muted-foreground">{u.email}</span>

                <div className="flex justify-center">
                  {u.is_admin ? (
                    <span className="inline-flex items-center justify-center rounded-full w-[70px] h-6 text-xs font-semibold bg-[hsl(var(--lex-primary))/0.12] text-[hsl(var(--lex-primary))] border border-[hsl(var(--lex-primary))/0.35]">
                      Admin
                    </span>
                  ) : (
                    <span className="inline-flex items-center justify-center rounded-full w-[70px] h-6 text-xs font-medium bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border border-[hsl(var(--border))]">
                      User
                    </span>
                  )}
                </div>

                <div className="flex justify-center">
                  {u.is_admin ? (
                    <Button
                      variant="outline"
                      className="h-8 w-[160px] justify-center border-red-500 text-red-500 hover:bg-red-500/10"
                      disabled={actingId === u.id || deletingId === u.id}
                      onClick={() => handleRemoveAdmin(u.id)}
                    >
                      {actingId === u.id ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <ShieldOff className="w-4 h-4 mr-1" />
                      )}
                      Adminliği Kaldır
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      className="h-8 w-[160px] justify-center border-[hsl(var(--lex-primary))] text-[hsl(var(--lex-primary))] hover:bg-[hsl(var(--lex-primary))/0.1]"
                      disabled={actingId === u.id || deletingId === u.id}
                      onClick={() => handleMakeAdmin(u.id)}
                    >
                      {actingId === u.id ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <ShieldCheck className="w-4 h-4 mr-1" />
                      )}
                      Admin Yap
                    </Button>
                  )}
                </div>

                <div className="flex justify-center">
                  <Button
                    variant="destructive"
                    className="h-8 w-[80px] justify-center bg-red-600 hover:bg-red-700 text-white"
                    disabled={deletingId === u.id || actingId === u.id}
                    onClick={() => handleDelete(u.id)}
                  >
                    {deletingId === u.id ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4 mr-1" />
                    )}
                    Sil
                  </Button>
                </div>
              </div>
            ))}
          </Card>
        </div>
      )}
    </div>
  );
}
