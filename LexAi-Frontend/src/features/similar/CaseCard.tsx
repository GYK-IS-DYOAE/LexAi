import { Card } from "@/components/ui/card";
import { Eye } from "lucide-react";

export interface CaseItem {
  doc_id: string;
  dava_turu: string | null;
  sonuc: string | null;
  similarity_score: number;
  source: string;
  gerekce?: string | null;
  karar?: string | null;
  hikaye?: string | null;
}

interface CaseCardProps {
  item: CaseItem;
  onSelect?: (item: CaseItem) => void;
}

export default function CaseCard({ item, onSelect }: CaseCardProps) {
  return (
    <Card
      className="
        relative   
        p-4 pr-10  
        rounded-xl bg-[hsl(var(--muted))] border border-transparent
        hover:bg-[hsl(var(--muted))/0.9] hover:border-[hsl(var(--lex-primary))/0.25]
        transition cursor-pointer
      "
      onClick={() => onSelect?.(item)}
    >
      {/* içerik */}
      <div>
        <p className="font-medium">{item.dava_turu || "Bilinmeyen Dava"}</p>
        <p className="text-xs text-muted-foreground mt-1">
          Sonuç: {item.sonuc || "?"} · Kaynak: {item.source}
        </p>
        <div className="mt-2 text-xs text-muted-foreground">
          Benzerlik: %{(item.similarity_score * 100).toFixed(1)}
        </div>
      </div>

      {/* ikon - sağda dikey ortalı */}
      <button
        aria-label="Ayrıntıyı aç"
        className="
          absolute right-4 top-1/2 -translate-y-1/2
          text-[hsl(var(--lex-primary))]
          opacity-80 hover:opacity-100
        "
        onClick={(e) => { e.stopPropagation(); onSelect?.(item); }}
      >
        <Eye className="w-4 h-4" />
      </button>
    </Card>
  );
}
