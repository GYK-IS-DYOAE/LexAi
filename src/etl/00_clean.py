import re
import html
import yaml
import json
import argparse
import unicodedata
from pathlib import Path
import pandas as pd

REQUIRED_COLS = ["Sira", "Daire", "Esas No", "Karar No", "Tarih", "Karar Metni"]

PLACEHOLDER_RE = re.compile(
    r"(\bkarar\s+bulunamad[ıi]\b|"
    r"\bkay[ıi]t\s+bulunamad[ıi]\b|"
    r"\bherhangi\s+bir\s+karar\s+bulunamad[ıi]\b|"
    r"\bsayfa\s+bulunamad[ıi]\b|"
    r"\bhata\s+olu[sş]tu\b|"
    r"\bsonuç\s+bulunamad[ıi]\b)",
    re.I
)
INCELENEN_RE = re.compile(r"(?mi)^\s*[İI]NCELENEN\s+KARAR(?:IN|ININ)?\b.*$")

def load_config(config_path: str | Path) -> dict:
    """YAML dosyasını okuyup sözlük döndürür."""
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))

def compile_patterns(cfg: dict) -> dict:
    """Konfigdeki regexleri derler ve yardımcı desenleri hazırlar."""
    n = cfg["normalize"]
    h = cfg["html"]
    tr = cfg["turkish"]
    seg = cfg.get("segment", {}).get("court", {})
    court_rx_str = seg.get("header_line") if isinstance(seg, dict) else None
    if court_rx_str:
        court_header = re.compile(court_rx_str)
    else:
        court_header = re.compile(r"(?mi)^\s*MAHKEMES[İIıi]\s*:\s*.*$")
    return {
        "crlf": re.compile(n["crlf"]),
        "zero_width": re.compile(n["zw"]),
        "inline_ws": re.compile(n["span"]),
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
        "blank_collapse": n.get("blank_collapse", "single"),
        "strip_banner_regex": n.get("strip_banner_regex"),
        "court_header": court_header,
        "court_header_simple": re.compile(r"(?mi)^\s*MAHKEMES[İIıi]\s*:\s*"),
    }

def html_to_text(text: str, p: dict) -> str:
    """HTML etiketlerini temizler ve entity’leri çözer."""
    if not text:
        return ""
    text = p["script_block"].sub("", text)
    text = p["style_block"].sub("", text)
    text = p["br"].sub("\n", text)
    text = p["block_open"].sub("\n", text)
    text = p["block_close"].sub("\n", text)
    text = p["any_tag"].sub("", text)
    return html.unescape(text)

def normalize_unicode_and_whitespace(text: str, p: dict) -> str:
    """Unicode ve boşlukları normalize eder, boş satırları azaltır."""
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
    return "\n".join(lines)

def _unique_preserve_order(seq):
    """Sıralı tekilleştirme yapar."""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def build_normalized_dates_per_row(all_captures: list) -> list:
    """Her satır için normalize edilmiş, sıralı ve tekil tarih listesi döndürür."""
    out = []
    for row_caps in all_captures or []:
        if not row_caps:
            out.append([])
        else:
            norms = [item.get("norm") for item in row_caps if item.get("norm")]
            out.append(_unique_preserve_order(norms))
    return out

def normalize_dates_in_text(text: str, cfg: dict) -> tuple[str, list]:
    """Metindeki tarihleri yakalar ve ayara göre metin içinde hedef formata çevirir."""
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
    """Banner satırlarını tamamen kaldırır."""
    if not banner_rx:
        return text
    rx = re.compile(banner_rx, flags=re.I)
    lines = []
    for ln in text.split("\n"):
        if rx.fullmatch(ln.strip()):
            continue
        lines.append(ln)
    return "\n".join(lines)

