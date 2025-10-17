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
        topn: 5,
        include_summaries: true, // ilk hali gibi (popup yerine direkt gösterilecekse)
      });
      setCases(res.data.similar_cases || []);
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
      {/* Arama */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Metninizi girin (örn: İşe iade davası kıdem tazminatı)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="
            flex-1 h-11 rounded-xl
            bg-[hsl(var(--muted))]
            border-none
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

      {/* İçerik */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 overflow-hidden">
        {/* Sol: Benzer Davalar */}
        <div className="overflow-y-auto pr-2">
          <h2 className="text-lg font-semibold mb-3 text-[hsl(var(--lex-primary))]">Benzer Davalar</h2>
          {!loading && cases.length === 0 && !query && (
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
          <h2 className="text-lg font-semibold mb-3 text-[hsl(var(--lex-primary))]">İlgili Kanunlar</h2>
          {!loading && laws.length === 0 && !query && (
            <p className="text-sm text-muted-foreground">Henüz sonuç yok.</p>
          )}
          {laws.length > 0 && <LawList laws={laws} />}
        </div>
      </div>

      {/* Dava Detay Popup */}
      <Dialog open={!!selectedCase} onOpenChange={() => setSelectedCase(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedCase?.dava_turu || "Dava Detayı"} — {selectedCase?.doc_id}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 text-sm">
            {selectedCase?.gerekce && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">Gerekçe</h3>
                <p className="text-muted-foreground">{selectedCase?.gerekce}</p>
              </div>
            )}
            {selectedCase?.karar && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">Karar</h3>
                <p className="text-muted-foreground">{selectedCase?.karar}</p>
              </div>
            )}
            {selectedCase?.hikaye && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">Olay Hikayesi</h3>
                <p className="text-muted-foreground">{selectedCase?.hikaye}</p>
              </div>
            )}
            {!selectedCase?.gerekce && !selectedCase?.karar && !selectedCase?.hikaye && (
              <p className="text-muted-foreground">Detay bilgisi bulunamadı.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
