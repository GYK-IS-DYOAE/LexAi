"""
Uçtan uca ETL orchestrator (in-process, runpy).
Sıra:
  00_clean  -> 01_segment -> 02_extract_llm submit-serial
  -> missing_id -> 02_extract_llm resume -> 03_validate_normalize -> 04_link_laws
"""

from __future__ import annotations
import sys, runpy, contextlib
from pathlib import Path
from dataclasses import dataclass

ROOT     = Path(__file__).resolve().parents[2]
SRC_ETL  = ROOT / "src" / "etl"
DATA     = ROOT / "data"
INTERIM  = DATA / "interim"
DEBUGDIR = INTERIM / "debug"

RAW_CSV              = DATA / "raw" / "kararlar.csv"

CLEAN_JSONL          = INTERIM / "kararlar_clean.jsonl"
CLEAN_JSON           = INTERIM / "kararlar_clean.json"

SEGMENT_JSON         = INTERIM / "kararlar_segment.json"
SEGMENT_JSONL        = INTERIM / "kararlar_segment.jsonl"

EXTRACT_JSONL        = INTERIM / "02_extract_llm.jsonl"

MISSING_IDS_TXT      = DEBUGDIR / "missing_ids.txt"


@contextlib.contextmanager
def temp_argv(argv):
    old = sys.argv[:]
    sys.argv = argv[:]
    try:
        yield
    finally:
        sys.argv = old

def run_script(pyfile: Path, argv: list[str]):
    if not pyfile.exists():
        raise FileNotFoundError(f"Bulunamadı: {pyfile}")
    with temp_argv(argv):
        runpy.run_path(str(pyfile), run_name="__main__")

def step_clean(out_fmt: str = "jsonl", limit: int | None = None):
    """
    out_fmt: 'jsonl' | 'json'
    """
    py = SRC_ETL / "00_clean.py"
    if out_fmt == "jsonl":
        argv = [
            str(py),
            "--in", str(RAW_CSV),
            "--out", str(CLEAN_JSONL),
            "--cfg", "configs/regex_patterns.yml",
        ]
        if limit:
            argv += ["--limit", str(limit)]
    else:
        argv = [
            str(py),
            "--in", str(RAW_CSV),
            "--out", str(CLEAN_JSON),
            "--cfg", "configs/regex_patterns.yml",
        ]
    print("[run] 00_clean:", " ".join(argv[1:]))
    run_script(py, argv)

def step_segment(inp_fmt: str = "jsonl", out_fmt: str = "jsonl"):
    """
    inp_fmt: 'jsonl' (senin komutun böyle)
    out_fmt: 'json' | 'jsonl'
    """
    py = SRC_ETL / "01_segment.py"
    inp = CLEAN_JSONL if inp_fmt == "jsonl" else CLEAN_JSON
    out = SEGMENT_JSONL if out_fmt == "jsonl" else SEGMENT_JSON
    argv = [
        str(py),
        "--in", str(inp),
        "--out", str(out),
        "--cfg", "configs/regex_patterns.yml",
    ]
    print("[run] 01_segment:", " ".join(argv[1:]))
    run_script(py, argv)
    return out 

def step_extract_submit_serial(seg_out: Path, chunk_size=1000, max_bytes=160_000_000, check_interval=60):
    py = SRC_ETL / "02_extract_llm.py"
    argv = [
        str(py), "submit-serial",
        "--in", str(seg_out),
        "--chunk-size", str(chunk_size),
        "--max-bytes", str(max_bytes),
        "--check-interval", str(check_interval),
    ]
    print("[run] 02_extract_llm submit-serial:", " ".join(argv[1:]))
    run_script(py, argv)

def step_missing_ids(seg_out: Path, done_jsonl: Path = EXTRACT_JSONL, out_txt: Path = MISSING_IDS_TXT):
    py = SRC_ETL / "missing_id.py"
    argv = [
        str(py),
        "--seg",  str(seg_out),
        "--done", str(done_jsonl),
        "--out",  str(out_txt),
    ]
    print("[run] missing_id:", " ".join(argv[1:]))
    run_script(py, argv)
    return out_txt

def step_extract_resume(seg_out: Path, *, batch_id: str | None = None,
                        chunk_size=1000, max_bytes=160_000_000, check_interval=60):
    py = SRC_ETL / "02_extract_llm.py"
    argv = [str(py), "resume"]
    if batch_id:
        argv += ["--batch-id", batch_id]
    else:
        argv += ["--all-remaining"]
    argv += [
        "--in", str(seg_out),
        "--chunk-size", str(chunk_size),
        "--max-bytes", str(max_bytes),
        "--check-interval", str(check_interval),
    ]
    print("[run] 02_extract_llm resume:", " ".join(argv[1:]))
    run_script(py, argv)

def step_validate_normalize():
    py = SRC_ETL / "03_validate_normalize.py"
    argv = [str(py)]  
    print("[run] 03_validate_normalize (args yok)")
    run_script(py, argv)

def step_link_laws():
    py = SRC_ETL / "04_link_laws.py"
    argv = [str(py)]  
    print("[run] 04_link_laws (args yok)")
    run_script(py, argv)

@dataclass
class Args:
    clean_out_fmt: str = "jsonl"   # 'jsonl' | 'json'
    segment_out_fmt: str = "jsonl" # 'jsonl' | 'json'
    limit: int = 0                 # clean için opsiyonel
    resume_batch_id: str | None = None  # verilirse batch_id kullan, verilmezse --all-remaining
    skip_clean: bool = False
    skip_validate: bool = False
    skip_link: bool = False

def parse_args() -> Args:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--clean-out-fmt", choices=["jsonl","json"], default="jsonl")
    p.add_argument("--segment-out-fmt", choices=["jsonl","json"], default="jsonl")
    p.add_argument("--limit", type=int, default=0, help="00_clean için opsiyonel limit")
    p.add_argument("--resume-batch-id", default=None, help="resume için tek batch ID; boşsa --all-remaining")
    p.add_argument("--skip-clean", action="store_true")
    p.add_argument("--skip-validate", action="store_true")
    p.add_argument("--skip-link", action="store_true")
    ns = p.parse_args()
    return Args(**vars(ns))

def main():
    a = parse_args()

    # 00_clean
    if not a.skip_clean:
        step_clean(out_fmt=a.clean_out_fmt, limit=(a.limit or None))
    else:
        print("[skip] 00_clean")

    # 01_segment
    seg_path = step_segment(inp_fmt="jsonl", out_fmt=a.segment_out_fmt)

    # 02_extract_llm submit-serial
    step_extract_submit_serial(seg_out=seg_path)

    # missing_id -> eksik listesi
    step_missing_ids(seg_out=seg_path)

    # 02_extract_llm resume
    step_extract_resume(seg_out=seg_path, batch_id=a.resume_batch_id)

    # 03_validate_normalize
    if not a.skip_validate:
        step_validate_normalize()
    else:
        print("[skip] 03_validate_normalize")

    # 04_link_laws
    if not a.skip_link:
        step_link_laws()
    else:
        print("[skip] 04_link_laws")

    print("\n[done] pipeline tamamlandı.")

if __name__ == "__main__":
    main()


# Örnek kullanım
# python src/etl/05_export_processed.py
# python src/etl/05_export_processed.py --clean-out-fmt json
# python src/etl/05_export_processed.py --segment-out-fmt json
# python src/etl/05_export_processed.py --resume-batch-id FAILED_BATCH_123
# python src/etl/05_export_processed.py --skip-clean