def cut_until_court_header(text: str, p: dict) -> str:
    """İlk 'MAHKEMESİ:' başlığından itibaren kırpar; yoksa olduğu gibi bırakır."""
    cand = []
    rx1 = p.get("court_header")
    rx2 = p.get("court_header_simple")
    if rx1:
        m1 = rx1.search(text)
        if m1:
            cand.append(m1.start())
    if rx2:
        m2 = rx2.search(text)
        if m2:
            cand.append(m2.start())
    if not cand:
        return text.lstrip()
    start = min(cand)
    return text[start:].lstrip()

def fix_spaced_letters(text: str, p: dict) -> str:
    """Aralıklı harflerden oluşan kelimeleri birleştirir."""
    return p["spaced_word"].sub(lambda m: m.group(0).replace(" ", ""), text)

def fix_ordinal_dot_letter(text: str, p: dict) -> str:
    """Sayı-nokta-harf bitişikliğini normalleştirir."""
    return p["ordinal_dot_letter"].sub(r"\1. ", text)

def normalize_colon_spacing(text: str) -> str:
    """İki nokta çevresindeki boşlukları normalize eder."""
    text = re.sub(r"\s+:", ":", text)
    text = re.sub(r":(?!\s|\n)", ": ", text)
    text = re.sub(r":\s{2,}", ": ", text)
    return text

def clean_text(text: str, patterns: dict, cfg: dict) -> tuple[str, list]:
    """Metni temizler, opsiyonel kırpar ve tarihleri normalize eder."""
    if text is None:
        return "", []
    if not isinstance(text, (list, dict, set, tuple)) and pd.isna(text):
        return "", []
    if isinstance(text, str) and text.strip().lower() in {"", "null", "none", "nan", "na"}:
        return "", []
    if not isinstance(text, str):
        text = str(text)
    text = html_to_text(text, patterns)
    text = normalize_unicode_and_whitespace(text, patterns)
    rx = cfg.get("normalize", {}).get("strip_banner_regex")
    if rx:
        text = _strip_banner_lines(text, rx)
    text = INCELENEN_RE.sub("", text)
    if cfg.get("normalize", {}).get("cut_until_court_header", True):
        text = cut_until_court_header(text, patterns)
    text = fix_spaced_letters(text, patterns)
    text = fix_ordinal_dot_letter(text, patterns)
    text = normalize_colon_spacing(text)
    text, date_caps = normalize_dates_in_text(text, cfg)
    if PLACEHOLDER_RE.search(text):
        text = ""
    text = text.strip()
    return text, date_caps

def null_report(df: pd.DataFrame, out_csv: str | None = None) -> pd.DataFrame:
    """Sütun bazında boş/null özetini yazdırır ve istenirse CSV’ye kaydeder."""
    def is_blank(x):
        if x is None:
            return True
        try:
            if not isinstance(x, (list, dict, set, tuple)) and pd.isna(x):
                return True
        except Exception:
            pass
        if isinstance(x, (list, dict, set, tuple)):
            return len(x) == 0
        if isinstance(x, str):
            s = x.strip().lower()
            return (s == "") or (s in {"null", "none", "nan", "na"})
        return False
    summary = pd.DataFrame({
        "Sütun": df.columns,
        "Boş/Null Sayısı": [df[c].apply(is_blank).sum() for c in df.columns],
        "Toplam": [len(df)] * len(df.columns)
    })
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print("\n=== Boş/Null Özet ===")
    print(summary.to_string(index=False))
    return summary

def blank_mask_for_series(s: pd.Series) -> pd.Series:
    """Boş kabul edilen değerler için maske üretir."""
    return s.isna() | s.map(lambda x: isinstance(x, str) and x.strip().lower() in {"", "nan", "null", "none", "na"})

def _infer_format_from_path(output_path: str) -> str:
    suf = Path(output_path).suffix.lower()
    if suf == ".jsonl":
        return "jsonl"
    if suf == ".json":
        return "json"
    if suf == ".csv":
        return "csv"
    # Varsayılan: jsonl
    return "jsonl"

