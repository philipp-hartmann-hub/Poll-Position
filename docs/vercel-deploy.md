# Deployment auf Vercel (ein Projekt: Next.js + FastAPI via Services)

## Pflicht im Dashboard (häufigster Deploy-Fehler)

Ein Projekt baut **nur dann** als Services, wenn **beides** gilt
([Vercel Docs](https://vercel.com/kb/guide/vercel-services#troubleshooting)):

1. **Settings → Build and Deployment → Framework Preset = `Services`**
2. `vercel.json` enthält den Key `"services"`

Fehlt (1), ignoriert Vercel unsere Multi-Service-Config und fällt auf
Ein-Framework-Erkennung zurück → typisch *No python entrypoint* oder Next-only-Build.

Weitere Checks:

| Einstellung | Wert |
| --- | --- |
| **Root Directory** | leer / Repository-Root (**nicht** `web/`) |
| **Framework Preset** | **Services** |
| **Node.js Version** | 20.x oder 22.x (für `web/`) |

Nach Änderung: **Redeploy** (ohne Cache, falls der erste Build noch mit altem Preset lief).

## Architektur

| Service | Root | Rolle |
| --- | --- | --- |
| `web` | `web/` | Next.js App Router |
| `api` | `./` (Repo-Root) | FastAPI `backend.main:app` + `analysis/` + `data_pipeline/` |

Routing (`vercel.json`):

- `/api/*`, `/health`, `/docs`, … → Service `api`
- alles andere → Service `web`

Der API-Service behält den Originalpfad (`/api/parliaments` bleibt `/api/parliaments`).

Lokal:

```bash
npm run vercel:dev          # vercel dev -L
# oder getrennt:
npm run dev:api             # :8000
npm run dev:web             # :3000, proxied /api → :8000
```

## MotherDuck

1. [Marketplace → MotherDuck](https://vercel.com/marketplace/motherduck) installieren  
2. Env (automatisch): `MOTHERDUCK_TOKEN`, `MOTHERDUCK_READONLY_TOKEN`  
3. Optional manuell: `MOTHERDUCK_DATABASE=poll_position` (Production + Preview)  
4. **Daten füllen:** Marketplace allein legt nur Tokens an. Silver/Gold kommen erst nach
   Pipeline-Lauf mit demselben Token:
   - GitHub → Actions → *Daily Pipeline* → Run workflow  
     (Secrets `MOTHERDUCK_TOKEN` + optional `MOTHERDUCK_DATABASE`)  
   - oder lokal: `MOTHERDUCK_TOKEN=… uv run python -m data_pipeline.run`
5. Diagnose: `GET /health` → `motherduck_configured`, `surveys`, ggf. `hint`/`error`

Auf Vercel setzt der Code `saas_mode=true` und `HOME=/tmp` (DuckDB-Extensions).
Kein `attach_mode=single` — der verhindert den Workspace-Bootstrap (`md:`).

## Bundle

Config-YAMLs unter `data_pipeline/config/` und `data_pipeline/reference/` müssen im
Python-Bundle liegen → deshalb API-`root: "./"` (nicht nur `backend/`).
`excludeFiles` entfernt Frontend/Tests aus dem Function-Bundle.

In `pyproject.toml` steht `[tool.uv] package = false`, damit Vercel bei
`uv sync --frozen --no-editable` **kein Hatchling-Wheel** des Monorepos bauen muss
(das schlug fehl, sobald Nebenordner wie `.cursor` mitgepackt wurden). Imports laufen
über den Quellbaum im Deployment. Streamlit/Plotly liegen unter optionalem Extra `ui`
und werden auf Vercel nicht installiert.

## Verifizierung nach Deploy

```bash
curl https://<dein-deployment>/health
curl https://<dein-deployment>/api/parliaments
# OpenAPI
open https://<dein-deployment>/docs
```

## Wenn Services im Account nicht wählbar ist

Framework **Services** ist Beta auf allen Plänen, muss aber im Projekt explizit
gesetzt sein. Ist das Preset nicht sichtbar: Vercel-Support/Docs prüfen oder
**zwei Projekte** (Fallback):

1. Projekt A — Root Directory `web/` → Next.js; Env `NEXT_PUBLIC_API_BASE=https://…-api.vercel.app`
2. Projekt B — Root Directory `.` → Framework FastAPI / Entrypoint `backend.main:app`

Einzelprojekt mit Services bleibt der empfohlene Weg.
