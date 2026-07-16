import os

import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


class OllamaError(Exception):
    pass


def ask_llm(messages: list[dict]) -> str:
    try:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
        )
    except httpx.ConnectError as e:
        raise OllamaError(
            "Could not reach the local Ollama server. Is it running (`ollama serve`)?"
        ) from e
    except httpx.TimeoutException as e:
        raise OllamaError("The model took too long to respond.") from e

    if resp.status_code != 200:
        raise OllamaError(f"Ollama error: {resp.text}")

    return resp.json()["message"]["content"]
