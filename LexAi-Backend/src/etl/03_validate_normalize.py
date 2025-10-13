# -*- coding: utf-8 -*-
"""
03_validate_normalize.py
------------------------
1) data/interim/02_extract_llm.jsonl dosyasını okur: {"Id": "...", "output": {...}}
2) VALIDASYON + NORMALİZASYON yapar (flatten edilmiş çıktı üretir):
   - zorunlu alanlar: dava_turu, taraf_iliskisi, sonuc, karar, gerekce, basvuru_yolu, adimlar, hikaye
   - tip düzeltme: beklenen yerlerde string/list/dict'e normalize
   - null/boş düzeltme: None -> "" veya []
   - tarih normalize: YYYY-MM-DD (başarısızsa ""), adimlar.tarih daima string (boşsa "")
   - sonuc & basvuru_yolu normalize
   - kanun_atiflari: alanları string'leştir
   - metin_esas_no / metin_karar_no: liste + tekilleştir
   - dava_turu: "_" -> " ", Türkçe-duyarlı lower (İ→i, I→ı), strip, iç boşlukları sadeleştir
   - karar: baştaki/sondaki boşlukları kes (strip)

Çıktılar:
- data/interim/03_validated.jsonl (FLAT JSON satırları)
- data/interim/validate.json (özet istatistikler)
- data/interim/sample_ft_dava_turu.jsonl (her unique dava_turu için max 5 örnek)

Çalıştırma:
$ python 03_validate_normalize.py
"""

import json
import re
from pathlib import Path
from datetime import datetime

# ==============================
# Config
# ==============================
INPUT_PATH   = Path("data/interim/02_extract_llm.jsonl")
OUTPUT_PATH  = Path("data/interim/03_validated.jsonl")
REPORT_PATH  = Path("data/interim/validate.json")
SAMPLE_OUTPUT_PATH = Path("data/interim/sample_ft_dava_turu.jsonl")

# ==============================
# Helpers
# ==============================
DATE_FORMATS = (
    "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y",
    "%d-%m-%Y", "%Y/%m/%d", "%d %m %Y",
    "%d.%m.%y", "%d/%m/%y", "%d-%m-%y"
)

SONUC_CANONICAL = {
    "onama": ["onama", "onan", "onand", "onanm"],
    "bozma": ["bozma", "bozul", "bozulmas", "bozulmasına"],
    "kısmen_bozma": ["kısmen boz", "kismen boz", "kısmi boz"],
    "duzelterek_onama": ["düzelterek onama", "düzelt", "duzelterek onama"],
    "ret": ["ret", "redd", "reddine"],
    "kabul": ["kabul", "kabulüne"],
    "kısmen_kabul": ["kısmen kabul", "kismen kabul"],
    "gönderme": ["gönderilmesine", "hgk'ya gönder", "genel kurula gönder", "dosyanın gönderilmesine"],
    "diger": []
}

BASVURU_YOLU_ALLOWED = {
    "istinaf": ["istinaf"],
    "temyiz": ["temyiz"],
    "karar_düzeltme": ["karar düzeltme", "karar duzeltme", "düzeltme"],
    "yok": ["yok", "bulunmuyor", "none", "null"]
}

