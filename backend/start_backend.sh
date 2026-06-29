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

echo "Starting backend on http://localhost:8000"
python3 -m uvicorn main:app --port 8000 --reload
