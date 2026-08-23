# Deployment auf Vercel (ein Projekt: Next.js + FastAPI)

## Architektur

| Service | Root | Rolle |
| --- | --- | --- |
| `web` | `web/` | Next.js App Router (Frontend) |
| `api` | `.` (Repo-Root) | FastAPI (`backend.main:app`), importiert `analysis/` + `data_pipeline/` |

Routing in `vercel.json` via **Vercel Services** (empfohlen für Polyglot-Monorepos):

- `/api/*`, `/health`, `/docs` → Python-Service
- alles andere → Next.js

Lokal: `npm run vercel:dev` (= `vercel dev -L`) oder getrennt `npm run dev:web` + `npm run dev:api`.

## Vercel-Dashboard (einmalig)

1. **Import** des Git-Repos als **ein** Vercel-Projekt.
2. **Root Directory:** leer / Repository-Root (nicht `web/` — Services übernehmen die Aufteilung).
3. **Framework Preset:** wird pro Service gesetzt (`vercel.json` → `services.web.framework: nextjs`, `services.api.framework: fastapi`).
4. Kein separates zweites Projekt nötig.

> **Hinweis:** Nur `web/` als Root Directory + Root-`requirements.txt` reicht **nicht** —
> dann fehlen `analysis/`/`data_pipeline/` für die Python-Function. Entweder Services
> (wie hier) oder ein explizites Monorepo-Setup mit Repo-Root.

## MotherDuck (Marketplace)

1. [MotherDuck for Vercel](https://vercel.com/marketplace/motherduck) → **Install** für dieses Projekt.
2. Die Integration setzt automatisch:
   - `MOTHERDUCK_TOKEN` (read-write) — **passt zu `data_pipeline/warehouse.py`**
   - `MOTHERDUCK_READONLY_TOKEN` (read-only, optional für reine Lese-API)
3. Optional manuell: `MOTHERDUCK_DATABASE=poll_position` (Default in Code).
4. Prüfen unter **Project Settings → Environment Variables** (Production + Preview).

Daily Pipeline (GitHub Actions) braucht denselben Token als **Repository Secret**
`MOTHERDUCK_TOKEN` (optional Secret `MOTHERDUCK_DATABASE`) — siehe README-Abschnitt
*GitHub Actions Secrets*. Token nie ins Repo oder in eine getrackte `.env` legen.

## Bundle / Config-YAMLs

Die API lädt zur Laufzeit u. a.:

- `data_pipeline/config/*.yaml`
- `data_pipeline/reference/*.yaml`

Pfade sind relativ zu den Python-Modulen (`Path(__file__).parents[…]`). Der Python-Service
bundelt standardmäßig erreichbare Projektdateien; `excludeFiles` in `vercel.json` schließt
`web/`, `tests/`, Streamlit-`app/` etc. aus.

## Verifizierung

```bash
# CLI ≥ 48.1.8 (FastAPI-Preset)
npx vercel --version

# Lokal (ohne Vercel-Login)
npm run vercel:dev

# API über den gemeinsamen Dev-Server
curl http://localhost:3000/api/parliaments
curl http://localhost:3000/health
```

OpenAPI: `/docs` (über denselben Host wie das Frontend).

## Alternative (legacy, ohne Services)

Falls Services im Dashboard noch nicht verfügbar ist, funktioniert theoretisch:

```json
{
  "functions": { "backend/main.py": { "maxDuration": 30 } },
  "rewrites": [{ "source": "/api/:path*", "destination": "/backend/main.py" }]
}
```

— erfordert aber Root Directory = Repo-Root **und** manuelles Next.js-Build-Command für `web/`.
Services ist der unterstützte Weg (siehe [Vercel Services](https://vercel.com/docs/services)).
