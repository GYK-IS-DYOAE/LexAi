import { Card } from "@/components/ui/card";
import { Eye } from "lucide-react";

interface CaseItem {
  doc_id: string;
  dava_turu: string | null;
  sonuc: string | null;
  similarity_score: number;
  source: string;
}

interface CaseCardProps {
  item: CaseItem;
  onSelect?: (item: CaseItem) => void;
}

export default function CaseCard({ item, onSelect }: CaseCardProps) {
  return (
    <Card
      className="p-4 cursor-pointer transition border border-[hsl(var(--border))] hover:border-[hsl(var(--lex-primary))]/70 hover:shadow-[0_0_10px_hsl(var(--lex-primary)/0.25)]"
      onClick={() => onSelect?.(item)}
    >
      <div className="flex justify-between items-start">
        <div>
          <p className="font-medium">{item.dava_turu || "Bilinmeyen Dava"}</p>
          <p className="text-xs text-muted-foreground mt-1">
            Sonuç: {item.sonuc || "?"} · Kaynak: {item.source}
          </p>
        </div>
        <Eye className="w-4 h-4 text-[hsl(var(--lex-primary))]" />
      </div>

      <div className="mt-2 text-xs text-muted-foreground">
        Benzerlik: %{(item.similarity_score * 100).toFixed(1)}
      </div>
    </Card>
  );
}
