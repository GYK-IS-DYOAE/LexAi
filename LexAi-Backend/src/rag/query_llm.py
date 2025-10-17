import json
import requests
from typing import Optional, Sequence, Dict, Any
from src.rag.config import LLM_BASE_URL, LLM_MODEL_NAME, LLM_TIMEOUT

def _merge_opts(base: Dict[str, Any], extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not extra:
        return base
    out = base.copy()
    out.update({k: v for k, v in extra.items() if v is not None})
    return out

def _parse_ollama_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        raise

def query_llm(
    system_prompt: str,
    user_prompt: str,
    context: str = "",
    *,
    temperature: float = 0.6,
    top_p: float = 0.9,
    num_ctx: int = 8192,
    repeat_penalty: float = 1.1,
    stop: Optional[Sequence[str]] = None,
    options_override: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    retries: int = 2,
) -> str:
    full_prompt = (
        f"{system_prompt}\n\nÖNCEKİ KONU BAĞLAMI:\n{context}\n\n{user_prompt}\n\nYanıt:"
        if context else
        f"{system_prompt}\n\n{user_prompt}\n\nYanıt:"
    )

    base_opts = {
        "temperature": temperature,
        "top_p": top_p,
        "num_ctx": num_ctx,
        "repeat_penalty": repeat_penalty,
    }
    if stop:
        base_opts["stop"] = list(stop)

    payload = {
        "model": LLM_MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": _merge_opts(base_opts, options_override),
    }

    last_err = None
    for _ in range(max(1, retries)):
        try:
            resp = requests.post(
                f"{LLM_BASE_URL}/api/generate",
                json=payload,
                timeout=timeout or LLM_TIMEOUT,
            )
            resp.raise_for_status()
            data = _parse_ollama_json(resp.text)
            return (data.get("response") or "").strip()
        except Exception as e:
            last_err = e
    raise RuntimeError(f"LLM request failed: {last_err}")