def ensure_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, str):
        return x
    return json.dumps(x, ensure_ascii=False)

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def turkish_lower(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.replace("İ", "i").replace("I", "ı")
    return s.lower()

def normalize_date_str(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    if re.search(r"\b\d{4}[-/.]00[-/.]00\b", s):
        return ""
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.month == 0 or dt.day == 0:
                return ""
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return ""

def to_list(x):
    if x is None or x == "":
        return []
    if isinstance(x, list):
        return x
    return [x]

def uniq_list(seq):
    out, seen = [], set()
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def normalize_sonuc(val: str) -> str:
    if not isinstance(val, str) or not val.strip():
        return "diger"
    v = val.lower()
    for canon, keys in SONUC_CANONICAL.items():
        if canon == "diger":
            continue
        for k in keys:
            if k in v:
                return canon
    if "red" in v or "redd" in v:
        return "ret"
    if "kabul" in v:
        return "kabul"
    if "boz" in v:
        return "bozma"
    return "diger"

def normalize_basvuru_yolu(raw) -> list:
    items = to_list(raw)
    out = []
    for v in items:
        vv = turkish_lower(ensure_str(v)).strip()
        if not vv:
            continue
        matched = False
        for canon, keys in BASVURU_YOLU_ALLOWED.items():
            for k in keys:
                if k in vv:
                    out.append(canon)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            out.append(vv)
    if not out:
        out = ["yok"]
    return uniq_list(out)
# ==============================
# Main
# ==============================
def main():
    if not INPUT_PATH.exists():
        print(f"Girdi dosyası bulunamadı: {INPUT_PATH}")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    stats = {
        "total": 0,
        "fixed_types": 0,
        "empty_to_defaults": 0,
        "date_normalized": 0,
        "date_failed": 0,
        "records_with_missing_required": 0
    }
    flags_counter = {}

    required_fields = [
        "dava_turu", "taraf_iliskisi", "sonuc", "karar",
        "gerekce", "basvuru_yolu", "adimlar", "hikaye"
    ]

    with INPUT_PATH.open("r", encoding="utf-8") as f_in, \
         OUTPUT_PATH.open("w", encoding="utf-8") as f_out:

        for line in f_in:
            line = line.strip()
            if not line:
                continue
            stats["total"] += 1

            try:
                item = json.loads(line)
            except Exception:
                out = {
                    "id": None,
                    "record": {},
                    "quality_flags": ["processing_error", "json_decode_error"]
                }
                f_out.write(json.dumps(out, ensure_ascii=False) + "\n")
                flags_counter["processing_error"] = flags_counter.get("processing_error", 0) + 1
                flags_counter["json_decode_error"] = flags_counter.get("json_decode_error", 0) + 1
                continue

            _id = item.get("Id") or item.get("id")
            content = item.get("output") or {}
            quality_flags = []

            # -------------- dava_turu --------------
            raw_case_type = ensure_str(content.get("dava_turu"))
            if isinstance(raw_case_type, str):
                cleaned_case_type = normalize_whitespace(
                    turkish_lower(raw_case_type.replace("_", " "))
                )
            else:
                cleaned_case_type = ""
            content["dava_turu"] = cleaned_case_type

            # -------------- taraf_iliskisi --------------
            taraf_iliskisi = normalize_whitespace(ensure_str(content.get("taraf_iliskisi")))
            if not taraf_iliskisi:
                stats["empty_to_defaults"] += 1
            content["taraf_iliskisi"] = taraf_iliskisi

            # -------------- sonuc --------------
            content["sonuc"] = normalize_sonuc(content.get("sonuc"))

            # -------------- karar --------------
            content["karar"] = normalize_whitespace(ensure_str(content.get("karar")))

            # -------------- gerekce (list<string>) --------------
            gerekce = content.get("gerekce")
            if not isinstance(gerekce, list):
                gerekce = [] if gerekce in (None, "") else [ensure_str(gerekce)]
                stats["fixed_types"] += 1
            gerekce = [
                normalize_whitespace(ensure_str(x))
                for x in gerekce
                if ensure_str(x).strip()
            ]
            content["gerekce"] = gerekce

            # -------------- hikaye (list<string>) --------------
            hikaye = content.get("hikaye")
            if not isinstance(hikaye, list):
                hikaye = [] if hikaye in (None, "") else [ensure_str(hikaye)]
                stats["fixed_types"] += 1
            hikaye = [
                normalize_whitespace(ensure_str(x))
                for x in hikaye
                if ensure_str(x).strip()
            ]
            content["hikaye"] = hikaye

            # -------------- deliller / talepler / gecici_tedbirler --------------
            for k in ["deliller", "talepler", "gecici_tedbirler"]:
                v = content.get(k)
                if not isinstance(v, list):
                    v = [] if v in (None, "") else [ensure_str(v)]
                    stats["fixed_types"] += 1
                v = [
                    normalize_whitespace(ensure_str(x))
                    for x in v
                    if ensure_str(x).strip()
                ]
                content[k] = v

            # -------------- basvuru_yolu --------------
            content["basvuru_yolu"] = normalize_basvuru_yolu(content.get("basvuru_yolu"))

            # -------------- metin_esas_no / metin_karar_no --------------
            for k in ["metin_esas_no", "metin_karar_no"]:
                v = content.get(k)
                if not isinstance(v, list):
                    v = [] if v in (None, "") else [ensure_str(v)]
                    stats["fixed_types"] += 1
                v = [
                    normalize_whitespace(ensure_str(x))
                    for x in v
                    if ensure_str(x).strip()
                ]
                v = uniq_list(v)
                content[k] = v

            # -------------- kanun_atiflari --------------
            ka = content.get("kanun_atiflari")
            if not isinstance(ka, list):
                ka = [] if ka in (None, "") else [ka]
                stats["fixed_types"] += 1
            fixed_ka = []
            for obj in ka:
                if not isinstance(obj, dict):
                    obj = {
                        "kanun": "",
                        "madde": "",
                        "fikra": "",
                        "span": ensure_str(obj).strip()
                    }
                    stats["fixed_types"] += 1
                obj["kanun"] = normalize_whitespace(ensure_str(obj.get("kanun")))
                obj["madde"] = normalize_whitespace(ensure_str(obj.get("madde")))
                obj["fikra"] = normalize_whitespace(ensure_str(obj.get("fikra")))
                obj["span"]  = normalize_whitespace(ensure_str(obj.get("span")))
                if obj["kanun"] and not obj["span"]:
                    quality_flags.append("law_without_span")
                fixed_ka.append(obj)
            content["kanun_atiflari"] = fixed_ka

            # -------------- onemli_tarihler --------------
            ot = content.get("onemli_tarihler")
            if not isinstance(ot, list):
                ot = [] if ot in (None, "") else [ot]
                stats["fixed_types"] += 1
            fixed_ot = []
            for obj in ot:
                if not isinstance(obj, dict):
                    obj = {
                        "tip": "",
                        "tarih": "",
                        "span": ensure_str(obj).strip()
                    }
                    stats["fixed_types"] += 1
                obj["tip"] = normalize_whitespace(ensure_str(obj.get("tip")))
                raw_dt = ensure_str(obj.get("tarih")).strip()
                if raw_dt:
                    norm = normalize_date_str(raw_dt)
                    if norm:
                        obj["tarih"] = norm
                        stats["date_normalized"] += 1
                    else:
                        obj["tarih"] = ""
                        stats["date_failed"] += 1
                else:
                    obj["tarih"] = ""
                obj["span"] = normalize_whitespace(ensure_str(obj.get("span")))
                fixed_ot.append(obj)
            content["onemli_tarihler"] = fixed_ot
            # -------------- adimlar --------------
            steps = content.get("adimlar")
            if not isinstance(steps, list):
                steps = [] if steps in (None, "") else [steps]
                stats["fixed_types"] += 1
            fixed_steps = []
            for s in steps:
                if not isinstance(s, dict):
                    s = {
                        "ad": "",
                        "ozet": ensure_str(s).strip(),
                        "tarih": "",
                        "karar_mercii": "",
                        "spans": []
                    }
                    stats["fixed_types"] += 1
                s["ad"] = normalize_whitespace(ensure_str(s.get("ad")))
                s["ozet"] = normalize_whitespace(ensure_str(s.get("ozet")))
                raw_step_dt = s.get("tarih")
                s["tarih"] = ensure_str(raw_step_dt).strip() if raw_step_dt not in (None,) else ""
                s["karar_mercii"] = normalize_whitespace(ensure_str(s.get("karar_mercii")))
                sp = s.get("spans")
                if not isinstance(sp, list):
                    sp = [] if sp in (None, "") else [ensure_str(sp)]
                    stats["fixed_types"] += 1
                sp = [
                    normalize_whitespace(ensure_str(x))
                    for x in sp
                    if ensure_str(x).strip()
                ]
                s["spans"] = sp
                fixed_steps.append(s)
            content["adimlar"] = fixed_steps

            # kalite bayrakları
            if any(isinstance(a, dict) and not a.get("spans") for a in content.get("adimlar", [])):
                quality_flags.append("steps_dropped")
            if len(content.get("adimlar", [])) < 3:
                quality_flags.append("few_steps")

            # zorunlu alan kontrolü
            missing_any = False
            for rf in required_fields:
                if rf not in content or content.get(rf) in (None, "", [], {}):
                    quality_flags.append(f"missing_{rf}")
                    missing_any = True
            if missing_any:
                stats["records_with_missing_required"] += 1

            for fl in set(quality_flags):
                flags_counter[fl] = flags_counter.get(fl, 0) + 1

            # 🔥 ESKİ: {"id","record": {...}, "quality_flags": [...]}
            # ✅ YENİ: Flatten edilmiş satır + id alanlarını ekleyip direkt yaz
            flat_output = {
                "doc_id": ensure_str(_id),
                **content,
                "quality_flags": sorted(list(set(quality_flags)))
            }
            f_out.write(json.dumps(flat_output, ensure_ascii=False) + "\n")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total_records": stats["total"],
        "fixed_types": stats["fixed_types"],
        "empty_to_defaults": stats["empty_to_defaults"],
        "date_normalized": stats["date_normalized"],
        "date_failed": stats["date_failed"],
        "records_with_missing_required": stats["records_with_missing_required"],
        "quality_flags_distribution": dict(sorted(flags_counter.items(), key=lambda x: (-x[1], x[0])))
    }
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2))

    print("✅ Tamamlandı:")
    print(f"  • {OUTPUT_PATH}")
    print(f"  • {REPORT_PATH}")


# -------------------------------------------------------------------------
# SAMPLE OLUŞTURMA (Flatten kayıtlar üzerinden)
# -------------------------------------------------------------------------
def create_sample_by_dava_turu():
    if not OUTPUT_PATH.exists():
        print(f"❌ Örnek çıkarımı için gereken dosya yok: {OUTPUT_PATH}")
        return

    samples = {}
    def is_valid_string(x):
        if x is None:
            return False
        if not isinstance(x, str):
            return False
        if not x.strip():
            return False
        return True

    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                flat_rec = json.loads(line)
            except:
                continue

            dava_turu = flat_rec.get("dava_turu")
            if not is_valid_string(dava_turu):
                continue

            if dava_turu not in samples:
                samples[dava_turu] = []
            if len(samples[dava_turu]) < 5:
                samples[dava_turu].append(flat_rec)

    with SAMPLE_OUTPUT_PATH.open("w", encoding="utf-8") as f_out:
        for dt, rows in samples.items():
            for r in rows:
                f_out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"✅ Dava türü başına max 5 örnek oluşturuldu:\n  • {SAMPLE_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
    create_sample_by_dava_turu()
