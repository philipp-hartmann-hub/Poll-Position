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
2. Env: `MOTHERDUCK_TOKEN` (automatisch), optional `MOTHERDUCK_DATABASE=poll_position`  
3. Daily Pipeline: dieselben Werte als **GitHub Actions Secrets** (siehe README)

## Bundle

Config-YAMLs unter `data_pipeline/config/` und `data_pipeline/reference/` müssen im
Python-Bundle liegen → deshalb API-`root: "./"` (nicht nur `backend/`).
`excludeFiles` entfernt Frontend/Tests aus dem Function-Bundle.

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
