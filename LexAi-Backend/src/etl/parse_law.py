#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kanun PDF'inden maddeleri JSON'a çevirir.
- Uyarı/önsöz, sayfa başlık/altlıkları ve bölüm başlıklarını (BİRİNCİ KISIM/FASIL/BAP vb.) atlar.
- "Madde <num>" ve "GEÇİCİ MADDE <num>" bloklarını ayrıştırır.
- Geçici maddeleri ayrı anahtar altında toplar.
- PDF'te metin yoksa (tarama) otomatik OCR fallback (pytesseract) dener.

Kullanım:
    python parse_law_pdf.py --pdf data/raw/1086.pdf --out data/interim/1086.json --url "https://www.mevzuat.gov.tr/..."
"""

import re
import json
import argparse
from collections import Counter
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import fitz  # PyMuPDF

# OCR opsiyonel
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# -------- Yardımcılar ---------------------------------------------------------

UPPER_WORDS = set("""
BİRİNCİ İKİNCİ ÜÇÜNCÜ DÖRDÜNCÜ BEŞİNCİ ALTINCI YEDİNCİ SEKİZİNCİ DOKUZUNCU ONUNCU
BAP FASIL KISIM BÖLÜM UMUMİ GENEL HÜKÜMLER
""".split())

MADDE_RE = re.compile(
    r"(?P<label>Madde|MADDE)\s+(?P<num>\d+)\s*[-–—:]?\s*(?P<title>\".+?\"|[A-ZÇĞİÖŞÜ][^.\n]{0,80})?",
    flags=re.UNICODE
)
GECICI_RE = re.compile(
    r"(?P<label>GEÇİCİ\s+MADDE)\s+(?P<num>\d+)\s*[-–—:]?",
    flags=re.UNICODE
)

def normalize_spaces(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def is_all_caps_heading(line: str) -> bool:
    t = line.strip()
    if len(t) < 3:
        return False
    # Tamamen büyük (noktalama/sayı izinli) ve bilinen anahtarlar içeriyorsa
    if re.fullmatch(r"[A-ZÇĞİÖŞÜ0-9 .,'’\-()]+", t) and any(w in UPPER_WORDS for w in t.split()):
        return True
    # "BİRİNCİ KISIM/FASIL/BAP ..." kalıbı
    if re.fullmatch(r"(BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU)\s+(BAP|FASIL|KISIM)(\s+[A-ZÇĞİÖŞÜ ]+)?", t):
        return True
    return False

def strip_inline_footnote_markers(text: str) -> str:
    # Metin içindeki (1), (2) gibi üstsimge/dipnot işaretlerini hafifçe temizle
    return re.sub(r"\( ?\d{1,2} ?\)", "", text)

def detect_repeating_headers_footers(pages_text: List[str]) -> Tuple[set, set]:
    """Sayfaların ilk/son 2 satırlarından en sık tekrar edenleri 'başlık/altlık' say."""
    head_counter, foot_counter = Counter(), Counter()
    for txt in pages_text:
        lines = [l for l in txt.splitlines() if l.strip()]
        if not lines:
            continue
        for l in lines[:2]:
            head_counter[l.strip()] += 1
        for l in lines[-2:]:
            foot_counter[l.strip()] += 1
    common_heads = {l for l, c in head_counter.most_common(3) if c >= 2}
    common_foots = {l for l, c in foot_counter.most_common(3) if c >= 2}
    return common_heads, common_foots

def clean_page_text(txt: str, common_heads: set, common_foots: set) -> str:
    lines = txt.splitlines()
    cleaned = []
    for l in lines:
        sl = l.strip()
        if not sl:
            continue
        if sl in common_heads or sl in common_foots:
            continue
        # Tek başına sayfa numarası gibi
        if re.fullmatch(r"\d{1,4}", sl):
            continue
        cleaned.append(l)
    out = "\n".join(cleaned)
    out = strip_inline_footnote_markers(out)
    return normalize_spaces(out)

def pdf_to_text(pdf_path: Path) -> Tuple[str, bool]:
    """Metin katmanını kullanarak PDF'ten metin çıkar. (text, used_ocr=False)"""
    doc = fitz.open(pdf_path)
    pages_text = []
    text_chars_total = 0
    for p in doc:
        txt = p.get_text("text")
        pages_text.append(txt)
        text_chars_total += len(txt or "")
    if text_chars_total > 50:  # basit eşik: metin katmanı var
        heads, foots = detect_repeating_headers_footers(pages_text)
        cleaned_pages = [clean_page_text(t, heads, foots) for t in pages_text]
        return "\n".join(cleaned_pages), False
    return "", False  # metin yok/çok az

def ocr_pdf_to_text(pdf_path: Path) -> str:
    """pytesseract ile OCR."""
    if not OCR_AVAILABLE:
        raise RuntimeError("OCR gerekli ama pytesseract/Pillow bulunamadı. `pip install pytesseract pillow`")
    doc = fitz.open(pdf_path)
    pages = []
    for p in doc:
        # 300 DPI render
        pix = p.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(pytesseract.image_to_string(img, lang="tur"))  # Türkçe dil paketi yüklü olmalı
    return "\n\n".join(pages)

