"""
03_validate_normalize.py
------------------------
Amaç:
- 02_extract_llm_parsed.json içindeki LLM JSON çıktısını şemaya göre doğrulamak ve normalize etmek.
- Kurallar:
  * 'sonuc' alanını sabit listeye göre normalize eder: onama|bozma|ret|kabul|vs.
  * 'kanun_atiflari' içindeki 'kanun' ve 'madde' ayrıştırılır.
  * Tarihler YYYY-MM-DD formatına çevrilir.
  * 'adimlar' içindeki 'spans': [] olan adımlar çıkarılır.
  * Kalite bayrakları eklenir: law_without_span, few_steps, steps_dropped.
"""

import json
import re
from pathlib import Path
from datetime import datetime

INPUT_PATH = Path("data/interim/02_extract_llm_parsed.json")
OUTPUT_PATH = Path("data/interim/03_validated.jsonl")

VALID_SONUC_VALUES = [
    "onama", "bozma", "kısmen_bozma", "duzelterek_onama", "ret", "kabul",
    "kısmen_kabul", "diger"
]

KANUN_REGEX = re.compile(r"\b([A-ZÇĞİÖŞÜ]{2,5})\b")
TARIH_FORMATLARI = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y")

def normalize_date(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    for fmt in TARIH_FORMATLARI:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None

def normalize_sonuc(value):
    if not value or not isinstance(value, str):
        return "diger"
    val = value.strip().lower()
    for v in VALID_SONUC_VALUES:
        if v in val:
            return v
    if "red" in val or "reddi" in val:
        return "ret"
    if "kabul" in val:
        return "kabul"
    return "diger"

def normalize_kanun(kanun_str):
    if not kanun_str or not isinstance(kanun_str, str):
        return None
    match = KANUN_REGEX.search(kanun_str.upper())
    return match.group(1) if match else None

def validate_and_normalize_record(_id, content):
    record = content.copy()
    quality_flags = []

    # SONUC normalize
    record["sonuc"] = normalize_sonuc(record.get("sonuc"))

    # GEREKÇE - zorunlu, liste olmalı
    if not isinstance(record.get("gerekce"), list):
        record["gerekce"] = [record.get("gerekce")] if record.get("gerekce") else []

    # METIN NUMARALARI normalize
    for key in ["metin_esas_no", "metin_karar_no"]:
        items = record.get(key)
        if not isinstance(items, list):
            record[key] = [items] if items else [None]
        else:
            record[key] = list(set(items)) or [None]

    # KANUN ATIFLARI normalize
    for i, k in enumerate(record.get("kanun_atiflari", [])):
        if isinstance(k, dict):
            k["kanun"] = normalize_kanun(k.get("kanun"))
            if k.get("madde"):
                k["madde"] = re.sub(r"\D+", "", str(k["madde"])) or None
            k["fikra"] = str(k.get("fikra")) if k.get("fikra") else None
        else:
            record["kanun_atiflari"][i] = {
                "kanun": None, "madde": None, "fikra": None, "span": str(k)
            }
    # quality flag
    if any(k.get("kanun") and not k.get("span") for k in record.get("kanun_atiflari", [])):
        quality_flags.append("law_without_span")

    # TALEPLER vb. boş liste kontrolü
    for key in ["deliller", "talepler", "gecici_tedbirler"]:
        if not isinstance(record.get(key), list):
            record[key] = []

    # BASVURU YOLU normalize
    yollar = record.get("basvuru_yolu", [])
    if isinstance(yollar, str):
        yollar = [yollar]
    yollar = [y for y in yollar if y in {"istinaf", "temyiz", "karar_düzeltme", "yok"}]
    record["basvuru_yolu"] = yollar or ["yok"]

    # ONEMLI TARIHLER
    for item in record.get("onemli_tarihler", []):
        if "tarih" in item:
            item["tarih"] = normalize_date(item["tarih"])

    # ADIMLAR: spans boşsa çıkar
    steps = record.get("adimlar", [])
    kept, dropped = [], 0
    for a in steps:
        if isinstance(a, dict) and a.get("spans"):
            kept.append(a)
        else:
            dropped += 1
    record["adimlar"] = kept
    if dropped > 0:
        quality_flags.append("steps_dropped")

    if len(kept) < 3:
        quality_flags.append("few_steps")

    # HIKAYE normalize
    if not isinstance(record.get("hikaye"), list):
        record["hikaye"] = [record.get("hikaye")] if record.get("hikaye") else []

    # Zorunlu alanlar: yoksa flagle
    for key in ["dava_turu", "taraf_iliskisi", "sonuc", "karar", "gerekce", "basvuru_yolu", "adimlar", "hikaye"]:
        if not record.get(key):
            quality_flags.append(f"missing_{key}")

    return {
        "id": _id,
        "record": record,
        "quality_flags": sorted(list(set(quality_flags)))
    }

def main():
    if not INPUT_PATH.exists():
        print(f"❌ Girdi dosyası bulunamadı: {INPUT_PATH}")
        return

    parsed = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as out_f:
        for _id, content in parsed.items():
            try:
                result = validate_and_normalize_record(_id, content)
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            except Exception as e:
                out_f.write(json.dumps({
                    "id": _id,
                    "record": content,
                    "quality_flags": ["processing_error"],
                    "error": str(e)
                }, ensure_ascii=False) + "\n")

    print(f"✅ {OUTPUT_PATH.name} başarıyla oluşturuldu.")

if __name__ == "__main__":
    main()
