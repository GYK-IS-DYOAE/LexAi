import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Scale } from "lucide-react";

export interface LawItem {
  law_name: string;
  article_no: string;
  relevance_score: number;
}

interface LawListProps {
  laws: LawItem[];
}

export default function LawList({ laws }: LawListProps) {
  const [selectedLaw, setSelectedLaw] = useState<LawItem | null>(null);

  // 🔹 geçersiz kayıtları filtrele
  const validLaws = (laws || []).filter(
    (l) => l.law_name && l.law_name.trim() !== ""
  );

  if (validLaws.length === 0) {
    return <p className="text-sm text-muted-foreground">Henüz sonuç yok.</p>;
  }

  return (
    <div className="space-y-3">
      {validLaws.map((law, i) => (
        <Card
          key={`${law.law_name}-${law.article_no}-${i}`}
          className="
            relative p-4 pr-10 rounded-xl
            bg-[hsl(var(--muted))] border border-transparent
            hover:bg-[hsl(var(--muted))/0.9]
            hover:border-[hsl(var(--lex-primary))/0.25]
            transition cursor-pointer
          "
          onClick={() => setSelectedLaw(law)}
        >
          <div>
            {/* 🔹 Kanun adı + madde numarası */}
            <p className="font-medium text-[hsl(var(--foreground))] truncate">
              {law.law_name.toUpperCase()}
              {law.article_no && law.article_no !== "-" && (
                <> — Madde {law.article_no}</>
              )}
            </p>

            {/* 🔹 Alaka skoru */}
            <div className="mt-1 text-xs text-muted-foreground">
              Alaka Skoru: {(law.relevance_score * 100).toFixed(1)}%
            </div>
          </div>

          {/* 🔹 Sağ üst ikon */}
          <button
            aria-label="Kanun ayrıntısı"
            className="
              absolute right-4 top-1/2 -translate-y-1/2
              text-[hsl(var(--lex-primary))] opacity-80 hover:opacity-100
            "
            onClick={(e) => {
              e.stopPropagation();
              setSelectedLaw(law);
            }}
          >
            <Scale className="w-4 h-4" />
          </button>
        </Card>
      ))}

      {/* 🔹 Ayrıntı popup */}
      <Dialog open={!!selectedLaw} onOpenChange={() => setSelectedLaw(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="break-words">
              {selectedLaw?.law_name?.toUpperCase()}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-2 text-sm text-muted-foreground">
            <p>
              <strong>Madde:</strong>{" "}
              {selectedLaw?.article_no && selectedLaw.article_no !== "-"
                ? selectedLaw.article_no
                : "Belirtilmemiş"}
            </p>

            <p>
              <strong>Alaka Skoru:</strong>{" "}
              {((selectedLaw?.relevance_score || 0) * 100).toFixed(1)}%
            </p>

            <p>
              Bu kanun maddesi, sistem tarafından benzer davalardaki karar
              metinlerinden tespit edilmiştir.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
