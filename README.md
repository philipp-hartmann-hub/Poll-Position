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
| **Bronze** | `data/raw/<quelle>/<YYYY-MM-DD>.parquet` | Roh-Snapshots je Quelle und Abrufdatum (Dawum: unveränderte JSON-Antwort) |
| **Silver** | `data/warehouse.duckdb` → `parliaments`, `parties`, `institutes`, `surveys`, `survey_results` | Vereinheitlichte Entitäten im kanonischen Schema |
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

## Datenquellen & Lizenzen

Umfragedaten von [dawum.de](https://dawum.de/) werden unter der
[Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/) genutzt.
Attributionshinweis: *„Umfragedaten: dawum.de (Open Database License (ODbL))“*.

## Status

<!-- AUTO:START:meta -->
_Zuletzt automatisch aktualisiert: **2026-08-23 12:32:27 CEST**_

Diese Abschnitte werden von `scripts/update-readme.py` gepflegt (Cursor-Hook nach jeder Agent-Session + manueller Aufruf).
<!-- AUTO:END:meta -->

## Überblick

<!-- AUTO:START:overview -->
- **Repo:** [Poll-Position](https://github.com/philipp-hartmann-hub/Poll-Position)
- **Remote:** `https://github.com/philipp-hartmann-hub/Poll-Position.git`
- **Projektroot:** `Umfragen`
- **Dateien (sichtbar):** 44
- **Stack-Hinweise:** Python (pyproject)
- **Git-Branch:** `main` · Commits: 2 · Status: Arbeitsbaum unsauber
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
data/raw/dawum/last_update.txt
data/raw/wikipedia_polls/2026-08-23.parquet
data/warehouse.duckdb
data_pipeline/__init__.py
data_pipeline/config/de_parliaments.yaml
data_pipeline/run.py
data_pipeline/schema.py
data_pipeline/schema_bridge.py
data_pipeline/sources/__init__.py
data_pipeline/sources/dawum.py
data_pipeline/sources/wikipedia_polls.py
data_pipeline/warehouse.py
pyproject.toml
scripts/update-readme.py
tests/__init__.py
tests/analysis/__init__.py
tests/analysis/seats/__init__.py
tests/analysis/seats/test_sainte_lague.py
tests/analysis/test_coalitions.py
tests/analysis/test_schema.py
tests/data_pipeline/__init__.py
tests/data_pipeline/fixtures/dawum_sample.json
tests/data_pipeline/test_canonical_schema.py
tests/data_pipeline/test_dawum.py
uv.lock
```
<!-- AUTO:END:structure -->

## Dateitypen

<!-- AUTO:START:languages -->
| Endung | Anzahl |
| --- | ---: |
| `.py` | 27 |
| `(ohne Endung)` | 6 |
| `.parquet` | 2 |
| `.duckdb` | 1 |
| `.example` | 1 |
| `.json` | 1 |
| `.lock` | 1 |
| `.md` | 1 |
| `.tag` | 1 |
| `.toml` | 1 |
| `.txt` | 1 |
| `.yaml` | 1 |
<!-- AUTO:END:languages -->

## README aktualisieren

<!-- AUTO:START:howto -->
```bash
python3 scripts/update-readme.py
```

Der Cursor-Hook `.cursor/hooks/update-readme.sh` ruft dasselbe Skript
am Ende jeder Agent-Session (`stop`) auf.
<!-- AUTO:END:howto -->
