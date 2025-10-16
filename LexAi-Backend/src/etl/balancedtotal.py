import json, random
from pathlib import Path
from collections import defaultdict


KARARLAR_FILE = "data/interim/kararlar_segment.jsonl"
INPUT_FILE    = "data/interim/04_link_law.jsonl"
ENRICHED_OUT  = "data/interim/04_link_law_enriched.jsonl"   
OUT_FILE      = "data/interim/balanced_total30k.jsonl"
TOTAL_TARGET  = 30000
random.seed(42)

def iter_jsonl(path: str):
    """JSONL satırlarını BOM güvenli şekilde okur."""
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def write_jsonl(path: str, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _norm(s):
    if s is None: return ""
    s = str(s).upper()
    return "".join(ch for ch in s if ch.isalnum())

def make_key(d: dict):
    """
    Eşleştirme anahtarı:
      1) doc_id / Id (stringleştir)
      2) (Esas No, Karar No)  (+ opsiyonel mahkeme/daire ile sıkılaştırma)
    """
    for k in ("doc_id", "DocId", "docID", "document_id", "Id", "ID"):
        v = d.get(k)
        if v is not None and str(v).strip() != "":
            return f"ID::{str(v).strip()}"

    esas = (d.get("metin_esas_no") or d.get("Esas No") or d.get("EsasNo") or
            d.get("esas_no") or d.get("esas"))
    karar = (d.get("metin_karar_no") or d.get("Karar No") or d.get("KararNo") or
             d.get("karar_no") or d.get("karar"))
    if esas or karar:
        court = d.get("mahkeme") or d.get("Mahkeme") or d.get("daire") or d.get("Daire")
        if court:
            return f"EKC::{_norm(court)}::{_norm(esas)}::{_norm(karar)}"
        return f"EK::{_norm(esas)}::{_norm(karar)}"

    return None

def get_karar_text(d: dict):
    """'Karar Metni' alanını esnek anahtarlarla bulur."""
    for k in ("Karar Metni", "karar_metni", "karar", "Karar", "text", "full_text"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def main():
    # --- 1) Karar metni indexini kur ---
    p_kaynak = Path(KARARLAR_FILE)
    if not p_kaynak.exists():
        raise FileNotFoundError(f"KARARLAR_FILE bulunamadı: {KARARLAR_FILE}")

    karar_index = {}
    src_total = 0
    usable = 0
    collisions = 0

    for d in iter_jsonl(KARARLAR_FILE):
        src_total += 1
        key = make_key(d)
        txt = get_karar_text(d)
        if not key or not txt:
            continue
        if key in karar_index:
            collisions += 1
            if len(txt) > len(karar_index[key]):
                karar_index[key] = txt
        else:
            karar_index[key] = txt
            usable += 1

    print(f"[INDEX] kaynak={src_total}, kullanılabilir={usable}, çakışma={collisions}")


    p_input = Path(INPUT_FILE)
    if not p_input.exists():
        raise FileNotFoundError(f"INPUT_FILE bulunamadı: {INPUT_FILE}")

    enriched = []
    matched = 0
    no_key = 0
    no_hit = 0

    for rec in iter_jsonl(INPUT_FILE):
        key = make_key(rec)
        if not key:
            no_key += 1
            enriched.append(rec)
            continue

        karar_txt = karar_index.get(key)
        if karar_txt:
            
            if not rec.get("karar"):
                rec["karar"] = karar_txt

            rec["karar_metni"] = karar_txt
            matched += 1
        else:
            no_hit += 1

        enriched.append(rec)

    print(f"[ENRICH] matched={matched}, no_key={no_key}, no_hit={no_hit}, total={len(enriched)}")


    write_jsonl(ENRICHED_OUT, enriched)
    print(f"[WRITE] Enriched output -> {ENRICHED_OUT}")


    groups = defaultdict(list)
    for rec in enriched:
        groups[rec.get("dava_turu", "UNKNOWN")].append(rec)

    num_classes = len(groups)
    per_class_target = TOTAL_TARGET // num_classes if num_classes > 0 else TOTAL_TARGET
    print(f"[BALANCE] sınıf={num_classes} | kişi başı hedef={per_class_target}")

    balanced = []
    extras = []
    shortfall = 0

    for dt, records in groups.items():
        n = len(records)
        if n >= per_class_target:
            sample = random.sample(records, per_class_target)
            sample_ids = set(id(x) for x in sample)
            extras.extend([r for r in records if id(r) not in sample_ids])
        else:
            sample = records
            shortfall += (per_class_target - n)
        balanced.extend(sample)
        print(f"[BALANCE] {dt}: {n} -> {len(sample)} alındı")

    if len(balanced) < TOTAL_TARGET and extras:
        need = TOTAL_TARGET - len(balanced)
        balanced.extend(random.sample(extras, min(need, len(extras))))

    random.shuffle(balanced)
    write_jsonl(OUT_FILE, balanced)
    print(f"[DONE] Balanced -> {OUT_FILE} | Toplam={len(balanced)}")

if __name__ == "__main__":
    main()
