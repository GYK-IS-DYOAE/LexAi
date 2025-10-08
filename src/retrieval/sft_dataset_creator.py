import json
from datasets import load_dataset

# 1️⃣ Hugging Face veri setini yükle
hf_dataset = load_dataset("ipproo/Turkish-law", split="train")  # train split

# 2️⃣ Senin kendi datasetini JSONL olarak yükle
own_dataset_file = "C:/Users/Aslı/PycharmProjects/LexAi-main/data/interim/balanced_total30k.jsonl"
own_data = []
with open(own_dataset_file, "r", encoding="utf-8") as f:
    for line in f:
        own_data.append(json.loads(line))

# 3️⃣ Hugging Face datasetini instruction/input/output formatına dönüştür
hf_formatted = []
for entry in hf_dataset:
    # Örnek olarak Hugging Face datasetinde 'text' ve 'label' alanları varsa:
    text = entry.get("text") or entry.get("case_text") or ""
    label = entry.get("label") or "bilgi yok"

    hf_formatted.append({
        "instruction": "Bu dava metni için özet ve adımları çıkar.",
        "input": text,
        "output": label  # label yoksa boş bırakabiliriz veya basit özet üretebiliriz
    })

# 4️⃣ Kendi datasetini instruction/input/output formatına dönüştür
own_formatted = []
for case in own_data:
    # Örnek: her davanın adımları -> output
    adimlar_ozet = "\n".join([adim["ozet"] for adim in case.get("adimlar", [])])
    input_text = "\n".join(case.get("hikaye", []))  # hikaye -> input
    own_formatted.append({
        "instruction": f"{case.get('dava_turu')} davasında genel eğilimleri, izlenen adımları ve istisnaları açıkla.",
        "input": input_text,
        "output": adimlar_ozet
    })

# 5️⃣ İki dataset'i birleştir
combined_data = own_formatted + hf_formatted

# 6️⃣ JSONL olarak kaydet
with open("sft_dataset.jsonl", "w", encoding="utf-8") as f:
    for item in combined_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Toplam {len(combined_data)} kayıt işlendi ve sft_dataset.jsonl dosyasına kaydedildi.")
print(f"Kendi datasetinden: {len(own_formatted)} kayıt")
print(f"Hugging Face datasetinden: {len(hf_formatted)} kayıt")