def split_articles(full_text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Madde ve Geçici Madde bloklarını çıkar; bölüm başlıklarını/önsözü at."""
    # Bölüm başlıklarını ve kısa alt başlık satırlarını filtrele
    filt_lines = []
    for raw in full_text.splitlines():
        s = raw.strip()
        if not s:
            filt_lines.append("")
            continue
        if is_all_caps_heading(s):
            continue
        # "Umumi hükümler" gibi başlığın alt satırı (kısa, 1-4 kelime, 'madde' içermeyen)
        if re.fullmatch(r"[A-ZÇĞİÖŞÜI][a-zçğıöşüı ]{1,35}", s) and len(s.split()) <= 4 and "madde" not in s.lower():
            continue
        filt_lines.append(raw)
    text = "\n".join(filt_lines)

    # İlk gerçek maddeye kadar olan kısmı (uyarı/önsöz) at
    first = None
    m1 = MADDE_RE.search(text)
    m2 = GECICI_RE.search(text)
    if m1 and m2:
        first = min(m1.start(), m2.start())
    elif m1:
        first = m1.start()
    elif m2:
        first = m2.start()
    else:
        return [], []
    text = text[first:]

    matches = []
    for m in MADDE_RE.finditer(text):
        matches.append(("normal", m.start(), m))
    for m in GECICI_RE.finditer(text):
        matches.append(("gecici", m.start(), m))
    matches.sort(key=lambda x: x[1])

    normal, gecici = [], []
    for i, (typ, start, m) in enumerate(matches):
        end = matches[i + 1][1] if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()

        if typ == "normal":
            num = int(m.group("num"))
            title = (m.group("title") or "").strip().strip("“”\"' ")
            block_body = block[m.end() - start:].strip()
            block_body = re.sub(r"^[–—:\s]+", "", block_body)
            normal.append({
                "no": num,
                "baslik": title if title and "madde" not in title.lower() else None,
                "metin": block_body.strip()
            })
        else:
            num = int(m.group("num"))
            block_body = block[m.end() - start:].strip()
            block_body = re.sub(r"^[–—:\s]+", "", block_body)
            gecici.append({
                "no": num,
                "metin": block_body.strip()
            })

    return normal, gecici

def heuristics_extract_meta(full_text: str) -> Dict[str, Optional[str]]:
    """Baş kısmından kanun adı/no/kabul tarihi tahmini."""
    head = "\n".join(full_text.splitlines()[:150])
    name = None
    m_name = re.search(r"([A-ZÇĞİÖŞÜ ]{10,})\s+KANUNU", head)
    if m_name:
        name = (m_name.group(1).title().strip() + " Kanunu")

    no = None
    m_no = re.search(r"Kanun\s*Numarası\s*:\s*(\d+)", head, flags=re.IGNORECASE)
    if m_no:
        no = m_no.group(1)

    kabul = None
    m_k = re.search(r"Kabul\s*Tarihi\s*:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", head, flags=re.IGNORECASE)
    if m_k:
        kabul = m_k.group(1)

    return {"ad": name, "kanun_no": no, "kabul_tarihi": kabul}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="Girdi PDF yolu (örn: data/raw/1086.pdf)", default=Path("data/raw/1086.pdf"))
    ap.add_argument("--out", help="Çıktı JSON yolu", default=Path("data/raw/1086_parse.json"))
    ap.add_argument("--url", default=None, help="İsteğe bağlı kaynak URL’si (örn: Resmî Gazete linki)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    out_path = Path(args.out)
    source_url = args.url

    if not pdf_path.exists():
        raise FileNotFoundError(f"Girdi PDF bulunamadı: {pdf_path}")

    # 1) PDF'ten metine
    text, used_ocr = pdf_to_text(pdf_path)
    # 2) Gerekirse OCR fallback
    if not text:
        if OCR_AVAILABLE:
            print("Metin katmanı bulunamadı. OCR ile çıkarılıyor...")
            text = ocr_pdf_to_text(pdf_path)
            used_ocr = True
        else:
            raise RuntimeError("PDF metin içerik çıkmadı ve OCR kullanılamıyor (pytesseract bulunamadı).")

    # 3) Ayrıştır
    normal, gecici = split_articles(text)
    meta = heuristics_extract_meta(text)

    out: Dict[str, Any] = {
        "kanun": meta,
        "maddeler": normal,
        "gecici_maddeler": gecici,
        "source_url": source_url,
        "extraction": {
            "used_ocr": used_ocr,
            "pages": None  
        }
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Yazıldı: {out_path}")
    print(f"Maddeler: {len(normal)} | Geçici: {len(gecici)} | OCR: {used_ocr}")

if __name__ == "__main__":
    main()
