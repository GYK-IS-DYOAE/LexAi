"""
03_validate_normalize.py
------------------------
Amaç:
- 02_extract_llm.jsonl içindeki LLM ham çıktısını doğrulamak ve normalize etmek.
- Aşağıdakileri yapar:
  * 'sonuc' alanını sözlük üzerinden kanonikleştirir,
  * kanun atıflarında kanun kodu (TMK/HMK/HUMK/İİK/TBK/TCK) ve maddeyi normalize eder,
  * meta.tarih ve onemli_tarihler[].tarih alanlarını YYYY-MM-DD biçimine çevirir,
  * 'adimlar' listesinden spans'i boş olan adımları düşer (kronoloji kanıtlı kalsın),
  * basit kalite bayrakları ekler (few_steps, law_without_span, steps_dropped).
- Çıktı: data/interim/03_validated.jsonl (JSON Lines)
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
import yaml

# ------------------ Yapılandırma yükleme ------------------
CFG_PATH = Path("configs/normalizers.yml")

def load_norm_config() -> dict:
    """
    normalizers.yml dosyasını okur ve sözlük olarak döndürür.
    Dosya yok veya bozuksa anlamlı bir hata mesajı ile süreci durdurur.
    """
    if not CFG_PATH.exists():
        sys.exit("HATA: configs/normalizers.yml bulunamadı.")
    try:
        data = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) or {}
        return data
    except Exception as e:
        sys.exit(f"HATA: normalizers.yml okunamadı/bozuk: {e}")

NORM = load_norm_config()
SONUC_MAP = NORM.get("sonuc_map", {})          # ör: {"ret": ["reddi", "red"], ...}
KANUN_MAP = NORM.get("kanun_kod_map", {})      # ör: {"hmk": ["hmk","6100"], "humk": ["humk","1086"], ...}

# ------------------ Yardımcı normalizasyonlar ------------------
def norm_sonuc(x):
    """
    'sonuc' alanını kanonik değere çevirir.
    """
    if not x:
        return None
    lx = x.lower()
    for canon, variants in SONUC_MAP.items():
        if any(v in lx for v in variants):
            return canon
    return "diger"

def norm_kanun(k):
    """
    Kanun adını/kodunu TMK/TBK/HMK/HUMK/İİK/TCK gibi kısaltmalara çevirir.
    """
    if not k:
        return None
    lk = k.lower()
    for canon, variants in KANUN_MAP.items():
        if any(v in lk for v in variants):
            return {
                "medeni_kanun": "TMK",
                "borclar_kanunu": "TBK",
                "hmk": "HMK",
                "humk": "HUMK",
                "iik": "İİK",
                "tck": "TCK",
            }[canon]
    if re.fullmatch(r"[a-zçğıöşü]{2,5}", lk):
        return lk.upper()
    return None

def norm_date(s):
    """
    Tarihi YYYY-MM-DD formatına normalize eder.
    """
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return None

def normalize_onemli_tarihler(lst):
    """
    onemli_tarihler[*].tarih alanlarını normalize eder.
    """
    if not isinstance(lst, list):
        return []
    out = []
    for it in lst:
        if not isinstance(it, dict):
            continue
        d = dict(it)
        if "tarih" in d and d["tarih"]:
            d["tarih"] = norm_date(d["tarih"])
        out.append(d)
    return out

def drop_steps_without_spans(steps):
    """
    'adimlar' listesinden spans'i boş olan adımları düşer.
    """
    if not isinstance(steps, list):
        return ([], 0)
    kept, dropped = [], 0
    for a in steps:
        if isinstance(a, dict) and a.get("spans") and len(a.get("spans", [])) > 0:
            kept.append(a)
        else:
            dropped += 1
    return (kept, dropped)

# ------------------ Kayıt doğrulama ------------------
def validate_record(j):
    """
    Tek bir kaydı normalize eder ve kalite bayraklarını günceller.
    """
    rec = j.get("record", {}) or {}
    meta = j.get("meta", {}) or {}

    # meta.tarih normalize
    if meta.get("tarih"):
        meta["tarih"] = norm_date(meta.get("tarih"))
    j["meta"] = meta

    # sonuc normalize
    rec["sonuc"] = norm_sonuc(rec.get("sonuc"))

    # kanun atıfları normalize
    for a in rec.get("kanun_atiflari", []):
        a["kanun"] = norm_kanun(a.get("kanun"))
        if a.get("madde"):
            only_digits = re.sub(r"\D+", "", str(a["madde"]))
            a["madde"] = only_digits if only_digits else None

    # önemli tarihler normalize
    rec["onemli_tarihler"] = normalize_onemli_tarihler(rec.get("onemli_tarihler"))

    # adımlar: spans boş olanları düş
    adims = rec.get("adimlar", [])
    adims_filtered, dropped = drop_steps_without_spans(adims)
    rec["adimlar"] = adims_filtered

    # kalite bayrakları
    flags = list(j.get("quality_flags", []))
    if len(rec.get("adimlar", [])) < 3:
        flags.append("few_steps")
    if any(a.get("kanun") and not a.get("span") for a in rec.get("kanun_atiflari", [])):
        flags.append("law_without_span")
    if dropped > 0:
        flags.append("steps_dropped_no_span")

    j["record"] = rec
    j["quality_flags"] = flags
    return j

# ------------------ Giriş/Çıkış akışı ------------------
def run():
    """
    02_extract_llm.jsonl -> 03_validated.jsonl
    """
    inp = Path("data/interim/02_extract_llm.jsonl")
    out = Path("data/interim/03_validated.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)

    if not inp.exists():
        sys.exit("HATA: data/interim/02_extract_llm.jsonl yok. Önce 02_extract_llm.py çalıştırın.")

    n = 0
    with inp.open(encoding="utf-8") as f, out.open("w", encoding="utf-8") as g:
        for line in f:
            j = json.loads(line)
            g.write(json.dumps(validate_record(j), ensure_ascii=False) + "\n")
            n += 1
    print(f"✅ Doğrulama/normalize tamam: {n} kayıt -> {out}")

# ------------------ Çalıştırma ------------------
if __name__ == "__main__":
    run()
