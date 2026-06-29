#!/bin/bash
# Azure App Service (Linux) startup command.
# Gunicorn with a Uvicorn worker so FastAPI runs as ASGI.
# Long timeout because catalog/price-list processing makes synchronous
# Anthropic + PDF-rendering calls that can take a while.
gunicorn main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 600 \
  --bind 0.0.0.0:8000
