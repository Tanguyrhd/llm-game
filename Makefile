.PHONY: install run check-ollama clean

# Uses `pyenv exec`, which reads .python-version and runs inside the
# llm_game virtualenv without needing it activated in the shell.
PY := pyenv exec python
PIP := pyenv exec pip

install:
	$(PIP) install -r requirements.txt

run:
	pyenv exec uvicorn main:app --reload --port 8000

check-ollama:
	curl -sf http://localhost:11434/api/tags | $(PY) -m json.tool

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
