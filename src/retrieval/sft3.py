import json
from collections import defaultdict

input_path = "data/interim/balanced_total30k.jsonl"
output_path = "data/interim/sft_natural_all.jsonl"

# Her dava türü için geçici hafıza
memory = defaultdict(lambda: {"adimlar": [], "sonuclar": [], "kanunlar": []})

def merge_examples(dava_turu, record):
    merged = memory[dava_turu]
    # Adımlar
    merged["adimlar"].extend([a["ozet"] for a in record.get("adimlar", [])])
    merged["adimlar"] = list(dict.fromkeys(merged["adimlar"]))
    # Sonuçlar
    sonuc = record.get("sonuc", "")
    if sonuc and sonuc not in merged["sonuclar"]:
        merged["sonuclar"].append(sonuc)
    # Kanunlar
    for k in record.get("kanun_atiflari", []):
        kanun_str = f'{k["kanun"]} m.{k["madde"]}'
        if kanun_str not in merged["kanunlar"]:
            merged["kanunlar"].append(kanun_str)
    return merged

sft_data = []

with open(input_path, "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        dava_turu = record.get("dava_turu", "bilinmeyen")
        merged = merge_examples(dava_turu, record)

        adimlar_text = " ".join(merged["adimlar"])
        sonuclar_text = ", ".join(merged["sonuclar"]) if merged["sonuclar"] else "genellikle reddedilir"
        kanunlar_text = ", ".join(merged["kanunlar"]) if merged["kanunlar"] else "ilgili kanunlar davaya göre değişir"

        output_text = (
            f"{dava_turu} davalarında genel olarak, tarafların adımları şu şekilde ilerler: {adimlar_text}. "
            f"Genellikle sonuçlar {sonuclar_text} şeklindedir. "
            f"Sıkça atıf yapılan kanunlar: {kanunlar_text}. "
            f"İstisnai durumlar, fer'i müdahil veya temsil yetkisi olmayan tarafların başvurularıdır; "
            f"bu durumlarda süreç farklılaşabilir ve reddedilme olasılığı artar."
        )

        sft_record = {
            "instruction": f"{dava_turu} davalarında genel eğilimleri, izlenen adımları ve istisnaları açıkla.",
            "input": record.get("hikaye", []),
            "output": output_text
        }

        sft_data.append(sft_record)

with open(output_path, "w", encoding="utf-8") as f:
    for rec in sft_data:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Tüm dava türleri için doğal dil SFT verisi oluşturuldu: {output_path}")
