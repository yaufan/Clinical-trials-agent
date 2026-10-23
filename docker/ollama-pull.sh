#!/usr/bin/env sh
# One-shot helper: pull the LLM and embedding models into the Ollama service.
# Usage (inside the compose network): OLLAMA_HOST=http://ollama:11434 sh ollama-pull.sh qwen3:32b bge-m3
set -eu
HOST="${OLLAMA_HOST:-http://ollama:11434}"
for m in "$@"; do
  echo ">> pulling $m"
  curl -sS -X POST "$HOST/api/pull" -d "{\"name\": \"$m\", \"stream\": false}" | head -c 400; echo
done
echo ">> models now available:"
curl -sS "$HOST/api/tags"
