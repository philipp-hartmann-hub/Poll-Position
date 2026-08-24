# Poll-Position

Umfragetracker für Deutschland und Europa.

Ziel: Umfragen aus **Dawum** und paneuropäischen Quellen zusammenführen, daraus
**Sitzverteilung** und **Koalitionsszenarien** berechnen. Die Analyse-Logik liegt
UI-frei in `analysis/` und wird mit pytest abgesichert.

> Manuelle Abschnitte (dieser Intro und die Architektur/Start-Anleitung) bleiben erhalten.
> Alles zwischen `AUTO:START` / `AUTO:END` wird automatisch überschrieben.

## Datenarchitektur (Bronze / Silver / Gold)

| Layer | Ort | Inhalt |
| --- | --- | --- |
| **Bronze** | `data/raw/<quelle>/<YYYY-MM-DD>.parquet` | Roh-Snapshots je Quelle und Abrufdatum (Dawum: unveränderte JSON-Antwort); lokal/CI, **nicht** MotherDuck |
| **Silver** | DuckDB lokal (`data/warehouse.duckdb`) **oder** MotherDuck (`md:$MOTHERDUCK_DATABASE`) | `parliaments`, `parties`, `institutes`, `surveys`, `survey_results` |
| **Gold** | dieselbe DuckDB-/MotherDuck-Instanz | `party_averages`, `party_trends` |

Silver/Gold steuern über Env: mit gesetztem `MOTHERDUCK_TOKEN` schreibt/liest die Pipeline gegen MotherDuck
(Default-DB `poll_position` via `MOTHERDUCK_DATABASE`); ohne Token bleibt das bisherige lokale Verhalten.
Siehe `.env.example`.

## Start

```bash
# Abhängigkeiten (uv) — inkl. Streamlit-UI
uv sync --extra ui --group dev

# Pipeline (ETL → Parquet + DuckDB / MotherDuck)
uv run python -m data_pipeline.run

# Streamlit-App
uv run streamlit run app/Home.py

# FastAPI (Vercel-Entrypoint lokal)
uv run uvicorn backend.main:app --reload
# OpenAPI: http://127.0.0.1:8000/docs

# Next.js-Frontend (proxied /api → FastAPI)
cd web && npm install && npm run dev
# http://localhost:3000

# Tests (inkl. Offline-E2E + API)
uv run pytest
```

### Automatisierte Pipeline

| Weg | Datei | Hinweis |
| --- | --- | --- |
| **GitHub Actions** | `.github/workflows/daily-pipeline.yml` | Täglich → Silver/Gold in MotherDuck (unabhängig vom Vercel-Deploy) |
| **CI** | `.github/workflows/ci.yml` | `pytest` auf Push/PR (ohne MotherDuck) |
| **Host-Cron** | `scripts/cron-pipeline.sh` | Lokaler/cron-ETL |
| **Vercel (Prod)** | `vercel.json` + `docs/vercel-deploy.md` | Framework Preset **muss** `Services` sein; Root Directory = Repo-Root |

Bei Pipeline-Fehlern schreibt `python -m data_pipeline.run` einen vollständigen Stacktrace und Exit-Code `1`.

### GitHub Actions Secrets (Daily Pipeline → MotherDuck)

Der Workflow `.github/workflows/daily-pipeline.yml` schreibt Silver/Gold **nur** nach MotherDuck.
Dafür müssen im GitHub-Repo Secrets angelegt werden — **nicht** im Code und **nicht** in
einer eingecheckten `.env`:

1. Repo öffnen → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** für:

| Secret | Pflicht | Inhalt |
| --- | --- | --- |
| `MOTHERDUCK_TOKEN` | ja | MotherDuck Access Token (read-write), z. B. aus MotherDuck UI oder Vercel Marketplace |
| `MOTHERDUCK_DATABASE` | nein | Datenbankname; fehlt er, nutzt der Job den Default `poll_position` |

3. Workflow manuell testen: **Actions** → *Daily Pipeline* → *Run workflow*

**Sicherheit:** `MOTHERDUCK_TOKEN` **niemals** ins Repository committen, nicht in Issues/PRs
posten und nicht in eine getrackte `.env` schreiben. Lokal nur eine **private** `.env`
(steht in `.gitignore`); Vorlage mit leeren Platzhaltern: `.env.example`.
CI-Unit-/Integrationstests laufen absichtlich **ohne** Token (lokale Temp-DuckDB).

## Datenquellen & rechtliche Rahmenbedingungen

Die App ist für **persönlichen / nicht-kommerziellen** Gebrauch gedacht, solange keine
zusätzliche **kommerzielle Lizenz** für europäische Zusatzdaten (z. B. Europe Elects /
ähnliche Anbieter) erworben wurde. Eine Weitergabe oder kommerzielle Nutzung der
zusammengeführten Datenbank kann je nach Quelle **Share-Alike-** und
**Attributionspflichten** auslösen — bitte Lizenzen selbst prüfen.

