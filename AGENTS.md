# Poll-Position — Agent- und Beitragsregeln

## Ziel

Umfragen aus Dawum und paneuropäischen Quellen zusammenführen, Sitzverteilung und Koalitionen berechnen (Deutschland & Europa).

## Harte Regeln

1. **Analyse bleibt UI-frei**
   - Alle Auswertungs- und Wahlrechts-Logik liegt in `/analysis/`.
   - Keine Imports von `streamlit`, Plotly-UI-Widgets oder pydeck in `/analysis/`.
   - Streamlit (`/app/`) darf `analysis` nur **aufrufen**, nie Geschäftslogik duplizieren.

2. **pytest ist Pflicht für Analysis**
   - Neue oder geänderte Funktionen in `/analysis/` bekommen Tests unter `/tests/`, gespiegelt zur Paketstruktur (z. B. `analysis/seats/sainte_lague.py` → `tests/analysis/seats/test_sainte_lague.py`).
   - PRs/Merges ohne passende Tests für Analysis-Änderungen sind nicht zulässig.

3. **Datenquellen = eigene Adapter + einheitliches Schema**
   - Jede neue Quelle bekommt ein Modul unter `data_pipeline/sources/` (z. B. `dawum.py`, `wikipedia_polls.py`).
   - Kanonisches Domänenmodell: `data_pipeline/schema.py` (`Country`, `Parliament`, `Party`, `Pollster`, `Survey`, `ElectionSystem`).
   - Leichtes ETL-Zwischenformat: `analysis.schema.PollBatch` / `PollObservation` (Adapter-Rohrückgabe).
   - „Sonstige“ immer als eigene Partei (`SONSTIGE_PARTY_ID`), nie als Restwert ohne ID.
   - Wahlrechtsparameter: `data_pipeline/config/de_parliaments.yaml` (Bundestag + Landtage).
   - Keine Quell-Sonderformen direkt in Silver/Gold schreiben — Normalisierung im Adapter bzw. `schema_bridge`.

4. **Wahlrechts-Mathematik nie ohne Beleg-Test**
   - Sitzzuteilung, Schwellen, Ausgleichsmandate usw. werden **nicht** gemergt, ohne Unit-Test gegen ein **bekanntes echtes Wahlergebnis** (oder ein dokumentiertes amtliches Beispiel).
   - Toy-Beispiele allein reichen für Produktions-Wahlrechtscode nicht; mindestens ein Regressionstest mit veröffentlichten Ist-Zahlen.

5. **Datenarchitektur**
   - Bronze: `data/raw/<quelle>/<datum>.parquet`
   - Silver/Gold: `data/warehouse.duckdb`
   - Pipeline-Einstieg: `python -m data_pipeline.run`

6. **Stack**
   - Python ≥ 3.12, Abhängigkeiten über `pyproject.toml` / `uv`.
   - Secrets nur über `.env` (nie committen).
