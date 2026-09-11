#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PORT="${PORT:-8000}"

while getopts "p:h" opt; do
  case "$opt" in
    p) PORT="$OPTARG" ;;
    h) echo "Usage: $0 [-p port]"; exit 0 ;;
    *) echo "Usage: $0 [-p port]"; exit 1 ;;
  esac
done

cd "$PROJECT_DIR"
exec uvicorn src.api.chat_sse:app --host 0.0.0.0 --port "$PORT"
