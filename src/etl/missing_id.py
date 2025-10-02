#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
kararlar_segment.jsonl ile 02_extract_llm.jsonl karşılaştırması.
İkinci dosyada bulunmayan Id'ler data/interim/debug/missing_ids.txt'ye yazılır.
"""

import argparse, json
from pathlib import Path

CANDIDATE_KEYS = ("Id", "ID", "id", "custom_id")
NESTED_KEYS = ("input", "record", "metadata", "meta", "response", "responses", "data", "output", "message")

def pick_id(obj):
    """JSON objesinden Id/custom_id değerini olabildiğince esnek çıkar."""
    if not isinstance(obj, dict):
        return None

    for k in CANDIDATE_KEYS:
        v = obj.get(k)
        if v not in (None, ""):
            return str(v)

    for k in NESTED_KEYS:
        if k in obj:
            v = obj[k]
            if isinstance(v, dict):
                got = pick_id(v)
                if got: return got
            elif isinstance(v, list):
                for it in v:
                    got = pick_id(it)
                    if got: return got
    return None

def load_ids_from_jsonl(path: Path) -> set[str]:
    ids = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            val = pick_id(obj)
            if val:
                ids.add(val.strip())
    return ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seg",  type=Path, default=Path("data/interim/kararlar_segment.jsonl"),
                    help="Kaynak: segment JSONL")
    ap.add_argument("--done", type=Path, default=Path("data/interim/02_extract_llm.jsonl"),
                    help="Karşılaştırılacak: işlenmiş JSONL")
    ap.add_argument("--out",  type=Path, default=Path("data/interim/debug/missing_ids.txt"),
                    help="Eksik Id çıktı dosyası (txt)")
    args = ap.parse_args()

    seg_ids  = load_ids_from_jsonl(args.seg)
    done_ids = load_ids_from_jsonl(args.done)

    missing = sorted(seg_ids - done_ids, key=lambda x: (len(x), x))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for mid in missing:
            if mid:
                f.write(mid + "\n")

    print(f"Segment toplam: {len(seg_ids)}")
    print(f"İşlenmiş toplam: {len(done_ids)}")
    print(f"Eksik (yazıldı): {len(missing)}")
    print(f"Çıktı: {args.out}")

if __name__ == "__main__":
    main()
