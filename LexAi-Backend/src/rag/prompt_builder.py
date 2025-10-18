import hashlib
from typing import List, Dict, Optional, Tuple
import re
from src.rag.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES

SYSTEM_PROMPT = """
#[ROL]
Sen bir Türk hukuk asistanısın. Türk mahkeme kararlarını ve mevzuatı temel alarak kullanıcıya güvenilir, sade ve anlaşılır açıklamalar yaparsın.  
Amacın, kullanıcıyı bilgilendirmek ve gerektiğinde bir sonraki adıma yönlendirmektir.
Sadece Türkçe cevaplara vereceksin. 

#[GÖREV]
- Kullanıcının sorduğu soruya, verilen pasajlardan **genelleme yaparak** cevap ver.  
- **Mahkeme, tarih veya dosya adı** belirtme. “Bölge Adliye Mahkemesi” ya da “Yargıtay” gibi ifadeler kullanma; onun yerine **“mahkemeler genellikle”** veya **“yargı mercileri çoğunlukla”** de.  
- Cevabın akıcı bir metin olarak gelsin; başlık, madde veya tablo kullanma (yalnızca gerçekten faydalıysa kısa maddeler olabilir).  
- Cümleler kısa ama anlam olarak dolu olsun; yüzeysel yanıtlar verme.  
- Gerektiğinde örnek ilkeleri sadeleştirerek açıkla: “Genellikle şu durumlarda nafaka artışı uygun görülür.”  
- Son kısımda kullanıcıya yönlendirme yap:  
  “Benzer davaları incelemek ister misiniz?” veya  
  “Bu konuda bir hukuk uzmanına danışmanız yararlı olabilir.”  

#[KANIT ZAYIFSA]
- Eğer pasajlar yeterli bilgi sunmuyorsa, bunu açıkça belirt (“Mevcut bilgiler sınırlı olsa da genel uygulama şöyledir…”).  
- Bu durumda genel ilkelere dayanarak güvenli bir açıklama yap.  

#[YASA MADDELERİ]
- Pasajlarda geçen kanun veya madde varsa, kısa ve sade biçimde açıkla:  
  “Türk Medeni Kanunu’nun 175. maddesi, boşanma sonrası yoksulluğa düşecek eşe nafaka bağlanabileceğini düzenler.”  
- Kanun metnini kopyalama; sadece anlamını açıkla.  
- Belge numarası, karar tarihi veya taraf bilgisi verme.  

#[ÜSLUP]
- Sadece Türkçe yaz. Bu prompt’un tamamı Türkçedir.
- Samimi ama profesyonel, öğretici bir ton kullan.  
- Kısa paragraflardan oluşan akıcı bir anlatım tercih et.  
- Gerektiğinde maddelendirme yapabilirsin ama cevabı tamamen listeye dönüştürme.  
- Gereksiz tekrar ve resmi dil kullanımından kaçın.  
- Doğal bir kapanış yapabilirsin (“Teşekkürler, umarım faydalı olmuştur.”).  

#[İÇERİK AKIŞI]
Cevabın doğal paragraf yapısında olmalı;  
- Önce konunun genel çerçevesi,  
- Ardından değerlendirme ve olası sonuçlar,  
- Varsa ilgili yasa maddesinin kısa açıklaması,  
- Son olarak yol gösterici bir kapanış.  
- Yalnızca gerekliyse maddelendirme yap. Her cevabı liste gibi yazma; paragraflar öncelikli olsun.

#[HEDEF]
Kullanıcıya:  
1. Anlamlı, bağlamsal bir açıklama,  
2. Gerekçeli, dengeli bir değerlendirme,  
3. Öğretici ve yönlendirici bir sonuç sun.  

#[EK KURALLAR]
- Kullanıcı selamlaşırsa (“merhaba”, “selam”, “nasılsın”) kibarca yanıt ver: “Merhaba, size nasıl yardımcı olabilirim?”
- Kullanıcı anlamsız semboller veya eksik şeyler yazarsa: “Sorunuzu tam olarak anlayamadım, isterseniz hukuki bir konuda yardımcı olabilirim.” de.
- Hukuk dışı bir konu sorarsa: “Ben bir hukuk asistanıyım, hukuk dışı konularda bilgi veremem.” diye yanıtla.
- Cevapta **her zaman tam karar metinlerinden** yararlan.

Cevabın kullanıcıyı bilgilendirsin, ancak hukuki tavsiye verme.
"""
GREETINGS_RE = re.compile(r"^\s*(merhaba|selam|günaydın|iyi günler|iyi akşamlar|nasılsın)\b", re.IGNORECASE)
NONSENSE_RE  = re.compile(r"^[\?\*\.\,]+$")
# Basit Türkçe olmayan metin yakalayıcı (yalın sezgi)
NON_TURKISH_RE = re.compile(r"[A-Za-z]{3,}")

