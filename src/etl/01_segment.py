# placeholder: 01_segment.py
import re, json, yaml, argparse
from pathlib import Path
import pandas as pd

def load_config(path: str | Path) -> dict:
    '''yml konfigürasyonunu yükler'''
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def compile_segment_patterns(cfg: dict) -> dict:
    seg = cfg["segment"]
    return {
        "sections": {
            "baslik": [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("baslik", [])],
            "gerekce": [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("gerekce", [])],
            "hukum":   [re.compile(p, re.I | re.M) for p in seg["section_headers"].get("hukum", [])],
        },
        "court": {
            "header_line": re.compile(seg["court"]["header_line"], re.I | re.M),
            "inline_hints": [re.compile(p, re.I) for p in seg["court"]["inline_hints"]],
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
    '''metni bölümlere ayırır ve span döndürür'''
    hits=[]
    for label, regs in sp.items():
        for rx in regs:
            for m in rx.finditer(text):
                hits.append((m.start(), label))
    hits.sort()
    spans={}
    if hits:
        for i,(pos,label) in enumerate(hits):
            start=pos; end=hits[i+1][0] if i+1<len(hits) else len(text)
            if label not in spans or (end-start)>(spans[label]["span"][1]-spans[label]["span"][0]):
                spans[label]={"span":[start,end]}
    for k in ["baslik","gerekce","hukum"]:
        if k not in spans: spans[k]={"span":[0,0]}
    return spans

def extract_header_court(text: str, header_span: list[int], cp: dict) -> dict:
    '''başlıktaki "MAHKEMESİ:" satırından mahkeme adını alır'''
    hs, he = header_span
    haystack = text[hs:he] if he > hs else text
    m = cp["header_line"].search(haystack)
    if not m:
        return {"MahkemeAdi": None, "span": [0, 0]}
    start = (hs + m.start(1)) if he > hs else m.start(1)
    end   = (hs + m.end(1))   if he > hs else m.end(1)
    return {"MahkemeAdi": m.group(1).strip(), "span": [start, end]}

def _normalize_court_key(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\wçğıöşü\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _overlaps(a: list[int], b: list[int]) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0])

def extract_inline_courts(text: str, cp: dict, exclude_span: list[int] | None, header_value: str | None) -> list:
    '''başlık aralığını hariç tutar; başlıktaki mahkeme adını listeden çıkarır; tekrarları engeller'''
    ex = exclude_span if exclude_span and exclude_span[1] > exclude_span[0] else None
    header_key = _normalize_court_key(header_value) if header_value else None
    seen = set()
    out = []
    for rx in cp["inline_hints"]:
        for m in rx.finditer(text):
            span = [m.start(), m.end()]
            if ex and _overlaps(span, ex):
                continue
            val = m.group(0).strip()
            key = _normalize_court_key(val)
            if header_key and key == header_key:
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append({"deger": val, "span": span})
    return out

def extract_case_type(text: str, ctp: dict) -> dict:
    '''etiketli dava türünü döndürür; yoksa anahtar kelime hitleri verilir'''
    for rx in ctp["key_labels"]:
        m = rx.search(text)
        if m:
            return {"DavaTuru": m.group(1).strip(), "span": [m.start(1), m.end(1)], "anahtarlar": []}
    lowered = text.lower()
    hits = [kw for kw in ctp["keywords"] if kw in lowered]
    return {"DavaTuru": None, "span": [0,0], "anahtarlar": hits}

def _classify_docket(text: str, start: int, end: int, dp: dict) -> str:
    '''ref yakınındaki anahtar sözcüğe göre sınıflandırır'''
    L=max(0,start-dp["ctx_window"]); R=min(len(text), end+dp["ctx_window"])
    left = text[L:start]; right = text[end:R]
    if dp["left_kw"].search(left) or dp["left_kw"].search(right):
        return "esas"
    if dp["right_kw"].search(left) or dp["right_kw"].search(right):
        return "karar"
    return "diger"

def extract_dockets(text: str, dp: dict) -> dict:
    '''metin içindeki 20xx/xxxx referanslarını yıl/sıra ayırarak döndürür'''
    out={"MetinEsasListesi":[], "MetinKararListesi":[], "MetinDigerDosyaNoListesi":[]}
    for m in dp["generic"].finditer(text):
        year, seq = int(m.group(1)), int(m.group(2))
        cls = _classify_docket(text, m.start(), m.end(), dp)
        item={"ham": m.group(0), "yil": year, "sira": seq, "span":[m.start(), m.end()]}
        if cls=="esas":
            out["MetinEsasListesi"].append(item)
        elif cls=="karar":
            out["MetinKararListesi"].append(item)
        else:
            out["MetinDigerDosyaNoListesi"].append(item)
    return out

def run_segment(input_csv: str, output_csv: str, cfg_path: str, encoding: str = "utf-8-sig", limit: int | None = None) -> None:
    '''temiz csv'den mahkeme, dava türü ve metin içi esas/karar no çıkarır (Türkçe kolonlar)'''
    cfg = load_config(cfg_path)
    pats = compile_segment_patterns(cfg)
    df = pd.read_csv(input_csv, encoding=encoding)
    if limit and limit>0: df = df.head(limit)
    col="Karar Metni"

    mahkeme_adi=[]; metin_ici_mahkemeler=[]
    dava_turu=[]; dava_turu_span=[]; dava_kw=[]
    metin_esas=[]; metin_karar=[]; metin_diger=[]

    for txt in df[col].astype(str):
        sections = find_sections(txt, pats["sections"])
        header_span = sections.get("baslik", {}).get("span", [0,0])

        court_hdr = extract_header_court(txt, header_span, pats["court"])
        courts_inline = extract_inline_courts(txt, pats["court"], header_span, court_hdr["MahkemeAdi"])
        ctype = extract_case_type(txt, pats["case_type"])
        docks = extract_dockets(txt, pats["docket"])

        #mahkeme_deger = court_hdr["MahkemeAdi"] or (courts_inline[0]["deger"] if len(courts_inline)==1 else None)

        mahkeme_adi.append(court_hdr["MahkemeAdi"])
        metin_ici_mahkemeler.append(courts_inline)
        dava_turu.append(ctype["DavaTuru"])
        dava_turu_span.append(ctype["span"])
        dava_kw.append(ctype["anahtarlar"])
        metin_esas.append(docks["MetinEsasListesi"])
        metin_karar.append(docks["MetinKararListesi"])
        metin_diger.append(docks["MetinDigerDosyaNoListesi"])

    df["MahkemeAdi"] = mahkeme_adi                         # başlıktan tekil
    df["MetinIciMahkemeler"] = metin_ici_mahkemeler        # metin içindeki liste
    df["DavaTuru"] = dava_turu                         # etiketli bulunursa
    df["DavaTuruSpan"] = dava_turu_span                    # kanıt aralığı
    df["DavaTuruAnahtarlar"] = dava_kw                     # anahtar kelime hitleri
    df["MetinEsasListesi"] = metin_esas                    # {ham,yil,sira,span}
    df["MetinKararListesi"] = metin_karar                  # {ham,yil,sira,span}

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding=encoding)

def build_cli():
    p=argparse.ArgumentParser(prog="dyeoa-01-segment")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", dest="out", required=True)
    p.add_argument("--cfg", dest="cfg", required=True)
    p.add_argument("--encoding", default="utf-8-sig")
    p.add_argument("--limit", type=int, default=None)
    return p

def main():
    p=build_cli(); a=p.parse_args()
    run_segment(a.inp, a.out, a.cfg, a.encoding, a.limit)

if __name__=="__main__":
    main()

#python src/etl/01_segment.py --in data/interim/kararlar_clean.csv --out data/interim/kararlar_segment.csv --cfg configs/regex_patterns.yml
