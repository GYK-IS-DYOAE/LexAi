import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b-instruct"

def query_llm(system_prompt: str, user_prompt: str) -> str:
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
            "num_predict": 1024,
            "repeat_penalty": 1.1,
            "num_ctx": 8192,
            "stop": ["<|im_end|>"]
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()

    return response.json()["response"].strip()
