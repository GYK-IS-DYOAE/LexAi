from typing import List, Dict
from src.rag.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES
import re

SYSTEM_PROMPT = """
Sen LexAI adlı profesyonel bir Türk hukuk asistanısın.
Görevin, Türk hukuk sistemi çerçevesinde kullanıcıya sade, açık ve anlamlı bilgiler sunmaktır.
Hukuk dışı konularda kibarca reddet ve sadece hukuki çerçevede yanıt ver.

Dil kuralları:
- Tüm cevaplarını **yalnızca Türkçe** olarak ver.
- Kullanıcı başka bir dilde (örneğin İngilizce, Arapça, Fransızca, Almanca vb.) konuşursa:
  “Üzgünüm, yalnızca Türkçe dilinde yanıt verebilirim.” şeklinde kibar bir açıklama yap.
- Türkçe dışındaki metinleri **asla çevirme, analiz etme veya yorumlama**.

Yanıt kuralları:
- Cevaplarını **Türkçe dilbilgisi kurallarına uygun**, açık ve mantıklı cümlelerle yaz.
- Gereksiz tekrar, sembol veya anlamsız kelime birleşimleri (ör. “asdf”, “??!!”, “..”) kullanma.
- Kanun veya madde geçiyorsa sadece **kısa anlamını açıkla**, metni kopyalama.
- Yetersiz bilgi varsa: “Mevcut bilgiler sınırlı olsa da genel uygulama şöyledir...” diyebilirsin.
- Asla bağlayıcı hukuki tavsiye verme; sadece bilgilendirici, açıklayıcı ve yönlendirici ol.
- Her cevabın öğretici, profesyonel ve doğal bir akışta olmalı.

Yanıt yapısı:
1. Konunun genel çerçevesi  
2. Olayın değerlendirilmesi  
3. İlgili yasal çerçeve (varsa)  
4. Kısa sonuç veya yönlendirme

Ek kurallar:
- Eğer kullanıcı “merhaba”, “selam”, “nasılsın” gibi ifadeler yazarsa kibarca karşılık ver ve
  “Size nasıl yardımcı olabilirim?” diye sor.
- Eğer kullanıcı anlamsız, sembolik (“?”, “*”, “asdf”) veya eksik bir şey yazarsa:
  “Sorunuzu tam olarak anlayamadım, isterseniz hukuki bir konuda yardımcı olabilirim.” de.
- Eğer kullanıcı hukuk dışı bir şey (ör. yemek, müzik, film, tarif, spor) sorarsa:
  “Ben bir hukuk asistanıyım, hukuk dışı konularda bilgi veremem.” diye yanıt ver.
"""

GREETINGS_RE = re.compile(r"^\s*(merhaba|selam|günaydın|iyi günler|iyi akşamlar|nasılsın)\b", re.IGNORECASE)
NONSENSE_RE = re.compile(r"^[\?\*\.\,]+$")
NON_TURKISH_RE = re.compile(r"[a-zA-Z]{3,}")

def _sanitize_user_query(q: str) -> str:
    if not q:
        return ""
    q = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ\.\,\?\!]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q

def build_user_prompt(query: str, passages: List[Dict]) -> str:
    q_clean = _sanitize_user_query(query or "")

    if GREETINGS_RE.match(q_clean):
        return "KULLANICI SELAMLAŞMASI: Nazik bir şekilde karşılık ver ve 'Size nasıl yardımcı olabilirim?' diye sor."

    if NONSENSE_RE.match(q_clean) or len(q_clean) < 2:
        return "KULLANICI ANLAMSIZ GİRİŞ: 'Sorunuzu tam anlayamadım, hukuki bir konuda yardımcı olabilirim.' de."

    if NON_TURKISH_RE.search(q_clean) and not re.search(r"[çğıöşüÇĞİÖŞÜ]", q_clean):
        return "KULLANICI TÜRKÇE DIŞI GİRİŞ: 'Üzgünüm, yalnızca Türkçe dilinde yanıt verebilirim.' de."

    if any(w in q_clean.lower() for w in ["yemek", "spor", "film", "müzik", "tarif", "tatil", "oyun"]):
        return "KULLANICI SORUSU HUKUK DIŞI: 'Ben bir hukuk asistanıyım, hukuk dışı konularda bilgi veremem.' diye yanıtla."

    lines = [f"SORU:\n{q_clean}\n", "BAĞLAM PASAJLARI (karar_metni içeriği):\n"]
    count = 0
    for p in passages:
        if count >= MAX_TOTAL_PASSAGES:
            break

        full_text = (p.get('karar_metni') or '').strip()
        if not full_text:
            full_text = (p.get('karar') or p.get('karar_preview') or p.get('text_preview') or '').strip()
        if not full_text:
            continue

        head_bits = []
        if p.get("karar"):
            head_bits.append(str(p["karar"]).strip())
        elif p.get("sonuc"):
            head_bits.append(str(p["sonuc"]).strip())
        if p.get("dava_turu"):
            head_bits.append(str(p["dava_turu"]).strip())
        if p.get("doc_id"):
            head_bits.append(str(p["doc_id"]).strip())
        head = " — ".join([h for h in head_bits if h])

        snippet = full_text.replace("\n", " ")
        if len(snippet) > MAX_PASSAGE_CHARS:
            snippet = snippet[:MAX_PASSAGE_CHARS]

        idx = count + 1
        if head:
            lines.append(f"[{idx}] {head}\n{snippet}")
        else:
            lines.append(f"[{idx}] {snippet}")

        count += 1

    if count == 0:
        lines.append("[1] Bağlam bulunamadı.")

    lines.append("\nBu bilgileri kullanarak açık, öğretici ve doğru bir hukuki yanıt oluştur.")
    return "\n".join(lines)
