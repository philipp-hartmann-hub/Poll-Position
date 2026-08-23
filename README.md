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
| **Gold** | `data/warehouse.duckdb` → `party_averages`, `party_trends` | Gewichtete Parteischnitte, Trends, Swing vs. letzte Wahl |

## Start

```bash
# Abhängigkeiten (uv)
uv sync

# Pipeline (ETL → Parquet + DuckDB)
uv run python -m data_pipeline.run

# Streamlit-App
uv run streamlit run app/Home.py

# Tests (inkl. Offline-E2E)
uv run pytest
```

### Automatisierte Pipeline

| Weg | Datei | Hinweis |
| --- | --- | --- |
| **GitHub Actions** | `.github/workflows/daily-pipeline.yml` | Cron `15 5 * * *` UTC + manueller `workflow_dispatch`; bei Fehlern `::error::` und Artifact `warehouse-<run_id>` |
| **CI** | `.github/workflows/ci.yml` | `pytest` auf Push/PR |
| **Host-Cron** | `scripts/cron-pipeline.sh` | z. B. `15 6 * * * /pfad/scripts/cron-pipeline.sh >> /var/log/poll-position.log 2>&1` |

Bei Pipeline-Fehlern schreibt `python -m data_pipeline.run` einen vollständigen Stacktrace und Exit-Code `1`.

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
_Zuletzt automatisch aktualisiert: **2026-08-23 14:21:14 CEST**_

Diese Abschnitte werden von `scripts/update-readme.py` gepflegt (Cursor-Hook nach jeder Agent-Session + manueller Aufruf).
<!-- AUTO:END:meta -->

## Überblick

<!-- AUTO:START:overview -->
- **Repo:** [Poll-Position](https://github.com/philipp-hartmann-hub/Poll-Position)
- **Remote:** `https://github.com/philipp-hartmann-hub/Poll-Position.git`
- **Projektroot:** `Umfragen`
- **Dateien (sichtbar):** 80
- **Stack-Hinweise:** Python (pyproject)
- **Git-Branch:** `main` · Commits: 7 · Status: Arbeitsbaum unsauber
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
AGENTS.md
CHANGELOG.md
analysis/__init__.py
analysis/averages.py
analysis/coalitions.py
analysis/house_effects.py
analysis/party_families.py
analysis/scenario.py
analysis/schema.py
analysis/seat_allocation.py
analysis/seats/__init__.py
analysis/seats/sainte_lague.py
analysis/uncertainty.py
app/Home.py
app/__init__.py
app/lib/__init__.py
app/lib/analysis_bridge.py
app/lib/charts.py
app/lib/components.py
app/lib/db.py
app/lib/ui.py
app/pages/1_Deutschland_Bund.py
app/pages/2_Deutschland_Laender.py
app/pages/3_Europa_Uebersicht.py
app/pages/4_Institute_Vergleich.py
app/pages/5_Was_waere_wenn.py
data/raw/.gitkeep
data/raw/dawum/2026-08-23.parquet
data/raw/dawum/last_update.txt
data/raw/wikipedia_polls/2026-08-23.parquet
data/warehouse.duckdb
data_pipeline/__init__.py
data_pipeline/config/coalition_rules.yaml
data_pipeline/config/de_parliaments.yaml
data_pipeline/config/party_families.yaml
data_pipeline/config/wikipedia_pages.yaml
data_pipeline/reference/__init__.py
data_pipeline/reference/election_results.py
data_pipeline/reference/election_results.yaml
data_pipeline/run.py
data_pipeline/schema.py
data_pipeline/schema_bridge.py
data_pipeline/sources/__init__.py
data_pipeline/sources/base.py
data_pipeline/sources/dawum.py
data_pipeline/sources/wikipedia_parsers.py
data_pipeline/sources/wikipedia_polls.py
data_pipeline/warehouse.py
pyproject.toml
scripts/cron-pipeline.sh
scripts/update-readme.py
tests/__init__.py
tests/analysis/__init__.py
tests/analysis/seats/__init__.py
tests/analysis/seats/test_sainte_lague.py
tests/analysis/test_averages.py
tests/analysis/test_coalitions.py
tests/analysis/test_house_effects.py
tests/analysis/test_party_families.py
tests/analysis/test_scenario.py
tests/analysis/test_schema.py
tests/analysis/test_seat_allocation.py
tests/analysis/test_uncertainty.py
tests/data_pipeline/__init__.py
tests/data_pipeline/fixtures/dawum_sample.json
tests/data_pipeline/fixtures/pipeline_e2e_payload.py
tests/data_pipeline/fixtures/wikipedia_austria.html
tests/data_pipeline/fixtures/wikipedia_spain.html
tests/data_pipeline/test_canonical_schema.py
tests/data_pipeline/test_dawum.py
tests/data_pipeline/test_wikipedia_polls.py
… (weitere Dateien ausgeblendet)
```
<!-- AUTO:END:structure -->

## Dateitypen

<!-- AUTO:START:languages -->
| Endung | Anzahl |
| --- | ---: |
| `.py` | 54 |
| `(ohne Endung)` | 6 |
| `.yaml` | 5 |
| `.html` | 2 |
| `.md` | 2 |
| `.parquet` | 2 |
| `.yml` | 2 |
| `.duckdb` | 1 |
| `.example` | 1 |
| `.json` | 1 |
| `.sh` | 1 |
| `.tag` | 1 |
| `.toml` | 1 |
| `.txt` | 1 |
<!-- AUTO:END:languages -->

## README aktualisieren

<!-- AUTO:START:howto -->
```bash
python3 scripts/update-readme.py
```

Der Cursor-Hook `.cursor/hooks/update-readme.sh` ruft dasselbe Skript
am Ende jeder Agent-Session (`stop`) auf.
<!-- AUTO:END:howto -->
