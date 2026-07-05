#!/bin/bash
cd "$(dirname "$0")"

if [ -z "$ANTHROPIC_API_KEY" ]; then
  if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
  else
    echo "ERROR: ANTHROPIC_API_KEY is not set."
    echo "Either:"
    echo "  1. Create a .env file with: ANTHROPIC_API_KEY=sk-ant-..."
    echo "  2. Or run: ANTHROPIC_API_KEY=sk-ant-... ./start_backend.sh"
    exit 1
  fi
fi

# .env ships with placeholder DB/storage values until real infra is provisioned —
# fall back to a local SQLite file and on-disk uploads so local dev isn't blocked.
if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"your-azure-host"* ]]; then
  echo "WARNING: DATABASE_URL is unset or a placeholder — using local SQLite (./dev.db)."
  export DATABASE_URL="sqlite:///./dev.db"
fi
if [ -z "$AZURE_STORAGE_CONNECTION_STRING" ] || [[ "$AZURE_STORAGE_CONNECTION_STRING" == *"AccountName=xxx"* ]]; then
  echo "WARNING: AZURE_STORAGE_CONNECTION_STRING is unset or a placeholder — uploads will be saved locally."
  export AZURE_STORAGE_CONNECTION_STRING="fake"
fi

echo "Starting backend on http://localhost:8000"
python3 -m uvicorn main_v2:app --port 8000 --reload
