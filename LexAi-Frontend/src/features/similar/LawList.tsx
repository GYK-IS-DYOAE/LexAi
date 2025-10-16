import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Scale } from "lucide-react";

interface LawItem {
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
    return <p className="text-sm text-muted-foreground">İlgili kanun bulunamadı.</p>;
  }

  return (
    <div className="space-y-3">
      {laws.map((law, i) => (
        <Card
          key={i}
          className="p-4 cursor-pointer transition border border-[hsl(var(--border))] hover:border-[hsl(var(--lex-primary))]/70 hover:shadow-[0_0_10px_hsl(var(--lex-primary)/0.25)]"
          onClick={() => setSelectedLaw(law)}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">{law.law_name}</p>
              <p className="text-xs text-muted-foreground">
                Madde: {law.article_no || "-"}
              </p>
            </div>
            <Scale className="w-4 h-4 text-[hsl(var(--lex-primary))]" />
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            Alaka Skoru: {(law.relevance_score * 100).toFixed(1)}%
          </div>
        </Card>
      ))}

      {/* Kanun Detay Popup */}
      <Dialog open={!!selectedLaw} onOpenChange={() => setSelectedLaw(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedLaw?.law_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><strong>Madde:</strong> {selectedLaw?.article_no}</p>
            <p>
              <strong>Alaka Skoru:</strong>{" "}
              {(selectedLaw?.relevance_score || 0) * 100}%
            </p>
            <p>
              Bu kanun maddesi, benzer davalardaki gerekçe veya karar
              metinlerinde tespit edilmiştir.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
