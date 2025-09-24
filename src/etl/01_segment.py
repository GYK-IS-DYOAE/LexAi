# python src/etl/01_segment.py --in data/interim/kararlar_clean.jsonl --out data/interim/kararlar_segment.json --cfg configs/regex_patterns.yml
import re, json, yaml, argparse
from pathlib import Path
import pandas as pd  # csv girdi/çıktı için
import csv

def load_config(path: str | Path) -> dict:
    """YAML konfigürasyonunu okur ve döndürür."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def compile_segment_patterns(cfg: dict) -> dict:
    """YAML’deki desenleri derler; bölüm başlıkları, mahkeme, dava türü ve dosya no şablonlarını döndürür."""
    seg = cfg["segment"]
    return {
        "sections": {
            "baslik":  [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("baslik", [])],
            "gerekce": [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("gerekce", [])],
            "hukum":   [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("hukum", [])],
        },
        "court": {
            "header_line":  re.compile(seg["court"]["header_line"], re.I | re.M | re.U),
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
    """Başlık/gerekçe/hüküm için en mantıklı blok sınırlarını bulur."""
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
    """Başlıkta ‘MAHKEMESİ: …’ benzeri ifadeden mahkeme adını döndürür."""
    hs, he = header_span
    haystack = text[hs:he] if he > hs else text
    m = cp["header_line"].search(haystack)
    if not m:
        return {"MahkemeAdi": None, "span": [0, 0]}
    grp = "court" if "court" in m.re.groupindex else 1
    value = m.group(grp).strip()
    start = (hs + m.start(grp)) if he > hs else m.start(grp)
    end = (hs + m.end(grp)) if he > hs else m.end(grp)
    return {"MahkemeAdi": value, "span": [start, end]}

def _normalize_court_key(s: str) -> str:
    """Mahkeme adını karşılaştırma için normalize eder (kısaltmaları açar, boşlukları sadeleştirir)."""
    s = s.strip().lower()
    s = s.replace("mah.", "mahkemesi").replace("daire.", "dairesi")
    s = s.replace("başkanlığı", "")
    s = re.sub(r"[^\wçğıöşü\s]", " ", s, flags=re.U)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _overlaps(a: list[int], b: list[int]) -> bool:
    """İki [start,end] aralığının çakışıp çakışmadığını söyler."""
    return not (a[1] <= b[0] or b[1] <= a[0])

_COURT_TAIL_RX = re.compile(r"(mahkemesi|mah\.|dairesi|daire\.)\b", re.I | re.U)

def _trim_to_court_phrase(s: str, max_left_tokens: int = 5) -> str:
    """Eşleşmeyi ‘… Mahkemesi / … Dairesi’ kalıbına indirger; gürültüyü atar."""
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
    tail = re.sub(r"\bdaire\.\b", "Dairesi", tail, flags=re.I)
    phrase = " ".join(keep + [tail])
    phrase = re.sub(r"\s+", " ", phrase).strip()

    def _tc(w: str) -> str:
        return w if w.isupper() and len(w) <= 4 else w.capitalize()
    return " ".join(_tc(w) for w in phrase.split())

def extract_inline_courts(text: str, cp: dict, exclude_span: list[int] | None, header_value: str | None) -> list:
    """Başlık bölgesini hariç tutarak metinde geçen mahkeme adlarını (string olarak) listeler."""
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
            out.append(val)
    return out

def extract_case_type(text: str, ctp: dict) -> str | None:
    """Etiketli dava türünü döndürür; yoksa None."""
    for rx in ctp["key_labels"]:
        m = rx.search(text)
        if m:
            return m.group(1).strip()
    return None

def _classify_docket(text: str, start: int, end: int, dp: dict) -> str:
    """20xx/xxxx ifadesini bağlamına göre sınıflandırır (‘esas’/‘karar’/‘diger’)."""
    L = max(0, start - dp["ctx_window"])
    R = min(len(text), end + dp["ctx_window"])
    left = text[L:start]
    right = text[end:R]
    if dp["left_kw"].search(left) or dp["left_kw"].search(right):
        return "esas"
    if dp["right_kw"].search(left) or dp["right_kw"].search(right):
        return "karar"
    return "diger"

def extract_dockets(text: str, dp: dict) -> list[str]:
    """Metindeki 20xx/xxxx referanslarını ayrıştırır; yalnızca Esas’ları 'YYYY/NNNN' listesi olarak döndürür."""
    seen, out = set(), []
    for m in dp["generic"].finditer(text):
        cls = _classify_docket(text, m.start(), m.end(), dp)
        if cls != "esas":
            continue
        yil, sira = m.group(1), m.group(2)
        val = f"{int(yil):04d}/{int(sira)}"
        if val not in seen:
            seen.add(val)
            out.append(val)
    return out

# ---------------------------
# I/O yardımcıları (format algılama, okuma, yazma)
# ---------------------------
def _infer_format_from_path(path: str) -> str:
    suf = Path(path).suffix.lower()
    if suf == ".jsonl": return "jsonl"
    if suf == ".json":  return "json"
    if suf == ".csv":   return "csv"
    return "jsonl"

def _iter_jsonl(path: str, limit: int | None = None, encoding: str = "utf-8-sig"):
    """JSONL dosyasını satır satır okur; BOM ve parse hatalarını tolere eder."""
    import sys
    with open(path, "r", encoding=encoding) as f:
        for i, line in enumerate(f, 1):
            s = line.lstrip("\ufeff").strip()
            if not s:
                if limit and i >= limit: break
                continue
            try:
                yield json.loads(s)
            except json.JSONDecodeError as e:
                print(f"[warn] JSONL parse atlandı (satır {i}): {e}", file=sys.stderr)
            if limit and i >= limit:
                break

def _read_input(inp: str, encoding: str, limit: int | None):
    fmt = _infer_format_from_path(inp)
    if fmt == "jsonl":
        return list(_iter_jsonl(inp, limit=limit, encoding=encoding))
    if fmt == "json":
        data = json.loads(Path(inp).read_text(encoding=encoding))
        if isinstance(data, dict):
            data = data.get("records") or data.get("data") or []
        if limit:
            data = data[:limit]
        return data
    if fmt == "csv":
        df = pd.read_csv(inp, encoding=encoding)
        if limit:
            df = df.head(limit)
        return df.to_dict(orient="records")
    return list(_iter_jsonl(inp, limit=limit, encoding=encoding))

def _csv_friendly(v):
    """CSV’de liste/dict değerleri JSON stringe çevir."""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v

PREFERRED_ORDER = ["Id", "Daire", "Esas No", "Karar No", "Tarih", "Karar Metni",
                   "MahkemeAdi", "MetinIciMahkemeler", "DavaTuru", "MetinEsasListesi"]

def _order_keys(obj: dict) -> dict:
    head = {k: obj[k] for k in PREFERRED_ORDER if k in obj}
    tail = {k: v for k, v in obj.items() if k not in head}
    return {**head, **tail}


def _write_output(records: list[dict], out_path: str, encoding: str):
    fmt = _infer_format_from_path(out_path)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "jsonl":
        with open(p, "w", encoding=encoding) as f:
            for rec in records:
                f.write(json.dumps(_order_keys(rec), ensure_ascii=False) + "\n")
        return

    if fmt == "json":
        with open(p, "w", encoding=encoding) as f:
            json.dump([_order_keys(r) for r in records], f, ensure_ascii=False)
        return


    if fmt == "csv":
        if not records:
            pd.DataFrame().to_csv(p, index=False, encoding="utf-8-sig")
            return
        df = pd.DataFrame(records)
        if "Sira" in df.columns:
            df = df.drop(columns=["Sira"])
        cols = (["Id"] if "Id" in df.columns else []) + [c for c in df.columns if c != "Id"]
        df = df[cols]
        for col in df.columns:
            df[col] = df[col].map(_csv_friendly)
        df.to_csv(p, index=False, encoding="utf-8-sig",
                  quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        return

    raise ValueError(f"Bilinmeyen çıktı formatı: {fmt}")

# ---------------------------

def run_segment(input_path: str, output_path: str, cfg_path: str, encoding: str = "utf-8-sig", limit: int | None = None) -> None:
    """Girdiyi okur, alan çıkarımı yapar ve sonucu seçilen formatta yazar."""
    cfg = load_config(cfg_path)
    pats = compile_segment_patterns(cfg)

    results = []
    for idx, rec in enumerate(_read_input(input_path, encoding=encoding, limit=limit), start=1):
        txt = str(rec.get("Karar Metni", "") or "")

        sections = find_sections(txt, pats["sections"])
        header_span = sections.get("baslik", {}).get("span", [0, 0])

        court_hdr = extract_header_court(txt, header_span, pats["court"])
        exclude_span = court_hdr.get("span", [0, 0])

        courts_inline = extract_inline_courts(txt, pats["court"], exclude_span, court_hdr["MahkemeAdi"])
        ctype = extract_case_type(txt, pats["case_type"])
        metin_esas_listesi = extract_dockets(txt, pats["docket"])

        rec["Id"] = idx
        if "Sira" in rec:
            del rec["Sira"]
        rec["MahkemeAdi"] = court_hdr["MahkemeAdi"]
        rec["MetinIciMahkemeler"] = courts_inline
        rec["DavaTuru"] = ctype
        rec["MetinEsasListesi"] = metin_esas_listesi

        results.append(rec)

    _write_output(results, output_path, encoding)

def build_cli():
    """Komut satırı argümanlarını tanımlar."""
    p = argparse.ArgumentParser(prog="LexAi-01-segment")
    p.add_argument("--in", dest="inp", required=True, help="Girdi dosyası (.jsonl/.json/.csv)")
    p.add_argument("--out", dest="out", required=True, help="Çıktı dosyası (.jsonl/.json/.csv)")
    p.add_argument("--cfg", dest="cfg", required=True, help="regex_patterns.yml")
    p.add_argument("--encoding", default="utf-8-sig")
    p.add_argument("--limit", type=int, default=None)
    return p

def main():
    """CLI’yi başlatır ve dosyaları işler."""
    p = build_cli()
    a = p.parse_args()
    run_segment(a.inp, a.out, a.cfg, a.encoding, a.limit)

if __name__ == "__main__":
    main()


#json
#python src/etl/01_segment.py --in data/interim/kararlar_clean.jsonl --out data/interim/kararlar_segment.json --cfg configs/regex_patterns.yml
#jsonl
#python src/etl/01_segment.py --in data/interim/kararlar_clean.jsonl --out data/interim/kararlar_segment.jsonl --cfg configs/regex_patterns.yml
#csv
#python src/etl/01_segment.py --in data/interim/kararlar_clean.csv --out data/interim/kararlar_segment.csv --cfg configs/regex_patterns.yml
