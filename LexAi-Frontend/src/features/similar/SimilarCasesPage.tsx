import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Search } from "lucide-react";
import api from "@/lib/api";
import CaseCard, { type CaseItem } from "./CaseCard";
import LawList, { type LawItem } from "./LawList";

export default function SimilarCasesPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [laws, setLaws] = useState<LawItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseItem | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.post("/similar/analyze", {
        query,
        topn: 10,
        include_summaries: true,
      });

      // 🔹 benzerlik oranına göre sırala
      const sorted = (res.data.similar_cases || []).sort(
        (a: CaseItem, b: CaseItem) => b.similarity_score - a.similarity_score
      );

      setCases(sorted.map((c: CaseItem) => ({ ...c, source: "" })));
      setLaws(res.data.related_laws || []);
    } catch (err) {
      console.error("Benzer davalar alınamadı:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="flex flex-col h-full w-full p-6 space-y-6">
      {/* 🔹 Arama Alanı */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Metninizi girin (örn: İşe iade davası kıdem tazminatı)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="
            flex-1 h-11 rounded-xl
            bg-[hsl(var(--muted))] border-none
            text-[hsl(var(--foreground))]
            placeholder:text-[hsl(var(--foreground))/0.55]
            focus-visible:ring-2 focus-visible:ring-[hsl(var(--lex-primary))/0.35]
          "
        />
        <Button
          onClick={handleSearch}
          disabled={loading}
          className="bg-[hsl(var(--lex-primary))] hover:bg-[hsl(var(--lex-primary))/0.9]"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </Button>
      </div>

      {/* 🔹 İçerik */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 overflow-hidden">
        {/* Sol: Benzer Davalar */}
        <div className="overflow-y-auto pr-2">
          <h2 className="text-lg font-semibold mb-3 text-[hsl(var(--lex-primary))]">
            Benzer Davalar
          </h2>

          {!loading && cases.length === 0 && (
            <p className="text-sm text-muted-foreground">Henüz sonuç yok.</p>
          )}

          {cases.length > 0 && (
            <div className="space-y-3">
              {cases.map((c) => (
                <CaseCard key={c.doc_id} item={c} onSelect={(it) => setSelectedCase(it)} />
              ))}
            </div>
          )}
        </div>

        {/* Sağ: İlgili Kanunlar */}
        <div className="overflow-y-auto pl-2">
          <h2 className="text-lg font-semibold mb-3 text-[hsl(var(--lex-primary))]">
            İlgili Kanunlar
          </h2>

          {!loading && laws.length === 0 && (
            <p className="text-sm text-muted-foreground">Henüz sonuç yok.</p>
          )}

          {laws.length > 0 && <LawList laws={laws} />}
        </div>
      </div>

      {/* 🔹 Dava Detay Popup */}
      <Dialog open={!!selectedCase} onOpenChange={() => setSelectedCase(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="break-words text-[hsl(var(--foreground))]">
              {/* 🔹 Başlık önceliği: sonuç > kısa karar > dava türü */}
              {selectedCase?.sonuc
                ? selectedCase.sonuc.split(" ").slice(0, 10).join(" ") + "…"
                : selectedCase?.karar
                ? selectedCase.karar.split(" ").slice(0, 10).join(" ") + "…"
                : selectedCase?.dava_turu || "Dava Detayı"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-5 text-sm">
            {/* 🔹 Sonuç */}
            {selectedCase?.sonuc && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">Sonuç</h3>
                <p className="text-muted-foreground whitespace-pre-line leading-relaxed">
                  {selectedCase.sonuc}
                </p>
              </div>
            )}

            {/* 🔹 Tam Karar Metni */}
            {selectedCase?.karar_metni && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">
                  Karar Metni
                </h3>
                <p className="text-muted-foreground whitespace-pre-line leading-relaxed">
                  {selectedCase.karar_metni}
                </p>
              </div>
            )}

            {/* 🔹 Eğer hiçbiri yoksa */}
            {!selectedCase?.sonuc && !selectedCase?.karar_metni && (
              <p className="text-muted-foreground">Detay bilgisi bulunamadı.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
