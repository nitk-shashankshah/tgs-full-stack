# Deploying the TGS backend to Azure App Service

This is a single-file FastAPI app (`main:app`) packaged for **Azure App Service (Linux, Python 3.13)**.
It runs under Gunicorn + a Uvicorn worker (see `startup.sh`).

## What was added

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (was missing). |
| `startup.sh` | Gunicorn/Uvicorn startup command for App Service. |
| `azure.yaml` | `azd` service definition. |
| `infra/` | Bicep IaC: App Service + plan, app settings, startup command, Python 3.13. |
| `.gitignore` | Keeps `.env`, venvs, and the large local input dirs out of the deploy package. |

The app's `ANTHROPIC_API_KEY` is supplied as an **App Service application setting** — never baked into the image or committed.

> ⚠️ **Rotate your API key.** A live key is currently sitting in `.env` in plaintext. `.gitignore` now excludes `.env` from deploys, but since the key has been on disk/shared you should rotate it in the Anthropic console and set the new value as the app setting below.

---

## Option A — Azure Developer CLI (`azd`), recommended

Provisions all infrastructure from `infra/` and deploys in one step.

```bash
cd /Users/shashankshah/TGS/backend

# one-time
azd auth login

# create an environment and set the secret + (optionally) the frontend origin
azd env new tgs-backend
azd env set ANTHROPIC_API_KEY "sk-ant-..."          # your rotated key
# azd env set ALLOWED_ORIGINS "https://your-frontend.example.com"
# azd env set APP_SERVICE_SKU B1                      # default; F1=free (limited), B1/S1/P1v3 for more power

# provision + deploy
azd up
```

`azd` prints the site URL when done. Verify with `<url>/health` and `<url>/docs`.

> **Note on the deploy package:** `azd` zips this folder. The large local input dirs
> (`catalogs/`, `curated/`, `price_lists/` — ~277 MB, not used at runtime) and `fastapi-quickstart/`
> are excluded via `.gitignore`. To be sure `azd` honors it, run `git init` here first
> (or just confirm those dirs are absent from the uploaded zip). The app only reads/writes `./data`.

---

## Option B — `az webapp up` (no IaC)

Simplest path; honors `.gitignore` for packaging.

```bash
cd /Users/shashankshah/TGS/backend
az login

az webapp up \
  --name tgs-backend-<unique> \
  --runtime "PYTHON:3.13" \
  --sku B1 \
  --location eastus

# startup command + secrets
az webapp config set \
  --name tgs-backend-<unique> --resource-group <rg-from-output> \
  --startup-file "bash startup.sh"

az webapp config appsettings set \
  --name tgs-backend-<unique> --resource-group <rg-from-output> \
  --settings ANTHROPIC_API_KEY="sk-ant-..." \
             SCM_DO_BUILD_DURING_DEPLOYMENT=true \
             WEBSITES_CONTAINER_START_TIME_LIMIT=600
# optional: ALLOWED_ORIGINS="https://your-frontend.example.com"
```

---

## Runtime notes

- **Health check:** `GET /health`. API docs at `/docs`.
- **CORS:** localhost Vite ports are allowed by default. Add your deployed frontend with the
  `ALLOWED_ORIGINS` app setting (comma-separated).
- **Data persistence:** the app stores catalogs/price-lists as JSON under `./data`, which resolves to
  `/home/site/wwwroot/data` on App Service — backed by the persistent `/home` share, so it survives
  restarts. For multi-instance scale-out or durability, move this to Azure Blob Storage later.
- **SKU sizing:** PDF rendering (pypdfium2/Pillow) + Anthropic calls are memory- and time-heavy.
  B1 (1.75 GB) is a reasonable start. F1 (Free) has no Always On and tight CPU quotas — fine only for
  light testing. The Gunicorn `--timeout 600` accommodates long catalog-processing requests.
