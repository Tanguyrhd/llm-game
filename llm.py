import json
import os
from collections.abc import Iterator

import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

TIMEOUT = httpx.Timeout(connect=5.0, read=150.0, write=10.0, pool=5.0)


class OllamaError(Exception):
    pass


def _payload(messages: list[dict], stream: bool) -> dict:
    return {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": stream,
        "keep_alive": -1,
        "options": {"num_predict": 300},
    }


def ask_llm(messages: list[dict]) -> str:
    try:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json=_payload(messages, stream=False),
            timeout=TIMEOUT,
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


def stream_llm(messages: list[dict]) -> Iterator[str]:
    try:
        with httpx.stream(
            "POST",
            f"{OLLAMA_HOST}/api/chat",
            json=_payload(messages, stream=True),
            timeout=TIMEOUT,
        ) as resp:
            if resp.status_code != 200:
                raise OllamaError(f"Ollama error: {resp.read().decode()}")
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break
    except httpx.ConnectError as e:
        raise OllamaError(
            "Could not reach the local Ollama server. Is it running (`ollama serve`)?"
        ) from e
    except httpx.TimeoutException as e:
        raise OllamaError("The model took too long to respond.") from e
