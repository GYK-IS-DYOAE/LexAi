#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAI Batch seri orkestratör (iki alt-komut: submit-serial, resume)

- submit-serial: Girdiyi chunk-size (vars 1000) ile parçalara böler, her parçayı
  TEK TEK gönderir; batch TAMAMLANINCA sonuçları 02_extract_llm.jsonl'a ekler,
  done/remaining dosyalarını atomik güncelleyip SONRA sıradaki parçaya geçer.
  (Paralel gönderim yok; collect gereksiz.)

- resume: Kalan/fail kayıt havuzunu seçer (tek batch id veya tüm remaining),
  sonra bu havuzu chunk-size ile yeniden parçalayıp YİNE SERİ şekilde
  batch-batch gönderir. Her batch tamamlanınca sonuçlar yazılır ve devam edilir.
  (Böylece "40k remaining'i tek seferde gönderme" sorunu olmaz.)

Varsayılan yollar:
  Girdi:   data/interim/kararlar_segment.jsonl
  Çıktı:   data/interim/02_extract_llm.jsonl
  Debug:   data/interim/debug/{batch_id.txt,submitted_ids.txt,done_ids.txt,remaining_ids_*.txt}
  Prompt:  src/llm/prompts/extract_system.md
"""

import sys, os, json, argparse, time, tempfile
from typing import Iterable, List, Dict, Set, Tuple, Generator
from math import ceil
from pathlib import Path
from openai import OpenAI


def ensure_dir(p: Path):
    """Verilen yolun dizinlerini (yoksa) oluşturur."""
    p.mkdir(parents=True, exist_ok=True)

def read_lines(p: Path) -> List[str]:
    """Bir metin dosyasındaki satırları kırparak okur; dosya yoksa boş liste döner."""
    if not p.exists():
        return []
    return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def write_lines_atomic(p: Path, lines: Iterable[str]):
    """Satır listesini dosyaya atomik olarak yazar (tmp dosya + replace)."""
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=p.name + ".", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for x in lines:
                s = str(x).strip()
                if s:
                    f.write(s + "\n")
        Path(tmp).replace(p)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def append_jsonl_atomic(p: Path, json_lines: Iterable[str]):
    """JSONL satırlarını dosyanın sonuna ekler; flush+fsync ile yarım yazım riskini azaltır."""
    ensure_dir(p.parent)
    with p.open("a", encoding="utf-8") as f:
        for ln in json_lines:
            f.write(ln if ln.endswith("\n") else ln + "\n")
        f.flush()
        os.fsync(f.fileno())

def append_lines(p: Path, lines: Iterable[str]):
    """Verilen satırları (atomik gerektirmeyen) dosyanın sonuna ekler."""
    ensure_dir(p.parent)
    with p.open("a", encoding="utf-8") as f:
        for x in lines:
            s = str(x).strip()
            if s:
                f.write(s + "\n")

def load_system_prompt(prompt_path: Path) -> str:
    """System prompt dosyasını (UTF-8) okur ve döndürür."""
    return prompt_path.read_text(encoding="utf-8")

def load_api_key() -> str:
    """OPENAI_API_KEY ortam değişkeni ya da data/interim/key/openai.key dosyasından anahtarı yükler."""
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key.strip()
    key_path = Path("data/interim/key/openai.key")
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    raise RuntimeError("OpenAI API key bulunamadı.")

def build_task(custom_id: str, system_prompt: str, user_text: str, model: str) -> Dict:
    """Tek bir kayıt için Chat Completions batch satırı (JSON) üretir."""
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model,
            "temperature": 0.0,
            "seed": 42,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text or ""},
            ],
        },
    }

def parse_batch_result_line(line: str) -> Tuple[str, Dict, str]:
    """Batch çıktı satırını parse eder; (custom_id, json_data, error_str) döndürür."""
    o = json.loads(line)
    cid = o.get("custom_id", "")
    resp = o.get("response")
    if resp and "body" in resp:
        body = resp["body"]
        try:
            content = body["choices"][0]["message"]["content"]
            data = json.loads(content) if isinstance(content, str) else content
            return cid, data, ""
        except Exception as e:
            return cid, {}, f"parse_error: {e}"
    err = o.get("error")
    if err:
        return cid, {}, json.dumps(err, ensure_ascii=False)
    return cid, {}, "unknown_result_shape"

def _iter_records_any(path: Path, limit: int | None = None, encoding: str = "utf-8-sig") -> Generator[Dict, None, None]:
    """JSONL veya JSON dosyasından kayıtları sözlük olarak sıralı üretir (generator)."""
    with path.open("r", encoding=encoding) as f:
        head = ""
        while True:
            ch = f.read(1)
            if not ch:
                break
            if ch == "\ufeff" or ch.isspace():
                continue
            head = ch
            break

    # JSON dosyası
    if head == "[":
        data = json.loads(path.read_text(encoding=encoding))
        count = 0
        for item in data:
            yield item if isinstance(item, dict) else {"_raw": item}
            count += 1
            if limit and count >= limit:
                return
        return

    # JSONL dosyası
    with path.open("r", encoding=encoding) as f:
        count = 0
        for i, raw in enumerate(f, 1):
            s = raw.lstrip("\ufeff").strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError as e:
                print(f"[warn] atlandı (satır {i}): {e}", file=sys.stderr)
                continue
            if isinstance(rec, dict):
                yield rec
                count += 1
            elif isinstance(rec, list):
                for item in rec:
                    yield item if isinstance(item, dict) else {"_raw": item}
                    count += 1
                    if limit and count >= limit:
                        return
            else:
                yield {"_raw": rec}
                count += 1
            if limit and count >= limit:
                return

def _write_tasks_chunked(
    pairs: List[Tuple[str, str]],
    out_dir: Path,
    system_prompt: str,
    model: str,
    split: int = 1,
    max_bytes: int = 180 * 1024 * 1024
) -> List[Tuple[Path, List[str]]]:
    """Kayıtları split adet parçaya (ve max_bytes sınırına uyarak) .jsonl dosyalarına yazar ve parça listesini döndürür."""
    ensure_dir(out_dir)
    if split < 1:
        split = 1

    n = len(pairs)
    target_per_part = ceil(n / split)

    parts: List[Tuple[Path, List[str]]] = []
    part_idx = 1
    cur_ids: List[str] = []
    cur_size = 0
    wf = None

    def _open_new_writer(idx: int):
        """Yeni parça dosyası açar."""
        return open(out_dir / f"batch_input.part{idx:02d}.jsonl", "w", encoding="utf-8")

    try:
        wf = _open_new_writer(part_idx)
        for _id, text in pairs:
            line = json.dumps(build_task(_id, system_prompt, text, model), ensure_ascii=False) + "\n"
            b = line.encode("utf-8")
            need_new = False

            if len(cur_ids) >= target_per_part:
                need_new = True
            if cur_size + len(b) > max_bytes:
                need_new = True

            if need_new and cur_ids:
                wf.close()
                parts.append((out_dir / f"batch_input.part{part_idx:02d}.jsonl", cur_ids))
                part_idx += 1
                wf = _open_new_writer(part_idx)
                cur_ids = []
                cur_size = 0

            wf.write(line)
            cur_ids.append(_id)
            cur_size += len(b)

        if cur_ids:
            wf.close()
            parts.append((out_dir / f"batch_input.part{part_idx:02d}.jsonl", cur_ids))
    finally:
        if wf and not wf.closed:
            wf.close()

    return parts

def cmd_submit_serial(args):
    """Parçaları sırayla gönderir; her batch tamamlanınca çıktı dosyasına yazar ve sonra sıradakine geçer (tek aktif batch)."""
    client = OpenAI(api_key=load_api_key())

    input_path        = args.inp
    out_dir           = Path("data/interim")
    debug_dir         = out_dir / "debug"
    submitted_path    = debug_dir / "submitted_ids.txt"
    done_path         = debug_dir / "done_ids.txt"
    batch_id_path     = debug_dir / "batch_id.txt"

    ensure_dir(debug_dir)

    done_ids: Set[str] = set(read_lines(done_path))
    already_submitted: Set[str] = set(read_lines(submitted_path))
    system_prompt = load_system_prompt(args.prompt)

    pairs: List[Tuple[str, str]] = []
    for i, obj in enumerate(_iter_records_any(input_path, limit=args.limit or None, encoding="utf-8-sig"), 1):
        _id = str(obj.get(args.id_field, i))
        if _id in done_ids or _id in already_submitted:
            continue
        text = (
            obj.get(args.text_field)
            or obj.get("karar_metni")
            or obj.get("Karar Metni")
            or obj.get("content")
            or ""
        )
        pairs.append((_id, text))

    if not pairs:
        print("[submit-serial] Gönderilecek kayıt yok.")
        return

    n = len(pairs)
    chunk_size = max(1, int(args.chunk_size))
    split = max(1, ceil(n / chunk_size))

    parts = _write_tasks_chunked(
        pairs=pairs,
        out_dir=debug_dir,
        system_prompt=system_prompt,
        model=args.model,
        split=split,
        max_bytes=int(args.max_bytes)
    )
    print(f"[submit-serial] {n} kayıt, {len(parts)} parça (≈{chunk_size}/parça)")

    results_path = out_dir / "02_extract_llm.jsonl"

    for idx, (path, ids) in enumerate(parts, 1):
        print(f"[submit-serial] ({idx}/{len(parts)}) gönderiliyor: {path.name} (kayıt={len(ids)})")
        up = client.files.create(file=open(path, "rb"), purpose="batch")
        job = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions", completion_window="24h")

        append_lines(batch_id_path, [job.id])
        append_lines(submitted_path, ids)

        remaining_path = debug_dir / f"remaining_ids_{job.id}.txt"
        write_lines_atomic(remaining_path, ids)

        last_status = None
        while True:
            job = client.batches.retrieve(job.id)
            status = getattr(job, "status", "unknown")
            if status != last_status:
                print(f"[submit-serial] batch {job.id} status={status}")
                last_status = status
            if status in ("completed", "failed", "expired", "canceled"):
                break
            time.sleep(args.check_interval)

        new_completed: Set[str] = set()
        new_failed: Set[str] = set()

        jsonl_buffer = []
        if getattr(job, "output_file_id", None):
            text = client.files.content(job.output_file_id).text
            for ln in text.strip().splitlines():
                _id, data, err = parse_batch_result_line(ln)
                if _id and not err:
                    jsonl_buffer.append(json.dumps({"Id": _id, "output": data}, ensure_ascii=False))
                    new_completed.add(_id)
                elif _id:
                    new_failed.add(_id)

        if jsonl_buffer:
            append_jsonl_atomic(results_path, jsonl_buffer)

        if getattr(job, "error_file_id", None):
            etext = client.files.content(job.error_file_id).text
            for ln in etext.strip().splitlines():
                try:
                    o = json.loads(ln)
                    cid = o.get("custom_id")
                    if cid:
                        new_failed.add(cid)
                except Exception:
                    pass

        if new_completed:
            di = set(read_lines(done_path))
            di |= new_completed
            write_lines_atomic(done_path, sorted(di))

        submitted_ids_for_this_batch = set(read_lines(remaining_path))
        remaining_now = sorted(list(submitted_ids_for_this_batch - new_completed))
        write_lines_atomic(remaining_path, remaining_now)

        print(json.dumps({
            "batch_id": job.id,
            "status": getattr(job, "status", "unknown"),
            "completed_added": len(new_completed),
            "failed_added": len(new_failed),
            "remaining_now": len(remaining_now)
        }, ensure_ascii=False, indent=2))

    print("[submit-serial] tüm parçalar sırayla gönderildi ve toplandı.")

def _gather_remaining_ids(debug_dir: Path, batch_id: str | None, limit_n: int) -> List[str]:
    """Tek bir batch için ya da tüm remaining dosyalarından ID listesi döndürür (limit_n uygulanır)."""
    if batch_id:
        batch_remaining_path = debug_dir / f"remaining_ids_{batch_id}.txt"
        rem = read_lines(batch_remaining_path)
        return rem[:limit_n] if (limit_n and limit_n > 0) else rem
    # all remaining
    pool: Set[str] = set()
    for p in debug_dir.glob("remaining_ids_*.txt"):
        pool |= set(read_lines(p))
    rem = sorted(pool)
    return rem[:limit_n] if (limit_n and limit_n > 0) else rem

def cmd_resume(args):
    """Kalan/fail kayıt havuzunu chunk-size ile yeniden parçalayıp SERİ olarak batch-batch gönderir ve sonuçları yazdırır."""
    client = OpenAI(api_key=load_api_key())

    input_path     = args.inp
    out_dir        = Path("data/interim")
    debug_dir      = out_dir / "debug"
    batch_input    = debug_dir / "batch_input_resume.jsonl"
    submitted_path = debug_dir / "submitted_ids.txt"
    batch_id_path  = debug_dir / "batch_id.txt"

    ensure_dir(debug_dir)

    remaining_ids: List[str] = _gather_remaining_ids(
        debug_dir=debug_dir,
        batch_id=args.batch_id if not args.all_remaining else None,
        limit_n=args.limit_n
    )

    if not remaining_ids:
        print("[resume] Gönderilecek remaining kayıt yok.")
        return

    print(f"[resume] havuz büyüklüğü: {len(remaining_ids)} id")

    system_prompt = load_system_prompt(args.prompt)
    want: Set[str] = set(remaining_ids)
    sel: Dict[str, str] = {}

    for obj in _iter_records_any(input_path, encoding="utf-8-sig"):
        if not want:
            break
        _id = str(obj.get(args.id_field))
        if _id in want:
            text = (
                obj.get(args.text_field)
                or obj.get("karar_metni")
                or obj.get("Karar Metni")
                or obj.get("content")
                or ""
            )
            sel[_id] = text
            want.remove(_id)

    if not sel:
        sys.exit("[resume] remaining kayıtlar girdide bulunamadı.")

    ids_text_pairs = list(sel.items())  # [(id, text), ...]
    n = len(ids_text_pairs)
    chunk_size = max(1, int(args.chunk_size))
    split = max(1, ceil(n / chunk_size))

    parts = _write_tasks_chunked(
        pairs=ids_text_pairs,
        out_dir=debug_dir,
        system_prompt=system_prompt,
        model=args.model,
        split=split,
        max_bytes=int(args.max_bytes)
    )
    print(f"[resume] {n} remaining kayıt, {len(parts)} yeni parça (≈{chunk_size}/parça)")

    results_path = out_dir / "02_extract_llm.jsonl"

    for idx, (path, ids) in enumerate(parts, 1):
        print(f"[resume] ({idx}/{len(parts)}) gönderiliyor: {path.name} (kayıt={len(ids)})")
        up = client.files.create(file=open(path, "rb"), purpose="batch")
        job = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions", completion_window="24h")

        append_lines(batch_id_path, [job.id])
        append_lines(submitted_path, ids)

        new_remaining_path = debug_dir / f"remaining_ids_{job.id}.txt"
        write_lines_atomic(new_remaining_path, ids)

        last_status = None
        while True:
            job = client.batches.retrieve(job.id)
            status = getattr(job, "status", "unknown")
            if status != last_status:
                print(f"[resume] batch {job.id} status={status}")
                last_status = status
            if status in ("completed", "failed", "expired", "canceled"):
                break
            time.sleep(args.check_interval)

        new_completed: Set[str] = set()
        new_failed: Set[str] = set()

        jsonl_buffer = []
        if getattr(job, "output_file_id", None):
            text = client.files.content(job.output_file_id).text
            for ln in text.strip().splitlines():
                _id, data, err = parse_batch_result_line(ln)
                if _id and not err:
                    jsonl_buffer.append(json.dumps({"Id": _id, "output": data}, ensure_ascii=False))
                    new_completed.add(_id)
                elif _id:
                    new_failed.add(_id)

        if jsonl_buffer:
            append_jsonl_atomic(results_path, jsonl_buffer)

        if getattr(job, "error_file_id", None):
            etext = client.files.content(job.error_file_id).text
            for ln in etext.strip().splitlines():
                try:
                    o = json.loads(ln)
                    cid = o.get("custom_id")
                    if cid:
                        new_failed.add(cid)
                except Exception:
                    pass

        done_path = debug_dir / "done_ids.txt"
        if new_completed:
            di = set(read_lines(done_path))
            di |= new_completed
            write_lines_atomic(done_path, sorted(di))

        submitted_ids_for_this_batch = set(read_lines(new_remaining_path))
        remaining_now = sorted(list(submitted_ids_for_this_batch - new_completed))
        write_lines_atomic(new_remaining_path, remaining_now)

        print(json.dumps({
            "batch_id": job.id,
            "status": getattr(job, "status", "unknown"),
            "completed_added": len(new_completed),
            "failed_added": len(new_failed),
            "remaining_now": len(remaining_now)
        }, ensure_ascii=False, indent=2))

    print("[resume] tüm remaining parçaları sırayla yeniden gönderildi ve toplandı.")

def main():
    """Komut satırı arayüzünü başlatır ve ilgili komutu çalıştırır (submit-serial, resume)."""
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--in", dest="inp", type=Path, default=Path("data/interim/kararlar_segment.jsonl"),
                        help="Girdi JSONL/JSON (vars: data/interim/kararlar_segment.jsonl)")
    common.add_argument("--prompt", type=Path, default=Path("src/llm/prompts/extract_system.md"),
                        help="System prompt (vars: src/llm/prompts/extract_system.md)")
    common.add_argument("--model", default="gpt-4o-mini", help="Model (vars: gpt-4o-mini)")
    common.add_argument("--id-field", default="Id", help="Girdi Id alanı (vars: 'Id')")
    common.add_argument("--text-field", default="Karar Metni", help="LLM'e gidecek metin alanı (vars: 'Karar Metni')")

    # submit-serial
    p_sserial = sub.add_parser("submit-serial", parents=[common],
                               help="Parçaları sırayla gönderir; her parça tamamlanınca sonucu yazar ve sonra sıradakine geçer")
    p_sserial.add_argument("--limit", type=int, default=0, help="Opsiyonel: ilk N kaydı oku")
    p_sserial.add_argument("--chunk-size", type=int, default=1000, help="Her batch dosyasına en fazla N kayıt (vars: 1000)")
    p_sserial.add_argument("--max-bytes", type=int, default=160*1024*1024, help="Her parça için ~maksimum dosya boyutu (byte)")
    p_sserial.add_argument("--check-interval", type=int, default=60, help="Durum kontrol aralığı (sn)")
    p_sserial.set_defaults(func=cmd_submit_serial)

    # resume
    p_resume = sub.add_parser("resume", parents=[common],
                              help="Kalan/fail kayıt havuzunu chunk-size ile yeniden parçalayıp seri olarak gönderir")
    p_resume.add_argument("--batch-id", help="Sadece bu batch'in remaining kayıtlarını al")
    p_resume.add_argument("--all-remaining", action="store_true", help="Tüm remaining dosyalarını birleştir")
    p_resume.add_argument("--limit-n", type=int, default=0, help="Havuzdan en fazla N kayıt al (ör: 1000)")
    p_resume.add_argument("--chunk-size", type=int, default=1000, help="Yeniden gönderimde her batch dosyasına en fazla N kayıt")
    p_resume.add_argument("--max-bytes", type=int, default=160*1024*1024, help="Her parça için ~maksimum dosya boyutu (byte)")
    p_resume.add_argument("--check-interval", type=int, default=60, help="Durum kontrol aralığı (sn)")
    p_resume.set_defaults(func=cmd_resume)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

#submit-serial
#python src/etl/02_extract_llm.py submit-serial --in data/interim/kararlar_segment.jsonl --chunk-size 1000 --max-bytes 160000000 --check-interval 60

#resume
# tek bir batch’in kalanları
#python src/etl/02_extract_llm.py resume --batch-id <FAILED_BATCH_ID> --chunk-size 1000 --max-bytes 160000000 --check-interval 60

# ya da tüm remaining havuzundan
#python src/etl/02_extract_llm.py resume --all-remaining --chunk-size 1000 --max-bytes 160000000 --check-interval 60
