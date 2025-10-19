import hashlib
from typing import List, Dict, Optional, Tuple
import re
from src.rag.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES

SYSTEM_PROMPT = """
#[ROL]
Sen bir Türk hukuk asistanısın. Türk mahkeme kararlarını ve mevzuatı temel alarak kullanıcıya güvenilir, sade ve anlaşılır açıklamalar yaparsın.  
Amacın, kullanıcıyı bilgilendirmek ve gerektiğinde bir sonraki adıma yönlendirmektir.
Sadece Türkçe cevap vereceksin. 

#[GÖREV]
- Kullanıcının sorduğu soruya, verilen pasajlardan genelleme yaparak cevap ver.  
- Mahkeme, tarih veya dosya adı belirtme. “Bölge Adliye Mahkemesi” ya da “Yargıtay” gibi ifadeler kullanma; onun yerine “mahkemeler genellikle” veya “yargı mercileri çoğunlukla” de.  
- Cevabın akıcı bir metin olarak gelsin; kısa, açıklayıcı ve tekrarsız olsun.  
- Gerektiğinde örnek ilkeleri sadeleştirerek açıkla.  
- Sonunda kullanıcıyı yalnızca gerekiyorsa yönlendir (“Benzer davaları inceleyebilirsiniz.” gibi).  

#[KANIT ZAYIFSA]
- Eğer pasajlar yeterli bilgi sunmuyorsa, bunu açıkça belirt (“Mevcut bilgiler sınırlı olsa da genel uygulama şöyledir…”).  
- Bu durumda genel ilkelere dayanarak güvenli bir açıklama yap.  

#[YASA MADDELERİ]
- Pasajlarda geçen kanun veya madde varsa, kısa ve sade biçimde açıkla.  
- Kanun metnini kopyalama; sadece anlamını açıkla.  
- Belge numarası, karar tarihi veya taraf bilgisi verme.  

#[ÜSLUP]
- Doğrudan konuya gir, selamlama veya kapanış cümlesi kullanma (“merhaba”, “teşekkürler” vb. yok).  
- Samimi ama profesyonel, öğretici bir ton kullan.  
- Kısa paragraflardan oluşan akıcı bir anlatım tercih et.  
- Gerektiğinde maddelendirme yapabilirsin ama cevabı tamamen listeye dönüştürme.  
- Gereksiz tekrar ve kalıp ifadelerden kaçın.  

#[KONUŞMA BAĞLAMI]
Eğer kullanıcıyla önceki konuşmalardan bir bağlam verildiyse (“--- ÖNCEKİ KONUŞMA BAĞLAMI ---” başlığı altında),
bu geçmiş konuşmaları dikkate alarak, yeni sorunun önceki konuyla bağlantısını koruyacak şekilde yanıt ver.
Geçmiş konu tamamen alakasızsa, yeni konuyu bağımsız ele al.

#[HEDEF]
Kullanıcıya:  
1. Anlamlı, bağlamsal bir açıklama,  
2. Gerekçeli, dengeli bir değerlendirme,  
3. Öğretici ve yönlendirici bir sonuç sun.  

#[EK KURALLAR]
- Anlamsız veya hukuk dışı konularda kibarca yönlendir (“Bu konu hukuki değil, bu nedenle yanıt veremem.”).  
- Cevapta her zaman karar metinlerinden yararlan, ama doğrudan alıntı yapma.

Cevabın kullanıcıyı bilgilendirsin, ancak hukuki tavsiye verme.
"""

GREETINGS_RE = re.compile(r"^\s*(merhaba|selam|günaydın|iyi günler|iyi akşamlar|nasılsın)\b", re.IGNORECASE)
NONSENSE_RE = re.compile(r"^[\?\*\.\,]+$")
NON_TURKISH_RE = re.compile(r"[A-Za-z]{3,}")


