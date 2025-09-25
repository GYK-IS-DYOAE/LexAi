import json
from pathlib import Path

"""
src/retrieval/prepare_records.py
-------------------
Amaç:
- 03_validated.jsonl dosyasındaki iç içe geçmiş `record` alanlarını düzleştirerek
  OpenSearch/Qdrant için uygun hale getirmek.

Girdi:
- data/interim/03_validated.jsonl

Çıktı:
- data/processed/records.jsonl (her satır: doc_id, dava_turu, taraf_iliskisi, sonuc, karar, gerekce, hikaye…)

Nasıl çalıştırılır:
$ python src/retrieval/prepare_records.py
"""
INPUT_FILE = "data/interim/03_validated.jsonl"
OUTPUT_FILE = "data/processed/records.jsonl"

def main():
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:

        for line in f_in:
            record_all = json.loads(line)
            rec_id = record_all["id"]
            record = record_all["record"]

            flat_record = {
                "doc_id": rec_id,
                "dava_turu": record.get("dava_turu"),
                "taraf_iliskisi": record.get("taraf_iliskisi"),
                "sonuc": record.get("sonuc"),
                "metin_esas_no": record.get("metin_esas_no"),
                "metin_karar_no": record.get("metin_karar_no"),
                "kanun_atiflari": record.get("kanun_atiflari"),
                "onemli_tarihler": record.get("onemli_tarihler"),
                "karar": record.get("karar"),
                "gerekce": record.get("gerekce"),
                "hikaye": record.get("hikaye")
            }

            f_out.write(json.dumps(flat_record, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
