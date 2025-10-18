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
  karar_metni?: string | null; // 🔹 backend’de “karar_metni_meta” alanına karşılık geliyor
}

interface CaseCardProps {
  item: CaseItem;
  onSelect?: (item: CaseItem) => void;
}

export default function CaseCard({ item, onSelect }: CaseCardProps) {
  // 🔹 kart başlığı için öncelik sırası:
  // dava_turu > karar_metni (ilk 8 kelime) > gerekçe (ilk 8 kelime)
  const getTitle = () => {
    if (item.dava_turu && item.dava_turu.trim() !== "")
      return item.dava_turu;
    if (item.karar_metni && item.karar_metni.trim() !== "")
      return item.karar_metni.split(" ").slice(0, 8).join(" ") + "…";
    if (item.gerekce && item.gerekce.trim() !== "")
      return item.gerekce.split(" ").slice(0, 8).join(" ") + "…";
    return "Emsal Dava";
  };

  return (
    <Card
      className="
        relative p-4 pr-10 rounded-xl
        bg-[hsl(var(--muted))] border border-transparent
        hover:bg-[hsl(var(--muted))/0.9]
        hover:border-[hsl(var(--lex-primary))/0.25]
        transition cursor-pointer
      "
      onClick={() => onSelect?.(item)}
    >
      {/* İçerik */}
      <div>
        {/* Başlık */}
        <p className="font-semibold text-[hsl(var(--foreground))] line-clamp-2">
          {getTitle()}
        </p>

        {/* Sonuç */}
        {item.sonuc && (
          <p className="text-xs text-muted-foreground mt-1">
            Sonuç: {item.sonuc}
          </p>
        )}

        {/* Benzerlik oranı */}
        <div className="mt-2 text-xs text-[hsl(var(--lex-primary))] font-medium">
          Benzerlik: %{(item.similarity_score * 100).toFixed(1)}
        </div>
      </div>

      {/* Ayrıntı ikonu */}
      <button
        aria-label="Ayrıntıyı aç"
        className="
          absolute right-4 top-1/2 -translate-y-1/2
          text-[hsl(var(--lex-primary))] opacity-80 hover:opacity-100
        "
        onClick={(e) => {
          e.stopPropagation();
          onSelect?.(item);
        }}
      >
        <Eye className="w-4 h-4" />
      </button>
    </Card>
  );
}
