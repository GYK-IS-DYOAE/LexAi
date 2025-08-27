import re
import html
import yaml
import argparse
import unicodedata
from pathlib import Path
import pandas as pd

def load_config(config_path: str | Path) -> dict:
    '''yaml dosyasını okuyup dict döndürür'''
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))

def compile_patterns(cfg: dict) -> dict:
    '''yml içindeki string regexleri derler'''
    n = cfg["normalize"]
    h = cfg["html"]
    tr = cfg["turkish"]
    return {
        "crlf": re.compile(n["crlf"]),
        "zero_width": re.compile(n["zw"]),
        "inline_ws": re.compile(n["span"]),
    #   "many_blank": re.compile(n["many_newlines"]),
        "trailing_ws": re.compile(n["trailing"]),
        "dash_variants": re.compile(n["dash"]),
        "script_block": re.compile(h["script"], re.I | re.S),
        "style_block": re.compile(h["style"], re.I | re.S),
        "br": re.compile(h["br"], re.I),
        "block_open": re.compile(h["block_open"], re.I),
        "block_close": re.compile(h["block_close"], re.I),
        "any_tag": re.compile(h["tag"]),
        "spaced_word": re.compile(tr["spaced_word"]),
        "ordinal_dot_letter": re.compile(tr["ordinal_dot_letter"]),
        "nbsp_chars": [bytes(p.encode("utf-8")).decode("unicode_escape") for p in n["nbsp"]],
        "smart_quotes": [(a, b) for a, b in n["smart_quotes"]],
        "line_separators": [bytes(s.encode("utf-8")).decode("unicode_escape") for s in n.get("line_separators", [])],
        "blank_collapse": n.get("blank_collapse", "single"),  # "single" | "none"
    }

def html_to_text(text: str, p: dict) -> str:
    '''html taglarını temizler ve entityleri çözer'''
    if not text:
        return ""
    text = p["script_block"].sub("", text)
    text = p["style_block"].sub("", text)
    text = p["br"].sub("\n", text)
    text = p["block_open"].sub("\n", text)
    text = p["block_close"].sub("\n", text)
    text = p["any_tag"].sub("", text)
    text = html.unescape(text)
    return text

def normalize_unicode_and_whitespace(text: str, p: dict) -> str:
    '''unicode ve boşluk normalizasyonu yapar, boş satırları tamamen kaldırır'''
    if not text:
        return ""

    for sep in p.get("line_separators", []):
        text = text.replace(sep, "\n")

    text = p["crlf"].sub("\n", text)
    text = unicodedata.normalize("NFKC", text)

    for ch in p["nbsp_chars"]:
        text = text.replace(ch, " ")

    text = p["zero_width"].sub("", text)
    text = p["dash_variants"].sub("-", text)

    for src, dst in p["smart_quotes"]:
        text = text.replace(src, dst)

    lines = []
    for ln in text.split("\n"):
        ln = p["inline_ws"].sub(" ", ln).strip()
        if ln != "":
            lines.append(ln)

    text = "\n".join(lines)
    return text


def build_normalized_dates(captures: list) -> list:
    '''yakalanan tarih kayıtlarından normalize değerlerin sıralı ve tekil listesini üretir'''
    seen = set()
    out = []
    for row_caps in captures:
        if not row_caps:
            continue
        for item in row_caps:
            val = item.get("norm")
            if val and val not in seen:
                seen.add(val)
                out.append(val)
    return out

def build_normalized_dates_per_row(all_captures: list) -> list:
    '''her satırdaki yakalanan tarihlerden sadece normalize değerlerin listesi'''
    out = []
    for row_caps in all_captures:
        if not row_caps:
            out.append([])
        else:
            out.append([item["norm"] for item in row_caps if "norm" in item])
    return out


