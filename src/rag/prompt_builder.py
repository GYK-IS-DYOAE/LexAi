from typing import List, Dict
from src.retrieval.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES

# ----------------------------
# SYSTEM PROMPT (Qwen'e talimat)
# ----------------------------
SYSTEM_PROMPT = """
# Rolün:
Sen bir hukuk asistanısın. Kullanıcılara Türkçe, doğal ve açıklayıcı cevaplar veriyorsun.

# Kurallar:
- Sadece TÜRKÇE konuş.
- Cevabını KULLANICI DOSTU, KİBAR ve AKICI bir dille ver.
- Uydurma, tahmin yapma. Sadece verilen pasajlardan çıkarım yap.
- Gerekiyorsa örnek yasa maddelerine atıf yap, ama sadece pasajda geçiyorsa.
- Kullanıcıya doğrudan hitap et (örneğin: “Bu tür davalarda...”, “Verilen kararlardan anlaşıldığı üzere...”).

# Cevap Şekli:
- Serbest metin olarak yaz.
- Giriş → gerekçe → sonuç şeklinde doğal bir akışla yaz.
- Cevabın kısa paragraflardan oluşmalı.
- Maddelendirme, JSON veya listeleme yapma.
- Önsöz, son söz, teşekkür veya selam içeren ifadeler kullanma.
- Kısa ve yetersiz cevaplar verme."""


from typing import List, Dict
from src.retrieval.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES

def build_user_prompt(query: str, passages: List[Dict]) -> str:
    """
    Kullanıcının sorusu ve ilgili karar pasajları birleştirilerek prompt hazırlanır.
    LLM'den açıklayıcı cevap alabilmek için net, kurgulu bir metin yapısı sunar.
    """
    lines = [f"# SORU:\n{query.strip()}\n", "# İLGİLİ MAHKEME KARARLARI:"]
    
    for i, p in enumerate(passages[:MAX_TOTAL_PASSAGES], 1):
        text = (p.get("text") or "").strip().replace("\n", " ")[:MAX_PASSAGE_CHARS]
        doc_id = p.get("doc_id", "—")
        lines.append(f"[{i}] doc_id={doc_id}  {text}")
    
    lines.append("")
    lines.append("# Yukarıdaki kararları dikkate alarak, kullanıcıyı bilgilendirici bir şekilde yanıt ver.")
    
    return "\n".join(lines)
