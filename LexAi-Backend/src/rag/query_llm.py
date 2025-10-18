import requests
from typing import List, Dict, Optional, Union

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b-instruct"

def _build_prompt_from_messages(messages: List[Dict[str, str]]) -> str:
    """
    Ollama /api/generate için 'prompt' (tek string) oluşturur.
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            parts.append(f"<|im_start|>system\n{content}<|im_end|>")
        elif role == "assistant":
            parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
        else:
            parts.append(f"<|im_start|>user\n{content}<|im_end|>")
    parts.append("<|im_start|>assistant\n")  # assistant turn'u başlat
    return "\n".join(parts)

def _post_ollama_generate(full_prompt: str,
                          num_ctx: int = 16384,
                          num_predict: int = 1024) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50,
            "num_predict": num_predict,
            "repeat_penalty": 1.1,
            "num_ctx": num_ctx,
            "stop": ["<|im_end|>"],
        },
    }
    resp = requests.post(OLLAMA_URL, json=payload)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()

def query_llm(
    a: Union[str, List[Dict[str, str]]],
    b: Optional[str] = None,
    *,
    history: Optional[List[Dict[str, str]]] = None,
    num_ctx: int = 16384,
    num_predict: int = 1024,
) -> str:
    """
    Geri uyumlu arayüz:

    1) Eski kullanım:
       query_llm(system_prompt: str, user_prompt: str, history: Optional[List[Dict]] = None, ...)

    2) Yeni kullanım (mesaj listesi):
       query_llm(messages: List[{"role": "...", "content": "..."}], num_ctx=..., num_predict=...)

    Her iki durumda da /api/generate ile tek 'prompt' stringi gönderilir.
    """
    # Yeni stil: ilk argüman messages listesi ise doğrudan kullan
    if isinstance(a, list):
        messages = a
        full_prompt = _build_prompt_from_messages(messages)
        return _post_ollama_generate(full_prompt, num_ctx=num_ctx, num_predict=num_predict)

    # Eski stil: a=system_prompt, b=user_prompt
    system_prompt: str = a or ""
    user_prompt: str = b or ""

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # history varsa ekle (en fazla son 6 tur gibi bir kısıt üst katmanda yapılabilir)
    if history:
        for turn in history:
            r = turn.get("role")
            c = turn.get("content", "")
            if r in ("user", "assistant", "system") and c:
                messages.append({"role": r, "content": c})

    messages.append({"role": "user", "content": user_prompt})

    full_prompt = _build_prompt_from_messages(messages)
    return _post_ollama_generate(full_prompt, num_ctx=num_ctx, num_predict=num_predict)
