# Changelog

Alle wesentlichen Änderungen an Poll-Position.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung: [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt

- Vercel Services-Deployment (`vercel.json`): ein Projekt mit Next.js (`web/`) + FastAPI (`backend/`)
- FastAPI-Backend `backend/` (Vercel-Entrypoint `backend.main:app`) mit JSON-API
- Next.js-Frontend `web/` (App Router, Tailwind, Recharts)
- Deploy-Doku `docs/vercel-deploy.md` inkl. MotherDuck Marketplace (`MOTHERDUCK_TOKEN`)
- MotherDuck-Unterstützung für Silver/Gold (`MOTHERDUCK_TOKEN` / `MOTHERDUCK_DATABASE`)
- Streamlit-Multi-Page-App unter `app/` (Bund, Länder, Europa, Institute, Was-wäre-wenn)
- Tägliche GitHub-Action `.github/workflows/daily-pipeline.yml` für `python -m data_pipeline.run`
- CI-Workflow `.github/workflows/ci.yml` (pytest)
- Cron-Hilfsskript `scripts/cron-pipeline.sh`
- Offline-Integrationstest `tests/integration/test_pipeline_e2e.py`
  (Bronze → Silver → Gold → Sitze → Koalitionen)
- Explizite Lizenz- und Nutzungsdokumentation in der README

### Geändert

- `data_pipeline.run` beendet sich bei Fehlern mit Exit-Code 1 und klarer Exception-Logzeile

## [0.1.0] — 2026-08-23

### Hinzugefügt

- Datenpipeline Bronze/Silver/Gold (Dawum, Wikipedia-Polls)
- Analyse: Durchschnitte, Sitzzuteilung, Koalitionen, Unsicherheit, House Effects,
  Parteienfamilien, Was-wäre-wenn-Szenarien
- Wahlrechts-Regressionstests gegen bekannte Ergebnisse
- Projektregeln in `AGENTS.md` / `.cursorrules`
