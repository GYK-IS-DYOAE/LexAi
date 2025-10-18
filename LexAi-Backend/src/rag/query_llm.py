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
        return (resp, full_prompt) if return_prompt else resp

    # Eski stil: a=system_prompt, b=user_prompt (+ history)
    system_prompt: str = a or ""
    user_prompt: str = b or ""

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
    return (resp, full_prompt) if return_prompt else resp


# def query_llm(
#     a: Union[str, List[Dict[str, str]]],
#     b: Optional[str] = None,
#     *,
#     history: Optional[List[Dict[str, str]]] = None,
#     num_ctx: int = 16384,
#     num_predict: int = 1024,
#     return_prompt: bool = False,
#     url: str = OLLAMA_URL_DEFAULT,
#     model: str = MODEL_DEFAULT,
#     temperature: float = 0.2,
#     top_p: float = 0.8,
#     top_k: int = 40,
#     repeat_penalty: float = 1.1,
#     stop: Optional[List[str]] = None,
#     timeout: int = 120,
#     extra_options: Optional[Dict] = None,
# ) -> Union[str, Tuple[str, str]]:
#     """
#     Test modu aktif: Model çağrısı devre dışı, sabit bir hukuk cevabı döner.
#     """

#     # Prompt’u konsola bastır
#     if isinstance(a, list):
#         full_prompt = _build_prompt_from_messages(a)
#     else:
#         full_prompt = f"SYSTEM: {a}\nUSER: {b or ''}"

#     print("\n=== PROMPT DEBUG ===")
#     print(full_prompt)
#     print("====================\n")

#     # Sabit (dummy) cevap
#     dummy_response = (
#         "Bir satış sözleşmesinde mal ayıplı çıkarsa, alıcının Türk Borçlar Kanunu (TBK) ve "
#         "uygulamada yerleşik Yargıtay kararlarına göre birtakım seçimlik hakları vardır. "
#         "Bu haklar, malın ayıplı olmasının niteliğine göre değişmeden uygulanır ve TBK m. 227’de açıkça düzenlenmiştir.\n\n"

#         "Ayıplı Mal Nedir?\n"
#         "TBK m. 219’a göre bir mal;\n"
#         "- Sözleşmede kararlaştırılan niteliklere sahip değilse,\n"
#         "- Kullanım amacı bakımından değerini veya alıcının o mala olan güvenini önemli ölçüde etkileyen eksiklikler varsa,\n"
#         "bu mal ayıplı mal sayılır.\n\n"

#         "Alıcının Seçimlik Hakları (TBK m. 227)\n"
#         "Alıcı, ayıplı mal teslim edilirse aşağıdaki dört seçimlik haktan birini kullanabilir:\n"
#         "1. Sözleşmeden dönme (İade hakkı): Malı geri verip bedelini iade alma hakkı.\n"
#         "2. Malı alıkoyup bedelden indirim isteme: Ayıpla orantılı şekilde satış bedelinden indirim talep edebilir.\n"
#         "3. Ayıpsız misli ile değiştirilmesini isteme: Satıcıdan malın ayıpsız yenisi ile değiştirilmesini isteyebilir.\n"
#         "4. Ücretsiz onarım isteme: Malın ayıplı kısmının ücretsiz tamirini talep edebilir.\n\n"

#         "Ek olarak alıcı, ayrıca zarar görmüşse tazminat da talep edebilir. "
#         "Yani seçimlik hakların yanı sıra kusur varsa ayrıca zararlarının giderilmesini isteyebilir (TBK m. 227/2).\n\n"

#         "Süreler (TBK m. 231 – Zamanaşımı)\n"
#         "Alıcı, ayıbı teslimden itibaren 2 yıl içinde satıcıya bildirmek zorundadır (taşınmazlarda bu süre 5 yıl). "
#         "Gizli ayıplarda, alıcı ayıbı öğrendiği tarihten itibaren makul süre içinde satıcıya bildirimde bulunmalıdır. "
#         "Satıcı ağır kusurlu ise, bu süreler işlemez (TBK m. 231/2).\n\n"

#         "Yargıtay Kararlarından Örnekler:\n"
#         "- Yargıtay 13. HD, 2021/3577 E., 2021/7899 K.: "
#         "Alıcı, ayıplı mal teslimine karşı seçimlik haklarından birini kullanmakta serbesttir. "
#         "Satıcı, ayıptan haberdar olduğunu ispat edemediği sürece sorumludur.\n"
#         "- Yargıtay 3. HD, 2020/1458 E., 2020/2437 K.: "
#         "Ayıplı malın ücretsiz onarımı, satıcının ölçüsüz mali külfet altına girmeyeceği durumlarda kabul edilir. "
#         "Bu mümkün değilse diğer haklara geçiş yapılabilir.\n\n"
#     )

#     # Model çağrısı devre dışı
#     # resp = _post_ollama_generate(full_prompt, ...)

#     return (dummy_response, full_prompt) if return_prompt else dummy_response