def _write_output(df: pd.DataFrame, output_path: str, encoding: str, fmt: str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "jsonl":
        s = df.to_json(orient="records", lines=True, force_ascii=False)
        p.write_text(s, encoding=encoding)
        return

    if fmt == "json":
        s = df.to_json(orient="records", force_ascii=False, indent=2)
        p.write_text(s, encoding=encoding)
        return

    if fmt == "csv":
        if "KararIlgiliTarihler" in df.columns:
            df = df.copy()
            df["KararIlgiliTarihler"] = df["KararIlgiliTarihler"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else x)
        df.to_csv(p, index=False, encoding="utf-8-sig")
        return

    raise ValueError(f"Bilinmeyen çıktı formatı: {fmt}")

def run_clean(input_csv: str, output_path: str, cfg_path: str,
              encoding: str = "utf-8-sig",
              limit: int | None = None,
              null_report_csv: str | None = None,
              out_format: str | None = None) -> None:
    """CSV’yi okur, metni temizler, tarih kolonunu ekler ve seçilen formata yazar."""
    cfg = load_config(cfg_path)
    patterns = compile_patterns(cfg)
    df = pd.read_csv(input_csv, encoding=encoding)
    if limit:
        df = df.head(limit)
    col = "Karar Metni"
    df = df.dropna(subset=[col]).copy()

    cleaned = []
    all_captures = []
    for txt in df[col]:
        t, caps = clean_text(txt, patterns, cfg)
        cleaned.append(t)
        all_captures.append(caps)
    df[col] = cleaned
    df["KararIlgiliTarihler"] = build_normalized_dates_per_row(all_captures)

    present_required = [c for c in REQUIRED_COLS if c in df.columns]
    if present_required:
        bad_any = pd.Series(False, index=df.index)
        for c in present_required:
            bad_any = bad_any | blank_mask_for_series(df[c])
        df = df[~bad_any].copy()

    fmt = (out_format or _infer_format_from_path(output_path)).lower()
    _write_output(df, output_path, encoding, fmt)

    null_report(df, null_report_csv)

def build_cli() -> argparse.ArgumentParser:
    """Komut satırı argümanlarını tanımlar."""
    parser = argparse.ArgumentParser(prog="LexAi-00-clean")
    parser.add_argument("--in", dest="inp", required=True, help="Girdi CSV yolu")
    parser.add_argument("--out", dest="out", required=True, help="Çıktı dosya yolu (.jsonl/.json/.csv)")
    parser.add_argument("--cfg", dest="cfg", required=True, help="Regex/YAML konfig yolu")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--null-report", dest="null_report", default=None, help="Null özet CSV yolu")
    parser.add_argument("--format", dest="out_format", choices=["jsonl", "json", "csv"], default=None,
                        help="Çıktı formatı (belirtilmezse uzantıdan çıkarılır)")
    return parser

def main() -> None:
    """Argümanları alır ve temizleme sürecini başlatır."""
    parser = build_cli()
    args = parser.parse_args()
    run_clean(args.inp, args.out, args.cfg, args.encoding, args.limit, args.null_report, args.out_format)

if __name__ == "__main__":
    main()



#jsonl
#python src/etl/00_clean.py --in data/raw/kararlar.csv --out data/interim/kararlar_clean.jsonl --cfg configs/regex_patterns.yml --limit 5000 
#json
#python src/etl/00_clean.py --in data/raw/kararlar.csv --out data/interim/kararlar_clean.json --cfg configs/regex_patterns.yml


#python src/etl/00_clean.py --in data/raw/kararlar.csv --out data/interim/kararlar_clean.csv --limit 5000 --cfg configs/regex_patterns.yml --null-report data/interim/boşluk_özeti.csv
#python src/etl/00_clean.py --in data/raw/kararlar.csv --out data/interim/kararlar_clean.csv --limit 5000 --cfg configs/regex_patterns.yml