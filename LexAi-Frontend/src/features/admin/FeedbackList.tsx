import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Eye, ThumbsUp, ThumbsDown } from "lucide-react";
import api from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Feedback {
  id: string;
  user_email: string;
  user_name?: string;
  question_text: string;
  answer_text: string;
  vote: "like" | "dislike" | null;
  ts: string;
}

export default function FeedbackList() {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [selected, setSelected] = useState<Feedback | null>(null);

  useEffect(() => {
    api
      .get("/feedback/all")
      .then((res) => setFeedbacks(res.data))
      .catch((err) => console.error("Feedbackler alınamadı:", err));
  }, []);

  const formatDate = (iso?: string) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="p-8 w-full h-full overflow-x-auto hide-scrollbar">
      <h1 className="text-2xl font-bold text-[hsl(var(--lex-primary))] mb-8">
        Geri Bildirimler
      </h1>

      {/* bu tablo ekran daralınca kaydırılabilir olacak */}
      <div className="min-w-[1500px]">
        <Card className="border border-border/40 rounded-2xl bg-[hsl(var(--card))]">
          {/* Header */}
          <div className="grid grid-cols-[1fr_2fr_3fr_0.8fr_1fr_0.8fr] px-6 py-3 text-[15px] font-semibold text-muted-foreground border-b border-border/40">
            <span>Kullanıcı</span>
            <span>Sorgu</span>
            <span>Cevap</span>
            <span className="text-center">Geri Bildirim</span>
            <span>Tarih</span>
            <span className="text-right">Aksiyonlar</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-border/40">
            {feedbacks.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground text-[15px]">
                Henüz geri bildirim yok.
              </div>
            ) : (
              feedbacks.map((f) => (
                <div
                  key={f.id}
                  className="grid grid-cols-[1fr_2fr_3fr_0.8fr_1fr_0.8fr] items-center px-6 py-3 text-[15px] hover:bg-muted/10 transition"
                >
                  {/* Kullanıcı */}
                  <span className="font-medium whitespace-nowrap">
                    {f.user_name?.trim() || f.user_email || "Bilinmiyor"}
                  </span>

                  {/* Sorgu */}
                  <span className="truncate text-muted-foreground pr-4">
                    {f.question_text}
                  </span>

                  {/* Cevap */}
                  <span className="truncate text-muted-foreground pr-4">
                    {f.answer_text}
                  </span>

                  {/* Oy */}
                  <span className="flex justify-center">
                    {f.vote === "like" ? (
                      <ThumbsUp className="w-4 h-4 text-green-500" />
                    ) : f.vote === "dislike" ? (
                      <ThumbsDown className="w-4 h-4 text-red-500" />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </span>

                  {/* Tarih */}
                  <span className="text-muted-foreground whitespace-nowrap">
                    {formatDate(f.ts)}
                  </span>

                  {/* Aksiyon */}
                  <div className="flex justify-end">
                    <button
                      onClick={() => setSelected(f)}
                      className="flex items-center justify-center w-8 h-8 rounded-md border border-border/50 bg-background hover:bg-muted/20 transition"
                    >
                      <Eye className="w-4 h-4 text-foreground" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Detay Modal */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Geri Bildirim Detayı</DialogTitle>
          </DialogHeader>

          {selected && (
            <div className="space-y-4 text-[15px]">
              <div>
                <strong>Kullanıcı:</strong>{" "}
                {selected.user_name?.trim() || selected.user_email || "Bilinmiyor"}
              </div>
              <div>
                <strong>Sorgu:</strong>{" "}
                <span className="text-muted-foreground">{selected.question_text}</span>
              </div>
              <div>
                <strong>Cevap:</strong>
                <p className="text-muted-foreground whitespace-pre-line mt-1">
                  {selected.answer_text}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <strong>Geri Bildirim:</strong>
                {selected.vote === "like" ? (
                  <span className="inline-flex items-center gap-1 text-green-500">
                    <ThumbsUp className="w-4 h-4" /> Beğenildi
                  </span>
                ) : selected.vote === "dislike" ? (
                  <span className="inline-flex items-center gap-1 text-red-500">
                    <ThumbsDown className="w-4 h-4" /> Beğenilmedi
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </div>
              <div>
                <strong>Tarih:</strong> {formatDate(selected.ts)}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
