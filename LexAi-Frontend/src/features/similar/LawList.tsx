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

  if (!laws || laws.length === 0) {
    return <p className="text-sm text-muted-foreground">Henüz sonuç yok.</p>;
  }

  return (
    <div className="space-y-3">
      {laws.map((law, i) => (
        <Card
          key={`${law.law_name}-${law.article_no}-${i}`}
          className="
                relative
                p-4 pr-10 rounded-xl
                bg-[hsl(var(--muted))] border border-transparent
                hover:bg-[hsl(var(--muted))/0.9] hover:border-[hsl(var(--lex-primary))/0.25]
                transition cursor-pointer
            "
            onClick={() => setSelectedLaw(law)}
            >
            <div>
                <p className="font-medium">{law.law_name}</p>
                <p className="text-xs text-muted-foreground">Madde: {law.article_no || "-"}</p>
                <div className="mt-1 text-xs text-muted-foreground">
                Alaka Skoru: {(law.relevance_score * 100).toFixed(1)}%
                </div>
            </div>

            {/* ikon - sağda dikey ortalı */}
            <button
                aria-label="Kanun ayrıntısı"
                className="
                absolute right-4 top-1/2 -translate-y-1/2
                text-[hsl(var(--lex-primary))] opacity-80 hover:opacity-100
                "
                onClick={(e) => { e.stopPropagation(); setSelectedLaw(law); }}
            >
                <Scale className="w-4 h-4" />
            </button>
            </Card>
      ))}

      <Dialog open={!!selectedLaw} onOpenChange={() => setSelectedLaw(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedLaw?.law_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><strong>Madde:</strong> {selectedLaw?.article_no}</p>
            <p><strong>Alaka Skoru:</strong> {(selectedLaw?.relevance_score || 0) * 100}%</p>
            <p>Bu kanun maddesi, benzer davalardaki metinlerden tespit edilmiştir.</p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
