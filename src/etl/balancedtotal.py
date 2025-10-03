import json
import random
from collections import defaultdict

INPUT = "data/interim/04_link_law.jsonl"
OUT_FILE = "data/interim/balanced_total30k.jsonl"

TOTAL_TARGET = 30000
random.seed(42)

# 1. dava_turu bazlı grupla (tüm kayıtlar JSON obje olarak tutulacak)
groups = defaultdict(list)
with open(INPUT, "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        dt = rec.get("dava_turu", "UNKNOWN")
        groups[dt].append(rec)

num_classes = len(groups)
per_class_target = TOTAL_TARGET // num_classes
print(f"Unique dava_turu sayısı: {num_classes} | Kişi başı hedef: {per_class_target}")

balanced_records = []
shortfall = 0
extras = []

# 2. her dava_turu’dan eşit miktarda örnek seç
for dt, records in groups.items():
    n = len(records)
    if n >= per_class_target:
        sampled = random.sample(records, per_class_target)
        extras.extend([r for r in records if r not in sampled])  # fazlalıkları kenara koy
    else:
        sampled = records  # azsa hepsini al
        shortfall += (per_class_target - n)
    balanced_records.extend(sampled)
    print(f"{dt}: {n} -> {len(sampled)} selected")

# 3. Eksikleri extras’tan doldur
if len(balanced_records) < TOTAL_TARGET and extras:
    need_more = TOTAL_TARGET - len(balanced_records)
    balanced_records.extend(random.sample(extras, min(need_more, len(extras))))

# 4. Shuffle ve JSONL olarak kaydet
random.shuffle(balanced_records)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    for rec in balanced_records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f" Balanced dataset saved to {OUT_FILE} | Toplam kayıt: {len(balanced_records)}")