def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _sanitize_user_query(q: str) -> str:
    if not q:
        return ""
    q = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ\.\,\?\!]+", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def _text_fields(payload: Dict) -> Tuple[str, str]:
    text_full = (
        payload.get("karar_metni")
        or payload.get("karar_metni_meta")
        or payload.get("karar_metni_raw")
        or payload.get("karar")
        or payload.get("text")
        or payload.get("full_text")
        or ""
    ).strip()
    text_repr = (payload.get("karar_preview") or text_full[:400]).strip()
    if len(text_full) > MAX_PASSAGE_CHARS:
        text_full = text_full[:MAX_PASSAGE_CHARS]
    return text_repr, text_full


def build_user_prompt(
    query: str,
    passages: List[Dict],
    conversation_history: Optional[List[Dict]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    q_clean = _sanitize_user_query(query or "")

    if GREETINGS_RE.match(q_clean):
        return None, "Sizi dinliyorum, sorunuz nedir?"
    if NONSENSE_RE.match(q_clean) or len(q_clean) < 2:
        return None, "Sorunuzu tam olarak anlayamadım, biraz daha açık yazar mısınız?"
    if NON_TURKISH_RE.search(q_clean) and not re.search(r"[çğıöşüÇĞİÖŞÜ]", q_clean):
        return None, "Üzgünüm, yalnızca Türkçe dilinde yanıt verebilirim."
    if any(w in q_clean.lower() for w in ["yemek", "spor", "film", "müzik", "tarif", "tatil", "oyun"]):
        return None, "Bu konu hukuk kapsamına girmiyor."

    parts: List[str] = []

    # --- geçmiş konuşmaları chat biçiminde ekle ---
    if conversation_history:
        for turn in conversation_history[-4:]:
            if "user" in turn and turn["user"]:
                parts.append(f"<|im_start|>user\n{turn['user']}<|im_end|>")
            elif "assistant" in turn and turn["assistant"]:
                parts.append(f"<|im_start|>assistant\n{turn['assistant']}<|im_end|>")

    # --- güncel kullanıcı sorusu ---
    parts.append(f"<|im_start|>user\n{q_clean}<|im_end|>")

    # --- benzer dava başlıkları ---
    similar_titles = []
    for p in passages or []:
        title = (
            p.get("dava_turu")
            or p.get("karar_ozeti")
            or p.get("karar")
            or p.get("sonuc")
            or p.get("karar_preview")
        )
        if title:
            similar_titles.append(str(title).strip())

    if similar_titles:
        parts.append("<|im_start|>system\n--- BENZER DAVALARIN KISA BAŞLIKLARI ---")
        for i, t in enumerate(similar_titles[:8], 1):
            parts.append(f"{i}. {t}")
        parts.append("<|im_end|>")

    # --- tam karar metinleri ---
    uniq, seen = [], set()
    for p in passages or []:
        _, full_text = _text_fields(p)
        if not full_text:
            continue
        key = _sha1(full_text)
        if key not in seen:
            seen.add(key)
            uniq.append(full_text)

    print(f"[DEBUG] build_user_prompt → Toplam {len(passages)} pasaj geldi.")
    print(f"[DEBUG] Filtre sonrası {len(uniq)} eşsiz pasaj kaldı.")
    if uniq:
        print(f"[DEBUG] İlk pasaj örneği: {uniq[0][:300]}")
    else:
        print("[DEBUG] Hiç karar metni bulunamadı.")

    if uniq:
        parts.append("<|im_start|>system\n--- BENZER DAVALARIN TAM KARAR METİNLERİ ---")
        cap_n = max(1, int(MAX_TOTAL_PASSAGES))
        cap_c = max(200, int(MAX_PASSAGE_CHARS))
        for i, txt in enumerate(uniq[:cap_n], 1):
            snippet = txt.replace("\n", " ")[:cap_c]
            parts.append(f"[{i}] {snippet}")
        parts.append("<|im_end|>")
    else:
        parts.append("<|im_start|>system\n--- BENZER DAVALARIN TAM KARAR METİNLERİ ---\n[bilgi yok]<|im_end|>")

    # --- talimat ---
    parts.append(
        "<|im_start|>system\nYukarıdaki konuşma ve karar metinlerine dayanarak, geçmiş diyalogla tutarlı, "
        "tekrarsız ve öğretici bir hukuki açıklama oluştur.<|im_end|>\n<|im_start|>assistant\n"
    )

    return "\n".join(parts), None
