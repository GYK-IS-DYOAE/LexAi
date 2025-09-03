import re, json, yaml, argparse
from pathlib import Path
import pandas as pd


def load_config(path: str | Path) -> dict:
    """YAML konfigürasyon dosyasını okur ve sözlük olarak döndürür."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def compile_segment_patterns(cfg: dict) -> dict:
    """YAML’deki desenleri derler; bölüm başlıkları, mahkeme, dava türü ve dosya no şablonlarını döndürür."""
    seg = cfg["segment"]
    return {
        "sections": {
            "baslik": [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("baslik", [])],
            "gerekce": [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("gerekce", [])],
            "hukum":   [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("hukum", [])],
        },
        "court": {
            "header_line": re.compile(seg["court"]["header_line"], re.I | re.M | re.U),
            "inline_hints": [re.compile(p, re.I | re.M | re.U) for p in seg["court"]["inline_hints"]],
        },
        "case_type": {
            "key_labels": [re.compile(p, re.I | re.M) for p in seg["case_type"]["key_labels"]],
            "keywords": [kw.lower() for kw in seg["case_type"]["keywords"]],
        },
        "docket": {
            "generic": re.compile(seg["docket"]["generic"]),
            "left_kw": re.compile(seg["docket"]["left_kw"], re.I),
            "right_kw": re.compile(seg["docket"]["right_kw"], re.I),
            "ctx_window": int(seg["docket"]["ctx_window"]),
        }
    }


def find_sections(text: str, sp: dict) -> dict:
    """Başlık/gerekçe/hüküm aralıklarını döndürür; 'baslik' için ilk görünen blok seçilir."""
    hits = []
    for label, regs in sp.items():
        for rx in regs:
            for m in rx.finditer(text):
                hits.append((m.start(), label))
    hits.sort()

    spans = {k: {"span": [0, 0]} for k in ["baslik", "gerekce", "hukum"]}
    if not hits:
        return spans

    baslik_starts = [pos for pos, lab in hits if lab == "baslik"]
    if baslik_starts:
        hs = min(baslik_starts)
        boundaries = [pos for pos, lab in hits if pos > hs and lab != "baslik"]
        he = boundaries[0] if boundaries else len(text)
        spans["baslik"] = {"span": [hs, he]}

    for i, (pos, label) in enumerate(hits):
        if label == "baslik":
            continue
        start = pos
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        cur = spans[label]["span"]
        if cur == [0, 0] or (end - start) > (cur[1] - cur[0]):
            spans[label] = {"span": [start, end]}
    return spans


def extract_header_court(text: str, header_span: list[int], cp: dict) -> dict:
    """Başlıktaki 'MAHKEMESİ:' satırından mahkeme adını yakalar; isimli grup varsa (?P<court>) onu kullanır."""
    hs, he = header_span
    haystack = text[hs:he] if he > hs else text
    m = cp["header_line"].search(haystack)
    if not m:
        return {"MahkemeAdi": None, "span": [0, 0]}
    grp = "court" if "court" in m.re.groupindex else 1
    value = m.group(grp).strip()
    start = (hs + m.start(grp)) if he > hs else m.start(grp)
    end   = (hs + m.end(grp))   if he > hs else m.end(grp)
    return {"MahkemeAdi": value, "span": [start, end]}


def _normalize_court_key(s: str) -> str:
    """Mahkeme adı karşılaştırmaları için sadeleştirilmiş anahtar üretir (Türkçe harfler korunur)."""
    s = s.strip().lower()
    s = s.replace("mah.", "mahkemesi").replace("daire.", "dairesi")
    s = s.replace("başkanlığı", "")
    s = re.sub(r"[^\wçğıöşü\s]", " ", s, flags=re.U)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _overlaps(a: list[int], b: list[int]) -> bool:
    """İki [start,end] aralığının çakışıp çakışmadığını döndürür."""
    return not (a[1] <= b[0] or b[1] <= a[0])


_COURT_TAIL_RX = re.compile(r"(mahkemesi|mah\.|dairesi|daire\.)\b", re.I | re.U)


def _trim_to_court_phrase(s: str, max_left_tokens: int = 5) -> str:
    """Uzun eşleşmeyi yalnızca ‘… Mahkemesi / … Dairesi’ ifadesine indirger; numara/tarih/bağlaç gürültüsünü temizler."""
    m = _COURT_TAIL_RX.search(s)
    if not m:
        return s.strip()
    end = m.end()
    left = s[:m.start()]
    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9\.]+", left, flags=re.U)
    stop = {"tarihli", "kararı", "karar", "sayılı", "ile", "ve", "olarak", "göre", "dava", "davaya", "esas", "no", "nolu"}
    tokens = [t for t in tokens if t.lower() not in stop and not re.fullmatch(r"\d+|\d+\.\d+|\d{4}/\d+", t)]
    keep = tokens[-max_left_tokens:]
    tail = s[m.start():end]
    tail = re.sub(r"\bmah\.\b", "Mahkemesi", tail, flags=re.I)
    tail = re.sub(r"\bdaire\.\b", "Dairesi",   tail, flags=re.I)
    phrase = " ".join(keep + [tail])
    phrase = re.sub(r"\s+", " ", phrase).strip()

    def _tc(w: str) -> str:
        return w if w.isupper() and len(w) <= 4 else w.capitalize()

    return " ".join(_tc(w) for w in phrase.split())


def extract_inline_courts(text: str, cp: dict, exclude_span: list[int] | None, header_value: str | None) -> list:
    """Başlık aralığını hariç tutarak metin içinde geçen mahkeme adlarını liste olarak döndürür (dict yerine string)."""
    if exclude_span and exclude_span[1] > exclude_span[0]:
        ex = [max(0, exclude_span[0]-80), min(len(text), exclude_span[1]+80)]
    else:
        ex = None
    header_key = _normalize_court_key(header_value) if header_value else None
    seen, out = set(), []
    for rx in cp["inline_hints"]:
        for m in rx.finditer(text):
            span = [m.start(), m.end()]
            if ex and _overlaps(span, ex):
                continue
            raw = m.group("court") if "court" in m.re.groupindex else m.group(0)
            val = _trim_to_court_phrase(raw)
            key = _normalize_court_key(val)
            if header_key and key == header_key:
                continue
            if key in seen:
                continue
            if len(val.split()) > 8:
                continue
            seen.add(key)
            out.append(val)   # artık sadece string ekliyoruz
    return out


def extract_case_type(text: str, ctp: dict) -> dict:
    """Etiketli dava türünü döndürür; yoksa anahtar kelimelerle tahmin listesi üretir."""
    for rx in ctp["key_labels"]:
        m = rx.search(text)
        if m:
            return {"DavaTuru": m.group(1).strip(), "span": [m.start(1), m.end(1)], "anahtarlar": []}
    lowered = text.lower()
    hits = [kw for kw in ctp["keywords"] if kw in lowered]
    return {"DavaTuru": None, "span": [0, 0], "anahtarlar": hits}


def _classify_docket(text: str, start: int, end: int, dp: dict) -> str:
    """20xx/xxxx ifadesini bağlama göre ‘esas’, ‘karar’ veya ‘diger’ olarak sınıflandırır."""
    L = max(0, start - dp["ctx_window"])
    R = min(len(text), end + dp["ctx_window"])
    left = text[L:start]
    right = text[end:R]
    if dp["left_kw"].search(left) or dp["left_kw"].search(right):
        return "esas"
    if dp["right_kw"].search(left) or dp["right_kw"].search(right):
        return "karar"
    return "diger"


def extract_dockets(text: str, dp: dict) -> dict:
    """Metindeki 20xx/xxxx referanslarını bularak {'yil','sira'} listeleri halinde döndürür (ham/span içermez)."""
    out = {"MetinEsasListesi": [], "MetinKararListesi": [], "MetinDigerDosyaNoListesi": []}
    for m in dp["generic"].finditer(text):
        year, seq = int(m.group(1)), int(m.group(2))
        cls = _classify_docket(text, m.start(), m.end(), dp)
        item = {"yil": year, "sira": seq}
        if cls == "esas":
            out["MetinEsasListesi"].append(item)
        elif cls == "karar":
            out["MetinKararListesi"].append(item)
        else:
            out["MetinDigerDosyaNoListesi"].append(item)
    return out


def run_segment(input_csv: str, output_csv: str, cfg_path: str, encoding: str = "utf-8-sig", limit: int | None = None) -> None:
    """CSV’yi okur, alan çıkarımı yapar ve sonucu yeni CSV’ye yazar."""
    cfg = load_config(cfg_path)
    pats = compile_segment_patterns(cfg)
    df = pd.read_csv(input_csv, encoding=encoding)
    if limit and limit > 0:
        df = df.head(limit)
    col = "Karar Metni"

    mahkeme_adi, metin_ici_mahkemeler = [], []
    dava_turu, dava_kw = [], []
    metin_esas, metin_karar, metin_diger = [], [], []

    for txt in df[col].astype(str):
        sections = find_sections(txt, pats["sections"])
        header_span = sections.get("baslik", {}).get("span", [0, 0])

        court_hdr = extract_header_court(txt, header_span, pats["court"])
        exclude_span = court_hdr.get("span", [0, 0])
        courts_inline = extract_inline_courts(txt, pats["court"], exclude_span, court_hdr["MahkemeAdi"])

        ctype = extract_case_type(txt, pats["case_type"])
        docks = extract_dockets(txt, pats["docket"])

        mahkeme_adi.append(court_hdr["MahkemeAdi"])
        metin_ici_mahkemeler.append(courts_inline)
        dava_turu.append(ctype["DavaTuru"])
        dava_kw.append(ctype["anahtarlar"])
        metin_esas.append(docks["MetinEsasListesi"])
        metin_karar.append(docks["MetinKararListesi"])
        metin_diger.append(docks["MetinDigerDosyaNoListesi"])

    df["MahkemeAdi"] = mahkeme_adi
    df["MetinIciMahkemeler"] = metin_ici_mahkemeler
    df["DavaTuru"] = dava_turu
    df["DavaTuruAnahtarlar"] = dava_kw
    df["MetinEsasListesi"] = metin_esas
    df["MetinKararListesi"] = metin_karar
    df["MetinDigerDosyaNoListesi"] = metin_diger

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding=encoding)


def build_cli():
    """Komut satırı argümanlarını tanımlar ve döndürür."""
    p = argparse.ArgumentParser(prog="dyeoa-01-segment")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", dest="out", required=True)
    p.add_argument("--cfg", dest="cfg", required=True)
    p.add_argument("--encoding", default="utf-8-sig")
    p.add_argument("--limit", type=int, default=None)
    return p


def main():
    """CLI’yi çalıştırır; dosyaları işler."""
    p = build_cli()
    a = p.parse_args()
    run_segment(a.inp, a.out, a.cfg, a.encoding, a.limit)


if __name__ == "__main__":
    main()


#python src/etl/01_segment.py --in data/interim/kararlar_clean.csv --out data/interim/kararlar_segment.csv --cfg configs/regex_patterns.yml