### Dawum (Deutschland)

| | |
| --- | --- |
| Quelle | [dawum.de](https://dawum.de/) |
| Lizenz | [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| Attribution | *„Umfragedaten: dawum.de (Open Database License (ODbL))“* |
| Hinweise | Abgeleitete Datenbanken unterliegen ODbL-Share-Alike; Roh-JSON bleibt in Bronze erhalten. |

### Wikipedia (paneuropäische Opinion-Polling-Tabellen)

| | |
| --- | --- |
| Quelle | en.wikipedia.org — Seiten *Opinion polling for the next … election* |
| Lizenz | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Attribution | *„Quelle: Wikipedia-Mitwirkende, CC BY-SA“* inkl. Permalink mit Revision-ID (`oldid=…`) |
| Hinweise | Textänderungen müssen unter kompatibler Share-Alike-Lizenz weitergegeben werden. |

### Nicht verdrahtet: Politico / Europe Elects (und ähnliche)

| | |
| --- | --- |
| [Politico Poll of Polls](https://www.politico.eu/europe-poll-of-polls/) | Keine offene API |
| [Europe Elects](https://europeelects.eu/) | Kostenpflichtig bzw. nicht-kommerziell lizenziert — **kein** Standard-Connector |
| Nutzung | Ein Adapter über `PollSourceAdapter` ist erst sinnvoll, wenn eine **gültige Lizenz** vorliegt; ohne diese bleibt der Einsatz auf persönliche/nicht-kommerzielle Wikipedia-/Dawum-Pfade beschränkt. |

### Wahlrechts- und Referenzdaten

Konfiguration und Belegzahlen (z. B. `de_parliaments.yaml`, `election_results.yaml`)
stützen sich auf öffentlich zugängliche Angaben der Bundeswahlleiterin,
Landeswahlleitungen und Fachportale wie [wahlrecht.de](https://www.wahlrecht.de/).
Das sind keine Umfrage-Rohdaten; bei Übernahme amtlicher Tabellen gelten die
jeweiligen Nutzungsbedingungen der Herausgebenden.

## Status

<!-- AUTO:START:meta -->
_Zuletzt automatisch aktualisiert: **2026-08-24 20:04:12 CEST**_

Diese Abschnitte werden von `scripts/update-readme.py` gepflegt (Cursor-Hook nach jeder Agent-Session + manueller Aufruf).
<!-- AUTO:END:meta -->

## Überblick

<!-- AUTO:START:overview -->
- **Repo:** [Poll-Position](https://github.com/philipp-hartmann-hub/Poll-Position)
- **Remote:** `https://github.com/philipp-hartmann-hub/Poll-Position.git`
- **Projektroot:** `Umfragen`
- **Dateien (sichtbar):** 80
- **Stack-Hinweise:** Node.js / npm, Python (pip), Python (pyproject)
- **Git-Branch:** `main` · Commits: 11 · Status: sauber
<!-- AUTO:END:overview -->

## Projektstruktur

<!-- AUTO:START:structure -->
```text
.cursorrules
.env.example
.github/workflows/ci.yml
.github/workflows/daily-pipeline.yml
.gitignore
.pytest_cache/.gitignore
.pytest_cache/CACHEDIR.TAG
.pytest_cache/v/cache/lastfailed
.pytest_cache/v/cache/nodeids
.vercel/python/.lock
.vercel/python/services/api/vc_init_dev.py
.vercel/python/vercel_runtime/__init__.py
.vercel/python/vercel_runtime/_vendor/__init__.py
.vercel/python/vercel_runtime/_vendor/click/LICENSE.txt
.vercel/python/vercel_runtime/_vendor/click/__init__.py
.vercel/python/vercel_runtime/_vendor/click/_compat.py
.vercel/python/vercel_runtime/_vendor/click/_termui_impl.py
.vercel/python/vercel_runtime/_vendor/click/_textwrap.py
.vercel/python/vercel_runtime/_vendor/click/_winconsole.py
.vercel/python/vercel_runtime/_vendor/click/core.py
.vercel/python/vercel_runtime/_vendor/click/decorators.py
.vercel/python/vercel_runtime/_vendor/click/exceptions.py
.vercel/python/vercel_runtime/_vendor/click/formatting.py
.vercel/python/vercel_runtime/_vendor/click/globals.py
.vercel/python/vercel_runtime/_vendor/click/parser.py
.vercel/python/vercel_runtime/_vendor/click/py.typed
.vercel/python/vercel_runtime/_vendor/click/shell_completion.py
.vercel/python/vercel_runtime/_vendor/click/termui.py
.vercel/python/vercel_runtime/_vendor/click/testing.py
.vercel/python/vercel_runtime/_vendor/click/types.py
.vercel/python/vercel_runtime/_vendor/click/utils.py
.vercel/python/vercel_runtime/_vendor/colorama/LICENSE.txt
.vercel/python/vercel_runtime/_vendor/colorama/__init__.py
.vercel/python/vercel_runtime/_vendor/colorama/ansi.py
.vercel/python/vercel_runtime/_vendor/colorama/ansitowin32.py
.vercel/python/vercel_runtime/_vendor/colorama/initialise.py
.vercel/python/vercel_runtime/_vendor/colorama/win32.py
.vercel/python/vercel_runtime/_vendor/colorama/winterm.py
.vercel/python/vercel_runtime/_vendor/colorama.pyi
.vercel/python/vercel_runtime/_vendor/h11/LICENSE.txt
.vercel/python/vercel_runtime/_vendor/h11/__init__.py
.vercel/python/vercel_runtime/_vendor/h11/_abnf.py
.vercel/python/vercel_runtime/_vendor/h11/_connection.py
.vercel/python/vercel_runtime/_vendor/h11/_events.py
.vercel/python/vercel_runtime/_vendor/h11/_headers.py
.vercel/python/vercel_runtime/_vendor/h11/_readers.py
.vercel/python/vercel_runtime/_vendor/h11/_receivebuffer.py
.vercel/python/vercel_runtime/_vendor/h11/_state.py
.vercel/python/vercel_runtime/_vendor/h11/_util.py
.vercel/python/vercel_runtime/_vendor/h11/_version.py
.vercel/python/vercel_runtime/_vendor/h11/_writers.py
.vercel/python/vercel_runtime/_vendor/h11/py.typed
.vercel/python/vercel_runtime/_vendor/markupsafe/LICENSE.txt
.vercel/python/vercel_runtime/_vendor/markupsafe/__init__.py
.vercel/python/vercel_runtime/_vendor/markupsafe/_native.py
.vercel/python/vercel_runtime/_vendor/markupsafe/_speedups.c
.vercel/python/vercel_runtime/_vendor/markupsafe/_speedups.pyi
.vercel/python/vercel_runtime/_vendor/markupsafe/py.typed
.vercel/python/vercel_runtime/_vendor/uvicorn/LICENSE.md
.vercel/python/vercel_runtime/_vendor/uvicorn/__init__.py
.vercel/python/vercel_runtime/_vendor/uvicorn/__main__.py
.vercel/python/vercel_runtime/_vendor/uvicorn/_compat.py
.vercel/python/vercel_runtime/_vendor/uvicorn/_subprocess.py
.vercel/python/vercel_runtime/_vendor/uvicorn/_types.py
.vercel/python/vercel_runtime/_vendor/uvicorn/config.py
.vercel/python/vercel_runtime/_vendor/uvicorn/importer.py
.vercel/python/vercel_runtime/_vendor/uvicorn/lifespan/__init__.py
.vercel/python/vercel_runtime/_vendor/uvicorn/lifespan/off.py
.vercel/python/vercel_runtime/_vendor/uvicorn/lifespan/on.py
.vercel/python/vercel_runtime/_vendor/uvicorn/logging.py
.vercel/python/vercel_runtime/_vendor/uvicorn/loops/__init__.py
.vercel/python/vercel_runtime/_vendor/uvicorn/loops/asyncio.py
.vercel/python/vercel_runtime/_vendor/uvicorn/loops/auto.py
.vercel/python/vercel_runtime/_vendor/uvicorn/loops/uvloop.py
.vercel/python/vercel_runtime/_vendor/uvicorn/main.py
.vercel/python/vercel_runtime/_vendor/uvicorn/middleware/__init__.py
.vercel/python/vercel_runtime/_vendor/uvicorn/middleware/asgi2.py
.vercel/python/vercel_runtime/_vendor/uvicorn/middleware/message_logger.py
.vercel/python/vercel_runtime/_vendor/uvicorn/middleware/proxy_headers.py
.vercel/python/vercel_runtime/_vendor/uvicorn/middleware/wsgi.py
… (weitere Dateien ausgeblendet)
```
<!-- AUTO:END:structure -->

## Dateitypen

<!-- AUTO:START:languages -->
| Endung | Anzahl |
| --- | ---: |
| `.py` | 59 |
| `(ohne Endung)` | 6 |
| `.txt` | 4 |
| `.typed` | 3 |
| `.pyi` | 2 |
| `.yml` | 2 |
| `.c` | 1 |
| `.example` | 1 |
| `.md` | 1 |
| `.tag` | 1 |
<!-- AUTO:END:languages -->

## README aktualisieren

<!-- AUTO:START:howto -->
```bash
python3 scripts/update-readme.py
```

Der Cursor-Hook `.cursor/hooks/update-readme.sh` ruft dasselbe Skript
am Ende jeder Agent-Session (`stop`) auf.
<!-- AUTO:END:howto -->
