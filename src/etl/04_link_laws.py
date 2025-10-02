import json
import os
import re
from typing import Dict, List, Optional, Tuple

# Statik bilinen kısaltmalar ve eski kanunlar
STATIC_ALIASES: Dict[str, Dict[str, str]] = {
    # HUMK (1086)
    "HUMK": {"canonical": "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu", "law_id": "1086"},
    "HMUK": {"canonical": "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu", "law_id": "1086"},
    "1086 sayılı HUMK": {"canonical": "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu", "law_id": "1086"},
    "1086 sayılı Kanun": {"canonical": "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu", "law_id": "1086"},
    "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu": {"canonical": "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu", "law_id": "1086"},

    # HMK (6100)
    "HMK": {"canonical": "6100 sayılı Hukuk Muhakemeleri Kanunu", "law_id": "6100"},
    "6100 sayılı HMK": {"canonical": "6100 sayılı Hukuk Muhakemeleri Kanunu", "law_id": "6100"},
    "6100 sayılı Kanun": {"canonical": "6100 sayılı Hukuk Muhakemeleri Kanunu", "law_id": "6100"},
    "6100 sayılı Hukuk Muhakemeleri Kanunu": {"canonical": "6100 sayılı Hukuk Muhakemeleri Kanunu", "law_id": "6100"},

    # Diğer örnekler
    "2828 sayılı Sosyal Hizmetler Kanunu": {"canonical": "2828 sayılı Sosyal Hizmetler Kanunu", "law_id": "2828"},
    "5395 sayılı Çocuk Koruma Kanunu": {"canonical": "5395 sayılı Çocuk Koruma Kanunu", "law_id": "5395"},
    "4421 sayılı Kanun": {"canonical": "4421 sayılı Kanun", "law_id": "4421"},
}

# Dinamik olarak mevzuat kataloğundan doldurulacak
DYNAMIC_ALIASES: Dict[str, Dict[str, str]] = {}

LAW_NAME_PATTERN = re.compile(
    r"(?:(?P<law_id>\d{3,4})\s*sayılı\s*)?"
    r"(?P<name>HUMK|HMUK|HMK|Hukuk\s+Usulü\s+Muhakemeleri\s+Kanunu|"
    r"Hukuk\s+Muhakemeleri\s+Kanunu|Sosyal\s+Hizmetler\s+Kanunu|"
    r"Çocuk\s+Koruma\s+Kanunu|\d{3,4}\s*sayılı\s*Kanun)",
    flags=re.IGNORECASE,
)
ARTICLE_PATTERN = re.compile(
    r"madde\s*:?[\s\u00A0]*([0-9]+(?:\/[0-9]+)?(?:-[IVXLC]+|\/[IVXLC]+|\/[A-Za-z0-9\-]+)?)",
    flags=re.IGNORECASE,
)
PARAGRAPH_PATTERN = re.compile(
    r"(?:fıkra|son|\b\/)([0-9IVXLC]+)",
    flags=re.IGNORECASE,
)

# --- Fonksiyonlar ---
def hydrate_dynamic_aliases() -> None:
    """Projede mevzuat kataloglarından DYNAMIC_ALIASES sözlüğünü doldurur."""
    global DYNAMIC_ALIASES
    if DYNAMIC_ALIASES:
        return

    catalog_paths = [
        "/Users/eslemnurgok/Downloads/LexAi/data/raw/mevzuat-kanunlar.json",
        "/Users/eslemnurgok/Downloads/LexAi/data/raw/mevzuat.json",
        "/Users/eslemnurgok/Downloads/LexAi/data/raw/mevzuat_meta_metadata.json",
        "/Users/eslemnurgok/Downloads/LexAi/data/raw/cb_bk__kurulu_yonetmelik.json",
        "cb_kararname.json",
    ]

    for path in catalog_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if isinstance(data, list):
            for item in data:
                law_no = str(item.get("mevzuatNo") or item.get("kanunNo") or "").strip()
                name = (item.get("mevAdi") or item.get("ad") or "").strip()
                if not name:
                    continue

                canonical = name
                meta = {"canonical": canonical}
                if law_no:
                    meta["law_id"] = law_no

                # Aliases
                DYNAMIC_ALIASES[name] = meta
                if law_no:
                    DYNAMIC_ALIASES[f"{law_no} sayılı {name}"] = meta
                upper = name.upper()
                if "HUKUK MUHAKEMELER" in upper and "KANUNU" in upper:
                    DYNAMIC_ALIASES["HMK"] = meta
                if ("HUKUK USUL" in upper or "HUKUK USULÜ" in upper) and "MUHAKEMELER" in upper and "KANUNU" in upper:
                    DYNAMIC_ALIASES["HUMK"] = {"canonical": canonical, "law_id": law_no or "1086"}
                    DYNAMIC_ALIASES["HMUK"] = {"canonical": canonical, "law_id": law_no or "1086"}

