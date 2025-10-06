"""
engine_ollama.py
----------------
Ollama üzerinden Qwen 2.5 7B Instruct'a istek atar.
- Chat API (httpx) kullanır
- Sıkı sistem prompt + 'sadece JSON' şartı
- Güvenlik için temperature düşük (0.2)
"""

import json
import httpx
from typing import Dict
from src.retrieval.config import OLLAMA_HOST, OLLAMA_MODEL

def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> Dict:
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        },
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ]
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    # Ollama yanıtı
    text = data.get("message", {}).get("content", "").strip()
    # Beklediğimiz: yalnızca JSON
    return json.loads(text)
