import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Search, Eye } from "lucide-react";
import api from "@/lib/api";
import CaseCard from "./CaseCard";
import LawList from "./LawList";

interface CaseItem {
  doc_id: string;
  dava_turu: string | null;
  sonuc: string | null;
  gerekce: string | null;
  karar: string | null;
  hikaye: string | null;
  similarity_score: number;
  source: string;
}

interface LawItem {
  law_name: string;
  article_no: string;
  relevance_score: number;
}

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
        include_summaries: true,
      });
      setCases(res.data.similar_cases || []);
      setLaws(res.data.related_laws || []);
    } catch (err) {
      console.error("Benzer davalar alınamadı:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full p-6 space-y-6">
      {/* Arama alanı */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Metninizi girin (örn: İşe iade davası kıdem tazminatı)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1"
        />
        <Button onClick={handleSearch} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </Button>
      </div>

      {/* İçerik alanı */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 overflow-hidden">
        {/* Sol: Benzer Davalar */}
        <div className="overflow-y-auto pr-2">
          <h2 className="text-lg font-semibold mb-3 text-[hsl(var(--lex-primary))]">
            Benzer Davalar
          </h2>
          {cases.length === 0 && !loading ? (
            <p className="text-sm text-muted-foreground">Henüz sonuç yok.</p>
          ) : (
            <div className="space-y-3">
              {cases.map((c) => (
                <Card
                  key={c.doc_id}
                  className="p-4 cursor-pointer hover:border-[hsl(var(--lex-primary))]"
                  onClick={() => setSelectedCase(c)}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium">{c.dava_turu || "Bilinmeyen dava"}</p>
                      <p className="text-sm text-muted-foreground">
                        Sonuç: {c.sonuc || "?"} · Kaynak: {c.source}
                      </p>
                    </div>
                    <Eye className="w-4 h-4 text-[hsl(var(--lex-primary))]" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Benzerlik: %{(c.similarity_score * 100).toFixed(1)}
                  </p>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Sağ: İlgili Kanunlar */}
        <div className="overflow-y-auto pl-2">
          <h2 className="text-lg font-semibold mb-3 text-[hsl(var(--lex-primary))]">
            İlgili Kanunlar
          </h2>
          <LawList laws={laws} />
        </div>
      </div>

      {/* Dava detay popup */}
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
                <p className="text-muted-foreground">{selectedCase.gerekce}</p>
              </div>
            )}
            {selectedCase?.karar && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">Karar</h3>
                <p className="text-muted-foreground">{selectedCase.karar}</p>
              </div>
            )}
            {selectedCase?.hikaye && (
              <div>
                <h3 className="font-semibold text-[hsl(var(--lex-primary))]">Olay Hikayesi</h3>
                <p className="text-muted-foreground">{selectedCase.hikaye}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
