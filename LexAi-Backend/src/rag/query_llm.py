import re
import requests
from typing import List, Dict, Optional, Union, Tuple

# Varsayılanlar (gerekirse config’ten enjekte edebilirsin)
OLLAMA_URL_DEFAULT = "http://localhost:11434/api/generate"
MODEL_DEFAULT = "qwen2.5:7b-instruct"


def _build_prompt_from_messages(messages: List[Dict[str, str]]) -> str:
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
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


def _post_ollama_generate(
    full_prompt: str,
    *,
    url: str = OLLAMA_URL_DEFAULT,
    model: str = MODEL_DEFAULT,
    num_ctx: int = 16384,
    num_predict: int = 1024,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
    repeat_penalty: float = 1.1,
    stop: Optional[List[str]] = None,
    timeout: int = 120,
    extra_options: Optional[Dict] = None,
) -> str:
    opts = {
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "num_predict": num_predict,
        "repeat_penalty": repeat_penalty,
        "num_ctx": num_ctx,
        "stop": stop or ["<|im_end|>"],
    }
    if extra_options:
        opts.update(extra_options)

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": opts,
    }

    r = requests.post(url, json=payload, timeout=timeout)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        # Sunucunun geri döndürdüğü body içindeki hata mesajını mümkünse ilet
        detail = ""
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise RuntimeError(f"Ollama generate error: {e}\nDetail: {detail}") from e

    try:
        data = r.json()
    except ValueError:
        # Bazı modeller satır-satır JSON döndürebilir; son satırı dene
        txt = (r.text or "").strip()
        last = txt.split("\n")[-1] if "\n" in txt else txt
        data = requests.utils.json.loads(last)

    return (data.get("response") or "").strip()


# --- Gereksiz kalıpları temizleyen yardımcı fonksiyon ---
def clean_response(text: str) -> str:
    if not text:
        return text
    # Baştaki yapay şablonları sil
    banned_prefixes = [
        "Cevap", "Yanıt", "Sonuç", "Örnek", "Senin sorunun cevabı",
        "Bu durumda", "Kullanıcıya bilgi", "Kullanıcıyı bilgilendirmek"
    ]
    for p in banned_prefixes:
        if text.strip().lower().startswith(p.lower()):
            text = text.split(":", 1)[-1].strip()
    # “Sonuç:” sonrası tekrarları at
    text = re.sub(r"(Sonuç|Kullanıcıyı bilgilendirmek).*", "", text, flags=re.I)
    # Fazla boşlukları toparla
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def query_llm(
    a: Union[str, List[Dict[str, str]]],
    b: Optional[str] = None,
    *,
    history: Optional[List[Dict[str, str]]] = None,
    num_ctx: int = 16384,
    num_predict: int = 1024,
    return_prompt: bool = False,
    # Aşağıdakiler isteğe bağlı override’lar
    url: str = OLLAMA_URL_DEFAULT,
    model: str = MODEL_DEFAULT,
    temperature: float = 0.2,
    top_p: float = 0.8,
    top_k: int = 40,
    repeat_penalty: float = 1.1,
    stop: Optional[List[str]] = None,
    timeout: int = 120,
    extra_options: Optional[Dict] = None,
) -> Union[str, Tuple[str, str]]:
    """
    Kullanımlar:
      1) query_llm(messages=[...], return_prompt=True)
      2) query_llm(system_prompt, user_prompt, history=[...], return_prompt=True)
    return_prompt=True -> (response, full_prompt)
    return_prompt=False -> "response"
    """

    # Yeni stil: messages listesi
    if isinstance(a, list):
        messages = a
        full_prompt = _build_prompt_from_messages(messages)
        resp = _post_ollama_generate(
            full_prompt,
            url=url, model=model,
            num_ctx=num_ctx, num_predict=num_predict,
            temperature=temperature, top_p=top_p, top_k=top_k,
            repeat_penalty=repeat_penalty, stop=stop,
            timeout=timeout, extra_options=extra_options,
        )
        resp = clean_response(resp)
        return (resp, full_prompt) if return_prompt else resp

    # Eski stil: a=system_prompt, b=user_prompt (+ history)
    system_prompt: str = a or ""
    user_prompt: str = b or ""

    # --- bağlamlı yanıt için yönlendirme ---
    if history:
        user_prompt += (
            "\n\nYukarıdaki konuşmaları dikkate alarak, yeni soruya bağlamı koruyan, "
            "neden-sonuç ilişkisi kuran, çıkarım içeren ve tekrarsız bir hukuki açıklama üret."
        )

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if history:
        for turn in history:
            r = turn.get("role")
            c = turn.get("content", "")
            if r in ("user", "assistant", "system") and c:
                messages.append({"role": r, "content": c})

    messages.append({"role": "user", "content": user_prompt})

    full_prompt = _build_prompt_from_messages(messages)

    print("\n=== PROMPT DEBUG ===")
    print(full_prompt)
    print("====================\n")

    resp = _post_ollama_generate(
        full_prompt,
        url=url, model=model,
        num_ctx=num_ctx, num_predict=num_predict,
        temperature=temperature, top_p=top_p, top_k=top_k,
        repeat_penalty=repeat_penalty, stop=stop,
        timeout=timeout, extra_options=extra_options,
    )

    # --- Gereksiz kalıpları temizle ---
    resp = clean_response(resp)

    return (resp, full_prompt) if return_prompt else resp
