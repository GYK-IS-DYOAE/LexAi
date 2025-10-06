"""
prompt_builder.py
-----------------
Retriever'dan gelen sonuçlar + kullanıcı sorusunu alır, LLM'e verilecek
**sistem** ve **kullanıcı** mesajlarını üretir.
- Sadece Türkçe cevap
- **Sadece JSON** çıktısı (şemaya uyumlu)
- Kaynaklar (doc_id listesi) zorunlu
"""

from typing import List, Dict
from src.config import MAX_PASSAGE_CHARS, MAX_TOTAL_PASSAGES

SYSTEM_PROMPT = """Sen bir hukuk asistanısın. Sadece TÜRKÇE konuş.
Aşağıdaki JSON ŞEMASINA UYGUN, SADECE JSON üret. Önsöz/son söz ekleme.

Şema alanları (zorunlu):
- dava_turu (string)
- taraf_iliskisi (string)
- sonuc (string; onama/bozma/ret/kabul/diger)
- karar (string; özlü sonuç)
- gerekce (string; kısa ama açık)
- hikaye (string; 2-5 cümlede özet)
- kanun_atiflari (list of {kanun, madde, fikra, span})
- kaynaklar (list of doc_id; string)

Kurallar:
- Cevabını SADECE verilen pasajlardan çıkar.
- Kaynak olarak kullandığın her pasajın doc_id'sini 'kaynaklar' listesine koy.
- Emin olamadığın yerleri uydurma; varsa "diger" de.
- ÇIKTIYI SADECE JSON olarak ver.
"""

def build_user_prompt(query: str, passages: List[Dict]) -> str:
    """
    passages: [{'doc_id': '123', 'text': '...kırpılmış pasaj...'}, ...]
    """
    # LLM'e giden pasajları tek bir "context" bloğu gibi hazırla
    lines = [f"SORU: {query}", "", "PASAJLAR:"]
    for i, p in enumerate(passages[:MAX_TOTAL_PASSAGES], 1):
        txt = (p.get("text") or "")[:MAX_PASSAGE_CHARS].replace("\n", " ")
        lines.append(f"[{i}] doc_id={p.get('doc_id')}  {txt}")
    lines.append("")
    lines.append("Lütfen yukarıdaki şemaya uygun, SADECE JSON ver.")
    return "\n".join(lines)