def normalize_law_name(raw: str) -> Tuple[str, Optional[str]]:
    """Ham kanun ismini canonical ve law_id’ye dönüştürür."""
    key = raw.strip()

    # Boş veya saçma değerler düzeltiliyor
    if not key or key.upper() in {"SAYILI", "HUKUK"}:
        return None, None

    if key in STATIC_ALIASES:
        m = STATIC_ALIASES[key]
        return m["canonical"], m.get("law_id")
    for alias, meta in STATIC_ALIASES.items():
        if key.lower() == alias.lower():
            return meta["canonical"], meta.get("law_id")
    if key in DYNAMIC_ALIASES:
        m = DYNAMIC_ALIASES[key]
        return m["canonical"], m.get("law_id")
    for alias, meta in DYNAMIC_ALIASES.items():
        if key.lower() == alias.lower():
            return meta["canonical"], meta.get("law_id")

    # Eğer sadece "XXXX sayılı Kanun" gelirse
    m = re.search(r"(\d{3,4})\s*sayılı", key)
    if m:
        law_id = m.group(1)
        if law_id == "1086":
            return "1086 sayılı Hukuk Usulü Muhakemeleri Kanunu", "1086"
        if law_id == "6100":
            return "6100 sayılı Hukuk Muhakemeleri Kanunu", "6100"
        return f"{law_id} sayılı Kanun", law_id

    return key, None

def build_candidate_urls(canonical_name: str, law_id: Optional[str], article: Optional[str]) -> List[str]:
    """Kanun ve madde bazlı bilgilendirici URL pattern’leri oluşturur."""
    urls: List[str] = []
    if not canonical_name:
        return urls
    query = canonical_name
    if article:
        query += f" madde {article}"
    urls.append(f"mevzuat: {canonical_name}")
    if article:
        urls.append(f"mevzuat: {canonical_name} madde {article}")
    if law_id:
        urls.append(f"law_id:{law_id}")
    return urls

def scan_text_for_laws(text: str) -> List[Dict[str, Optional[str]]]:
    """Verilen metindeki kanun referanslarını tespit eder."""
    links: List[Dict[str, Optional[str]]] = []
    if not text:
        return links
    for match in LAW_NAME_PATTERN.finditer(text):
        raw_name = match.group(0)
        canonical, law_id = normalize_law_name(raw_name)
        if not canonical:
            continue
        tail = text[match.end(): match.end() + 80]
        art = None
        par = None
        am = ARTICLE_PATTERN.search(tail)
        if am:
            art = am.group(1)
            pm = PARAGRAPH_PATTERN.search(tail)
            if pm:
                par = pm.group(1)
        links.append({
            "law_raw": raw_name,
            "law_canonical": canonical,
            "law_id": law_id,
            "article": art,
            "paragraph": par,
            "source": "text_scan",
            "span": raw_name,
            "candidate_urls": build_candidate_urls(canonical, law_id, art),
        })
    return links

def normalize_record_links(record: Dict) -> None:
    """Bir kayıttaki tüm kanun referanslarını normalize eder ve law_links alanına ekler."""
    law_links: List[Dict[str, Optional[str]]] = []

    # 1. kanun_atiflari
    for ref in record.get("kanun_atiflari", []) or []:
        raw_name = ref.get("kanun") or ""
        canonical, law_id = normalize_law_name(raw_name)
        if not canonical:
            continue
        article = ref.get("madde")
        paragraph = ref.get("fikra")
        span = ref.get("span")
        law_links.append({
            "law_raw": raw_name,
            "law_canonical": canonical,
            "law_id": law_id,
            "article": article,
            "paragraph": paragraph,
            "source": "kanun_atiflari",
            "span": span,
            "candidate_urls": build_candidate_urls(canonical, law_id, article),
        })

    # 2. metin alanlarından tarama
    text_fields: List[str] = []
    if isinstance(record.get("karar"), str):
        text_fields.append(record["karar"])
    if isinstance(record.get("gerekce"), list):
        text_fields.extend([g for g in record["gerekce"] if isinstance(g, str)])
    if isinstance(record.get("hikaye"), list):
        text_fields.extend([h for h in record["hikaye"] if isinstance(h, str)])

    for txt in text_fields:
        for link in scan_text_for_laws(txt):
            law_links.append(link)

    # 3. tekilleştirme
    seen = set()
    deduped: List[Dict] = []
    for l in law_links:
        key = (l.get("law_canonical"), l.get("article"), l.get("paragraph"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(l)

    record["law_links"] = deduped

def process_file(input_path: str, output_path: str) -> None:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Bulunamadı: {input_path}")

    hydrate_dynamic_aliases()

    # 1. JSONL oku
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue

    # 2. normalize
    for idx, record in enumerate(records, start=1):
        try:
            normalize_record_links(record["record"])
        except Exception:
            pass
        if idx % 1000 == 0:
            print(f"İşlenen kayıt: {idx}")

    # 3. tekrar JSONL yaz
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Tamamlandı. Çıktı: {output_path}")

if __name__ == "__main__":
    IN_FILE = "/Users/eslemnurgok/Downloads/LexAi/data/interim/03_validated.jsonl"
    OUT_FILE = "/Users/eslemnurgok/Downloads/LexAi/data/interim/04_link_laws.jsonl"
    process_file(IN_FILE, OUT_FILE)
