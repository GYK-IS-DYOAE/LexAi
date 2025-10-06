import json
#1086 numaralı kanunun maddelerini tek satır JSONL formatına dönüştürür
INPUT_PATH = "data/raw/1086_parse.json"        # Tam kanun JSON'un
OUTPUT_PATH = "data/raw/maddeler.jsonl"    # Tek satır JSONL formatında çıktı

def maddeleri_donustur(veri):
    yeni = {}
    maddeler = veri.get("maddeler", [])

    for madde in maddeler:
        no = madde.get("no")
        metin = madde.get("metin", "").strip()
        baslik = madde.get("baslik")

        if not isinstance(no, int):
            continue
        if no > 454:
            continue

        # Başlık varsa en başa ekle
        if baslik:
            icerik = baslik.strip() + " " + metin
        else:
            icerik = metin

        yeni[str(no)] = icerik.replace("\n", " ").replace("  ", " ")

    return yeni

def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        veri = json.load(f)

    cikti = maddeleri_donustur(veri)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        line = '"maddeler":' + json.dumps(cikti, ensure_ascii=False, separators=(",", ":"))
        f.write(line + "\n")

    print(f"✅ Çıktı üretildi: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
