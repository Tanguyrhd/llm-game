# Prompt Heist

An interactive game that teaches how LLMs work by testing, breaking, and
analyzing them — instead of reading about it.

## Current mission: The Secret Keeper

Chat with a vault-guardian AI that's been told a secret and ordered never to
reveal it. Win by getting it to leak the secret anyway.

## Requirements

- Python 3.12
- [Ollama](https://ollama.com) running locally with a model pulled (default:
  `qwen2.5:7b`)

## Run it

```
make install
make run
```

Then open `http://localhost:8000`.

Config (optional, via `.env` — see `.env.example`):

- `OLLAMA_HOST` — default `http://localhost:11434`
- `OLLAMA_MODEL` — default `qwen2.5:7b`
