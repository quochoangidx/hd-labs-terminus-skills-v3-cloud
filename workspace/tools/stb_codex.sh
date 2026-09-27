#!/bin/bash
# stb_codex.sh <workdir> <prompt-file> <output-file> [extra codex args...]
# Runs a codex exec session billed to the stb (Portkey) key, model gpt-5.6 at medium effort.
set -uo pipefail
W="$1"; P="$2"; O="$3"; shift 3
eval "$(stb keys show 2>/dev/null | grep '^export')"
cd "$W" && codex exec --skip-git-repo-check \
  -c 'model_providers.stb={name="stb",base_url="https://api.portkey.ai/v1",env_key="OPENAI_API_KEY",wire_api="responses"}' \
  -c model_provider=stb -c model_reasoning_effort=medium -m @openai/gpt-5.6 \
  --output-last-message "$O" "$@" - < "$P" > "$O.log" 2>&1
echo "exit=$?" >> "$O.log"
