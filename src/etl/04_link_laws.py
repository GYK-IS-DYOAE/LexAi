# -*- coding: utf-8 -*-
"""
03_validated.jsonl içindeki "kanun_atiflari" öğelerini,
yalnızca data/interim/mevzuat_parsed.jsonl kataloğuna bakarak
kanun numarası ve madde metni ile zenginleştirir.

Giriş:
- data/interim/mevzuat_parsed.jsonl  (katalog)
- data/interim/03_validated.jsonl    (validasyon verisi)

Çıkış:
- data/interim/03_validated.linked.jsonl  (zenginleştirilmiş kayıtlar)
"""

import io
import os
import re
import json
import argparse
from typing import Dict, Any, Optional

# -------------------------
# Yardımcılar
# -------------------------
def ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def read_jsonl(path: str):
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def write_jsonl(path: str, items):
    ensure_dir(path)
    with io.open(path, "w", encoding="utf-8") as f:
        for obj in items:
            f.write(json.dumps(obj, ensure_ascii=False))
            f.write("\n")

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

# -------------------------
# Eşleştirme için kısaltma -> kanun_no sözlüğü
# -------------------------
ABBR_TO_NO: Dict[str, int] = {
    "HUMK": 1086, "HMUK": 1086,
    "HMK": 6100,
    "TCK": 5237,
    "CMK": 5271,
    "TMK": 4721,
    "TBK": 6098,
    "TTK": 6102,
    "IİK": 2004, "İİK": 2004,
    "IYUK": 2577, "İYUK": 2577,
    "KVKK": 6698,
    "KABAHATLER": 5326,
    "KABAHATLER KANUNU": 5326,
    "EHK": 5809,
    "SKDM": 0
}

def norm_abbr(s: str) -> str:
    s = (s or "").strip()
    s = s.replace(".", "")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("İ", "I")
    s = s.upper()
    s = re.sub(r"\s+", " ", s)
    return s

KANUN_NO_RE = re.compile(r"(\d{3,4})\s*(?:sayılı|sayili)?", re.IGNORECASE)

def extract_law_no_from_kanun_field(kanun_field: str) -> Optional[int]:
    if not kanun_field:
        return None
    m = KANUN_NO_RE.search(kanun_field)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    stripped = kanun_field.strip()
    if stripped.isdigit():
        return int(stripped)
    ab = norm_abbr(stripped)
    if ab in ABBR_TO_NO and ABBR_TO_NO[ab] > 0:
        return ABBR_TO_NO[ab]
    nn = rough_expand_to_number(ab)
    return nn

def rough_expand_to_number(ab_upper: str) -> Optional[int]:
    txt = ab_upper
    if "HUKUK MUHAKEMELERI KANUNU" in txt or "HUKUK MUHAKEMELERİ KANUNU" in txt:
        return 6100
    if "HUKUK USULU MUHAKEMELERI KANUNU" in txt or "HUKUK USULÜ MUHAKEMELERİ KANUNU" in txt:
        return 1086
    if "TURK CEZA KANUNU" in txt or "TÜRK CEZA KANUNU" in txt:
        return 5237
    if "CEZA MUHAKEMESI KANUNU" in txt or "CEZA MUHAKEMESİ KANUNU" in txt:
        return 5271
    if "TURK MEDENI KANUNU" in txt or "TÜRK MEDENİ KANUNU" in txt:
        return 4721
    if "TURK BORCLAR KANUNU" in txt or "TÜRK BORÇLAR KANUNU" in txt:
        return 6098
    if "TURK TICARET KANUNU" in txt or "TÜRK TİCARET KANUNU" in txt:
        return 6102
    if "ICRA" in txt and "IFLAS" in txt:
        return 2004
    if "IDARI YARGILAMA USULU" in txt or "İDARİ YARGILAMA USULÜ" in txt:
        return 2577
    if "KABAHATLER" in txt:
        return 5326
    if "ELEKTRONIK HABERLESME" in txt or "ELEKTRONİK HABERLEŞME" in txt:
        return 5809
    if "KISIS" in txt and "VERI" in txt:
        return 6698
    if "CEZA MUHAKEMELERI USULU KANUNU" in txt or "CEZA MUHAKEMELERİ USULÜ KANUNU" in txt:
        return 1412
    return None

