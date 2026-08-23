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
| **Bronze** | `data/raw/<quelle>/<YYYY-MM-DD>.parquet` | Roh-Snapshots je Quelle und Abrufdatum, bereits im einheitlichen Beobachtungsschema |
| **Silver** | `data/warehouse.duckdb` → u. a. `polls_silver` | Vereinheitlichte, bereinigte Umfragezeilen |
| **Gold** | `data/warehouse.duckdb` (aggregierte Tabellen, folgen) | Auswertungsfertige Kennzahlen, Sitze, Koalitionen |

## Start

```bash
# Abhängigkeiten (uv)
uv sync

# Pipeline (ETL → Parquet + DuckDB)
uv run python -m data_pipeline.run

# Streamlit-App
uv run streamlit run app/Home.py

# Tests
uv run pytest
```

## Status

<!-- AUTO:START:meta -->
_Zuletzt automatisch aktualisiert: **2026-08-23 12:17:58 CEST**_

Diese Abschnitte werden von `scripts/update-readme.py` gepflegt (Cursor-Hook nach jeder Agent-Session + manueller Aufruf).
<!-- AUTO:END:meta -->

## Überblick

<!-- AUTO:START:overview -->
- **Repo:** [Poll-Position](https://github.com/philipp-hartmann-hub/Poll-Position)
- **Remote:** `https://github.com/philipp-hartmann-hub/Poll-Position.git`
- **Projektroot:** `Umfragen`
- **Dateien (sichtbar):** 34
- **Stack-Hinweise:** Python (pyproject)
- **Git-Branch:** `main` · Commits: 0 · Status: Arbeitsbaum unsauber
<!-- AUTO:END:overview -->

## Projektstruktur

<!-- AUTO:START:structure -->
```text
.cursorrules
.env.example
.gitignore
.pytest_cache/.gitignore
.pytest_cache/CACHEDIR.TAG
.pytest_cache/v/cache/lastfailed
.pytest_cache/v/cache/nodeids
AGENTS.md
analysis/__init__.py
analysis/coalitions.py
analysis/schema.py
analysis/seats/__init__.py
analysis/seats/sainte_lague.py
app/Home.py
app/__init__.py
app/pages/1_Umfragen.py
app/pages/2_Sitze_Koalitionen.py
data/raw/.gitkeep
data/raw/dawum/2026-08-23.parquet
data/raw/wikipedia_polls/2026-08-23.parquet
data/warehouse.duckdb
data_pipeline/__init__.py
data_pipeline/run.py
data_pipeline/schema_bridge.py
data_pipeline/sources/__init__.py
data_pipeline/sources/dawum.py
data_pipeline/sources/wikipedia_polls.py
data_pipeline/warehouse.py
pyproject.toml
scripts/update-readme.py
tests/analysis/seats/test_sainte_lague.py
tests/analysis/test_coalitions.py
tests/analysis/test_schema.py
uv.lock
```
<!-- AUTO:END:structure -->

## Dateitypen

<!-- AUTO:START:languages -->
| Endung | Anzahl |
| --- | ---: |
| `.py` | 20 |
| `(ohne Endung)` | 6 |
| `.parquet` | 2 |
| `.duckdb` | 1 |
| `.example` | 1 |
| `.lock` | 1 |
| `.md` | 1 |
| `.tag` | 1 |
| `.toml` | 1 |
<!-- AUTO:END:languages -->

## README aktualisieren

<!-- AUTO:START:howto -->
```bash
python3 scripts/update-readme.py
```

Der Cursor-Hook `.cursor/hooks/update-readme.sh` ruft dasselbe Skript
am Ende jeder Agent-Session (`stop`) auf.
<!-- AUTO:END:howto -->
