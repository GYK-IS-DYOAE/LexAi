# src/rag/query_llm.py

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b-instruct"

def query_llm(system_prompt: str, user_prompt: str) -> dict:
    full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n" \
                  f"<|im_start|>user\n{user_prompt}<|im_end|>\n" \
                  f"<|im_start|>assistant\n"

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50,
            "stop": ["<|im_end|>"]
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()

    output = response.json()["response"]

    try:
        return eval(output.strip())  # Eğer string JSON değilse
    except Exception as e:
        raise ValueError(f"Model çıktısı parse edilemedi: {output}") from e