# -------------------------
# KataloguOku
# -------------------------
def load_catalog(catalog_path: str):
    by_no: Dict[int, Dict[str, Any]] = {}
    by_title_lower: Dict[str, int] = {}
    for law in read_jsonl(catalog_path):
        no = law.get("kanun_no")
        if isinstance(no, int):
            by_no[no] = law
        title = normalize_text(law.get("kanun_adi", ""))
        if title:
            by_title_lower[title.lower()] = no if isinstance(no, int) else None
    return by_no, by_title_lower

# -------------------------
# Madde metni çek
# -------------------------
def get_article_text(law_obj: Dict[str, Any], madde_str: str) -> Optional[str]:
    if not law_obj or not madde_str:
        return None
    key = str(madde_str).strip()
    maddeler = law_obj.get("maddeler") or {}
    if key in maddeler:
        return normalize_text(maddeler[key])
    key_digits = re.sub(r"\D+", "", key)
    if key_digits and key_digits in maddeler:
        return normalize_text(maddeler[key_digits])
    gms = law_obj.get("gecici_maddeler") or {}
    if key in gms:
        return normalize_text(gms[key])
    if key_digits and key_digits in gms:
        return normalize_text(gms[key_digits])
    return None

# -------------------------
# GÜNCELLENMİŞ TEK ATIF ZENGİNLEŞTİRME
# -------------------------
def enrich_citation(cit: Dict[str, Any], catalog_by_no: Dict[int, Dict[str, Any]], catalog_by_title: Dict[str, int]) -> Dict[str, Any]:
    kanun_field = cit.get("kanun", "")
    law_no = extract_law_no_from_kanun_field(kanun_field)

    if law_no is None and kanun_field:
        k = normalize_text(kanun_field).lower()
        if k in catalog_by_title and isinstance(catalog_by_title[k], int):
            law_no = catalog_by_title[k]
        else:
            for title_lower, no in catalog_by_title.items():
                if no is None:
                    continue
                if k and k in title_lower:
                    law_no = no
                    break

    if law_no is not None and law_no in catalog_by_no:
        law_obj = catalog_by_no[law_no]

        out = dict(cit)
        out["law_id"] = str(law_no)

        madde_raw = cit.get("madde")
        madde_no = str(madde_raw).strip() if madde_raw else None

        if madde_no:
            # SADECE ilgili maddeyi getir
            madde_text = get_article_text(law_obj, madde_no)
            out["law_description"] = {
                "kanun_adi": law_obj.get("kanun_adi"),
                "madde": madde_text if madde_text else None
            }
        else:
            # Madde yoksa TÜM maddeleri getir
            all_articles = law_obj.get("maddeler") or {}
            enriched_all = {k: normalize_text(v) for k, v in all_articles.items()}
            out["law_description"] = {
                "kanun_adi": law_obj.get("kanun_adi"),
                "maddeler": enriched_all
            }
        return out

    return cit

# -------------------------
# Ana akış
# -------------------------
def main():
    ap = argparse.ArgumentParser(description="03_validated.jsonl içindeki kanun atıflarını mevzuat kataloğu ile zenginleştirir.")
    ap.add_argument("--catalog", default="data/interim/mevzuat_parsed.jsonl",
                    help="Mevzuat kataloğu (JSONL)")
    ap.add_argument("--inp", default="data/interim/03_validated.jsonl",
                    help="Zenginleştirilecek dosya (JSONL)")
    ap.add_argument("--out", default="data/interim/03_validated.linked.jsonl",
                    help="Çıktı (JSONL)")
    args = ap.parse_args()

    catalog_by_no, catalog_by_title = load_catalog(args.catalog)

    def gen():
        for rec in read_jsonl(args.inp):
            if isinstance(rec.get("kanun_atiflari"), list):
                enriched = [
                    enrich_citation(cit, catalog_by_no, catalog_by_title)
                    for cit in rec["kanun_atiflari"]
                ]
                rec["kanun_atiflari"] = enriched
            yield rec

    write_jsonl(args.out, gen())

if __name__ == "__main__":
    main()