def normalize_dates_in_text(text: str, cfg: dict) -> tuple[str, list]:
    '''tarihleri yakalar; ayarlıysa metin içinde normalize eder; yakalananları liste olarak döner'''
    dn = cfg.get("date_normalize", {})
    if not dn or not dn.get("enabled", False):
        return text, []

    months = dn["months_tr"]
    keys = sorted(set(months.keys()), key=len, reverse=True)
    rx_months = re.compile("|".join(map(re.escape, keys)), flags=re.I)
    month_map = {k.lower(): v for k, v in months.items()}

    pats = dn["patterns"]
    target = dn.get("target", "iso")
    month_only_target = dn.get("month_only_target", "iso_month")
    assume_dmy = dn.get("assume_dmy", True)

    captures = []

    def fmt(y, m, d):
        if target == "dmy_dot":
            return f"{int(d):02d}.{int(m):02d}.{int(y):04d}"
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    def fmt_month(y, m):
        if month_only_target == "iso_month":
            return f"{int(y):04d}-{int(m):02d}"
        return f"{int(y):04d}-{int(m):02d}"

    rx_dmy_sep  = re.compile(pats["dmy_sep"])
    rx_dmy_text = re.compile(pats["dmy_text"].replace("{MONTHS_RX}", rx_months.pattern), flags=re.I)
    rx_my_text  = re.compile(pats["my_text"].replace("{MONTHS_RX}", rx_months.pattern), flags=re.I)

    for m in rx_dmy_sep.finditer(text):
        d, mo, y = m.group(1), m.group(2), m.group(3)
        norm = fmt(y, mo, d) if assume_dmy else m.group(0)
        captures.append({"value": m.group(0), "norm": norm, "span": [m.start(), m.end()]})
    if dn.get("normalize_in_text", False):
        text = rx_dmy_sep.sub(lambda m: fmt(m.group(3), m.group(2), m.group(1)), text)

    for m in rx_dmy_text.finditer(text):
        d, mon, y = m.group(1), m.group(2), m.group(3)
        mm = month_map.get(mon.lower())
        if mm:
            norm = fmt(y, mm, d)
            captures.append({"value": m.group(0), "norm": norm, "span": [m.start(), m.end()]})
    if dn.get("normalize_in_text", False):
        text = rx_dmy_text.sub(lambda m: fmt(m.group(3), month_map.get(m.group(2).lower(), "01"), m.group(1)), text)

    for m in rx_my_text.finditer(text):
        mon, y = m.group(1), m.group(2)
        mm = month_map.get(mon.lower())
        if mm:
            norm = fmt_month(y, mm)
            captures.append({"value": m.group(0), "norm": norm, "span": [m.start(), m.end()]})
    if dn.get("normalize_in_text", False):
        text = rx_my_text.sub(lambda m: fmt_month(m.group(2), month_map.get(m.group(1).lower(), "01")), text)

    return text, captures

def _strip_banner_lines(text: str, banner_rx: str | None) -> str:
    '''İçtihat Metni vb. tek başına duran banner satırları siler'''
    if not banner_rx:
        return text
    rx = re.compile(banner_rx, flags=re.I)
    lines = []
    for ln in text.split("\n"):
        if rx.fullmatch(ln.strip()):
            continue
        lines.append(ln)
    return "\n".join(lines)

def fix_spaced_letters(text: str, p: dict) -> str:
    '''m a h k e m e s i -> Mahkemesi yapar'''
    return p["spaced_word"].sub(lambda m: m.group(0).replace(" ", ""), text)

def fix_ordinal_dot_letter(text: str, p: dict) -> str:
    '''4.İcra -> 4. İcra yapar'''
    return p["ordinal_dot_letter"].sub(r"\1. ", text)

def normalize_colon_spacing(text: str) -> str:
    '''iki nokta etrafındaki boşlukları normalize eder'''
    text = re.sub(r"\s+:", ":", text)
    text = re.sub(r":(?!\s|\n)", ": ", text)
    text = re.sub(r":\s{2,}", ": ", text)
    return text

def clean_text(text: str, patterns: dict, cfg: dict) -> tuple[str, list]:
    '''metni temizler; tarihleri yakalar ve opsiyonel normalize eder'''
    text = html_to_text(text or "", patterns)
    text = normalize_unicode_and_whitespace(text, patterns)
    text = fix_spaced_letters(text, patterns)
    text = fix_ordinal_dot_letter(text, patterns)
    text = normalize_colon_spacing(text)
    rx = cfg.get("normalize", {}).get("strip_banner_regex")
    if rx:
        text = _strip_banner_lines(text, rx)
    text, date_caps = normalize_dates_in_text(text, cfg)
    return text, date_caps

def run_clean(input_csv: str, output_csv: str, cfg_path: str, encoding: str = "utf-8-sig", limit: int | None = None) -> None:
    '''csv okur, karar metnini temizler; tarihleri yakalayarak iki yan kolon oluşturur'''
    cfg = load_config(cfg_path)
    patterns = compile_patterns(cfg)
    df = pd.read_csv(input_csv, encoding=encoding)
    if limit:
        df = df.head(limit)
    col = "Karar Metni"

    cleaned = []
    all_captures = []
    for txt in df[col].astype(str):
        t, caps = clean_text(txt, patterns, cfg)
        cleaned.append(t)
        all_captures.append(caps)

    df[col] = cleaned

    if cfg.get("date_normalize", {}).get("capture_column", True):
        df["TespitEdilenTarihler"] = all_captures

    df["KararIlgiliTarihler"] = build_normalized_dates_per_row(all_captures)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding=encoding)

def build_cli() -> argparse.ArgumentParser:
    '''komut satırı argümanlarını tanımlar'''
    parser = argparse.ArgumentParser(prog="dyeoa-00-clean")
    parser.add_argument("--in", dest="inp", required=True)
    parser.add_argument("--out", dest="out", required=True)
    parser.add_argument("--cfg", dest="cfg", required=True)
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--limit", type=int, default=None)
    return parser

def main() -> None:
    '''argümanları alır ve temizleme sürecini başlatır'''
    parser = build_cli()
    args = parser.parse_args()
    run_clean(args.inp, args.out, args.cfg, args.encoding, args.limit)

if __name__ == "__main__":
    main()


#python src/etl/00_clean.py --in data/raw/kararlar.csv --out data/interim/kararlar_clean.csv --limit 5000 --cfg configs/regex_patterns.yml