def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def _sanitize_user_query(q: str) -> str:
    if not q:
        return ""
    q = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ\.\,\?\!]+", " ", q)
    return re.sub(r"\s+", " ", q).strip()

def build_user_prompt(
    query: str,
    passages: List[Dict],
    conversation_history: Optional[List[Dict]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Dönüş: (user_prompt, early_answer)
    early_answer dolu ise LLM'i çağırma; doğrudan onu gönder.
    """
    q_clean = _sanitize_user_query(query or "")

    # Erken dönüşler
    if GREETINGS_RE.match(q_clean):
        return None, "Merhaba"
    if NONSENSE_RE.match(q_clean) or len(q_clean) < 2:
        return None, "Sorunuzu tam olarak anlayamadım, isterseniz hukuki bir konuda yardımcı olabilirim."
    # Türkçe değil gibi görünüyorsa (ve içinde Türkçe karakter de yoksa) reddet
    if NON_TURKISH_RE.search(q_clean) and not re.search(r"[çğıöşüÇĞİÖŞÜ]", q_clean):
        return None, "Üzgünüm, yalnızca Türkçe dilinde yanıt verebilirim."
    if any(w in q_clean.lower() for w in ["yemek", "spor", "film", "müzik", "tarif", "tatil", "oyun"]):
        return None, "Ben bir hukuk asistanıyım, hukuk dışı konularda bilgi veremem."

    lines: List[str] = []

    # Konuşma bağlamı (son 5 tur)
    if conversation_history:
        lines.append("--- ÖNCEKİ KONUŞMA BAĞLAMI ---")
        for turn in conversation_history[-5:]:
            u = (turn.get("user") or "").strip()
            a = (turn.get("assistant") or "").strip()
            if u: lines.append(f"Kullanıcı: {u}")
            if a: lines.append(f"Asistan: {a}")

    # Güncel soru
    lines.append("\n--- GÜNCEL SORU ---")
    lines.append(q_clean)

    # Pasajlar (tam karar metni) — eşsizleştir + sınırla + kırp
    uniq = []
    seen = set()
    for p in passages or []:
        txt = (p.get("karar_metni") or p.get("text_full") or "").strip()
        if not txt:
            continue
        key = _sha1(txt)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(txt)

    print(f"[DEBUG] build_user_prompt → Toplam {len(passages)} pasaj geldi.")
    print(f"[DEBUG] Filtre sonrası {len(uniq)} eşsiz pasaj kaldı.")
    if uniq:
        print(f"[DEBUG] İlk pasaj örneği: {uniq[0][:300]}")
    else:
        print("[DEBUG] Hiç karar metni bulunamadı.")


    if uniq:
        lines.append("\n--- BENZER DAVALARIN TAM KARAR METİNLERİ ---")
        cap_n = max(1, int(MAX_TOTAL_PASSAGES))
        cap_c = max(200, int(MAX_PASSAGE_CHARS))
        for i, txt in enumerate(uniq[:cap_n], 1):
            snippet = txt.replace("\n", " ")[:cap_c]
            lines.append(f"[{i}] {snippet}")
    else:
        lines.append("\n--- BENZER DAVALARIN TAM KARAR METİNLERİ ---")
        lines.append("[bilgi yok]")

    # Yönlendirme
    lines.append(
        "\nYukarıdaki bağlamı dikkate alarak, belirtilen yanıt yapısını izleyen, kısa ve öğretici bir hukuki yanıt üret."
    )

    return "\n".join(lines), None