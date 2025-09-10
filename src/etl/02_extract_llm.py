"""
02_extract_llm.py
-----------------
Amaç:
- data/interim/kararlar_segment.csv dosyasını okur.
- Her satırın "Karar Metni" kolonunu LLM'e (Ollama üzerinden Qwen2.5) verir.
- LLM'in çıkardığı alanları Pydantic şemasıyla doğrular.
- ÇIKTI: data/interim/02_extract_llm.jsonl
  * meta (CSV'den seçilmiş temel alanlar)
  * record (LLM çıkarımları)
  * source_csv (CSV satırının TÜM orijinal sütunları)  <<<<<< ÖNEMLİ
"""

import json, time, sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
import requests
import csv

# ------------------ Ayarlar ------------------
SYSTEM_PROMPT_FILE = Path("src/llm/prompts/extract_system.md")
system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b-instruct"  # yoksa: `ollama pull qwen2.5:7b-instruct`

# ------------------ Şema ---------------------
class KanunAtifi(BaseModel):
    """Kanun atıfları için şema."""
    kanun: Optional[str] = None
    madde: Optional[str] = None
    fikra: Optional[str] = None
    span: Optional[str] = None

class Adim(BaseModel):
    """Karar sürecindeki adımlar için şema (kronolojik)."""
    ad: str
    ozet: Optional[str] = None
    spans: List[str] = Field(default_factory=list)

class RecordOut(BaseModel):
    """LLM çıkarım kaydı şeması."""
    dava_turu: Optional[str] = None
    alt_dava_turleri: List[str] = Field(default_factory=list)
    taraf_iliskisi: Optional[str] = None
    sonuc: Optional[str] = None
    kanun_atiflari: List[KanunAtifi] = Field(default_factory=list)
    deliller: List[str] = Field(default_factory=list)
    talepler: List[str] = Field(default_factory=list)
    gecici_tedbirler: List[str] = Field(default_factory=list)
    basvuru_yolu: Optional[str] = None
    onemli_tarihler: List[dict] = Field(default_factory=list)
    miktarlar: List[dict] = Field(default_factory=list)
    adimlar: List[Adim] = Field(default_factory=list)

# --------------- LLM çağrısı (Ollama) ---------------
def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Ollama API üzerinden modele istek atar, JSON cevabı döndürür.
    JSON dışı içerik gelirse içteki { ... } bloğunu ayıklamayı dener.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        "options": {"temperature": 0, "num_ctx": 8192},
        "format": "json",   # JSON-only mod (modeller destekliyorsa)
        "stream": False,
    }
    # ilk kullanımda modelin derlenmesi uzun sürebilir; timeout yüksek
    r = requests.post(OLLAMA_URL, json=payload, timeout=(10, 600))
    r.raise_for_status()
    content = r.json()["message"]["content"]

    # debug: ilk birkaç cevabı kaydet
    dbg_dir = Path("data/interim/debug"); dbg_dir.mkdir(parents=True, exist_ok=True)
    idx = len(list(dbg_dir.glob("raw_*.txt"))) + 1
    if idx <= 5:
        (dbg_dir / f"raw_{idx}.txt").write_text(content, encoding="utf-8")

    # doğrudan JSON mu?
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        pass

    # içerideki ilk JSON bloğunu yakala
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1 and end > start:
        sliced = content[start:end+1]
        try:
            json.loads(sliced)
            return sliced
        except json.JSONDecodeError:
            pass

    # başaramazsa boş dict
    return "{}"

def build_user_prompt(text: str) -> str:
    """
    Kullanıcı promptunu kurar; çok uzun metinleri 3500 karaktere kısaltır.
    """
    text = (text or "").strip()
    if len(text) > 3500:
        text = text[:3500]
    return (
        "Aşağıdaki metinden sistem mesajındaki şema ve kurallara uygun olarak alanları çıkar. "
        "YALNIZ GEÇERLİ JSON döndür.\n\nMETİN:\n" + text
    )

# --------------- Girdi yükleme ---------------
def load_inputs():
    """
    CSV (kararlar_segment.csv) okur; her satır için:
      - text: Karar Metni
      - case_meta: seçilmiş meta (Sira/Daire/Esas No/Karar No/Tarih)
      - source_csv: TÜM CSV sütunları (ham kopya)
    """
    seg_csv = Path("data/interim/kararlar_segment.csv")
    if not seg_csv.exists():
        sys.exit("Girdi bulunamadı: data/interim/kararlar_segment.csv bekleniyor.")

    with seg_csv.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            # bazen dosyaya başlık satırı tekrar düşebiliyor
            if row.get("Sira", "").strip() == "Sira":
                continue

            text = (row.get("Karar Metni") or "").strip()

            meta = {
                "id": row.get("Sira") or None,
                "daire": row.get("Daire") or None,
                "esas_no": row.get("Esas No") or None,
                "karar_no": row.get("Karar No") or None,
                "tarih": row.get("Tarih") or None,
            }
            raw_csv = dict(row)  # <<<<<< TÜM sütunları ham olarak taşı
            yield {"case_meta": meta, "text": text, "source_csv": raw_csv}

# --------------- Ana koşu ---------------
def run(limit: Optional[int] = None):
    """
    Satırları LLM'e gönderir, Pydantic ile doğrular ve JSONL olarak yazar.
    Başarısız/boş metinlerde işaret bayrağıyla birlikte boş şema yazar.
    """
    out_path = Path("data/interim/02_extract_llm.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with out_path.open("w", encoding="utf-8") as out:
        for item in load_inputs():
            if limit and n >= limit:
                break

            # çok kısa/boş metin -> işaretle
            if not item["text"] or len(item["text"].strip()) < 50:
                payload = {
                    "meta": item["case_meta"],
                    "record": RecordOut().model_dump(),
                    "source_csv": item.get("source_csv", {}),
                    "quality_flags": ["empty_text"]
                }
                out.write(json.dumps(payload, ensure_ascii=False) + "\n")
                n += 1
                continue

            user = build_user_prompt(item["text"])

            success = False
            for _ in range(3):
                raw = call_llm(system_prompt, user)
                try:
                    data = json.loads(raw)
                    parsed = RecordOut.model_validate(data).model_dump()
                    payload = {
                        "meta": item["case_meta"],
                        "record": parsed,
                        "source_csv": item.get("source_csv", {})
                    }
                    out.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    success = True
                    break
                except (json.JSONDecodeError, ValidationError):
                    time.sleep(0.8)

            if not success:
                payload = {
                    "meta": item["case_meta"],
                    "record": RecordOut().model_dump(),
                    "source_csv": item.get("source_csv", {}),
                    "quality_flags": ["llm_parse_failed"]
                }
                out.write(json.dumps(payload, ensure_ascii=False) + "\n")

            n += 1

    print(f"✅ Extract tamam: {n} kayıt -> {out_path}")

if __name__ == "__main__":
    # Ör: python src/etl/02_extract_llm.py 5
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(limit)
