from typing import List, Dict
import re
from src.rag.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES

SYSTEM_PROMPT = """
Sen LexAI’nin hukuk asistanısın. Kullanıcının sorularına yalnızca Türk hukuku çerçevesinde yanıt ver. 
Cevaplar **sadece Türkçe** olacak, başka dil kullanamazsın. 
Hukuki olmayan sorulara kibarca reddet ve yanıt verme. 

Yanıt kuralları:
- Cümleler mantıklı, akıcı, Türkçe dilbilgisine uygun olacak.
- Gereksiz sembol veya anlamsız kelime birleşimleri (ör: asdf, ??, ..) kullanma.
- Kanun/madde geçiyorsa sadece anlamını açıkla, metni kopyalama.
- Bilgi yetersizse: “Mevcut bilgiler sınırlı olsa da genel uygulama şöyledir…” diyebilirsin.
- Bağlayıcı hukuki tavsiye verme; sadece bilgilendirici ol.

Yanıt yapısı:
1. Konunun genel çerçevesi
2. Olayın değerlendirilmesi
3. İlgili yasal çerçeve (varsa)
4. Kısa sonuç veya yönlendirme

Ek kurallar:
- Kullanıcı selamlaşırsa (“merhaba”, “selam”, “nasılsın”) kibarca yanıt ver: “Merhaba, size nasıl yardımcı olabilirim?”
- Kullanıcı anlamsız semboller veya eksik şeyler yazarsa: “Sorunuzu tam olarak anlayamadım, isterseniz hukuki bir konuda yardımcı olabilirim.” de.
- Hukuk dışı bir konu sorarsa: “Ben bir hukuk asistanıyım, hukuk dışı konularda bilgi veremem.” diye yanıtla.
- Cevapta **her zaman tam karar metinlerinden** yararlan.
"""

GREETINGS_RE = re.compile(r"^\s*(merhaba|selam|günaydın|iyi günler|iyi akşamlar|nasılsın)\b", re.IGNORECASE)
NONSENSE_RE = re.compile(r"^[\?\*\.\,]+$")


def _sanitize_user_query(q: str) -> str:
    """Kullanıcı sorgusunu temizle."""
    if not q:
        return ""
    q = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ\.\,\?\!]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def build_user_prompt(query: str, passages: List, conversation_history: List[Dict] | None = None) -> str:
    """
    Kullanıcı sorusu + tam karar_metni pasajları + önceki konuşmalar → LLM prompt'u.
    passages: List[Hit] veya sözlük (retrieve_combined.hybrid_search() sonucu)
    conversation_history: List[{"user": "...", "assistant": "..."}]
    """
    q_clean = _sanitize_user_query(query or "")

    # 🔹 selam, anlamsız veya hukuk dışı içerikler
    if GREETINGS_RE.match(q_clean):
        return "Merhaba, size nasıl yardımcı olabilirim?"
    if NONSENSE_RE.match(q_clean) or len(q_clean) < 2:
        return "Sorunuzu tam olarak anlayamadım, isterseniz hukuki bir konuda yardımcı olabilirim."
    if any(w in q_clean.lower() for w in ["yemek", "spor", "film", "müzik", "tarif", "tatil", "oyun"]):
        return "Ben bir hukuk asistanıyım, hukuk dışı konularda bilgi veremem."

    # 🔹 sistem kuralları
    lines = [SYSTEM_PROMPT.strip()]

    # 🔹 geçmiş konuşmalar
    if conversation_history:
        lines.append("\n--- ÖNCEKİ KONUŞMA BAĞLAMI ---")
        for turn in conversation_history[-5:]:
            user_msg = turn.get("user", "").strip()
            assistant_msg = turn.get("assistant", "").strip()
            if user_msg:
                lines.append(f"Kullanıcı: {user_msg}")
            if assistant_msg:
                lines.append(f"Asistan: {assistant_msg}")

    # 🔹 mevcut soru
    lines.append("\n--- GÜNCEL SORU ---")
    lines.append(q_clean)

    # 🔹 tam karar metinleri (karar_metni)
    if passages:
        lines.append("\n--- BENZER DAVALARIN TAM KARAR METİNLERİ ---")
        for i, p in enumerate(passages[:MAX_TOTAL_PASSAGES], 1):
            # retrieve_combined.Hit.text_full zaten karar_metni
            text = ""
            if hasattr(p, "text_full"):  # Hit objesi
                text = p.text_full
            elif isinstance(p, dict):   # dict olarak geldiyse
                text = p.get("karar_metni") or p.get("text_full") or ""
            text = (text or "").strip().replace("\n", " ")
            if text:
                snippet = text[:MAX_PASSAGE_CHARS]
                lines.append(f"[{i}] {snippet}")

    # 🔹 model yönlendirmesi
    lines.append(
        "\nYukarıdaki tam karar metinleri ve konuşma geçmişini dikkate alarak, "
        "kullanıcının sorusuna Türkçe, akıcı, bağlama uygun ve öğretici bir hukuki yanıt ver."
    )

    return "\n".join(lines)
