"""CLI-Einstieg: python -m data_pipeline.run"""

from __future__ import annotations

import logging
import sys
from datetime import date

from data_pipeline.sources.dawum import DawumAdapter
from data_pipeline.sources.wikipedia_polls import WikipediaPollsAdapter
from data_pipeline.warehouse import ensure_warehouse, refresh_gold_averages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("data_pipeline")

ADAPTERS = [
    DawumAdapter(),
    WikipediaPollsAdapter(),
]


def _run_freshness_checks(*, as_of: date) -> None:
    """Fehlertolerant: Wahlergebnis-Watch + Regierungs-Stand-Alter."""
    try:
        from data_pipeline.sources.election_watch import run_election_watch

        run_election_watch(as_of=as_of)
    except Exception:
        log.exception("Election-Watch-Schritt fehlgeschlagen — Pipeline läuft weiter")

    try:
        from analysis.bundesrat import check_government_config_age, load_bundesrat_config

        cfg = load_bundesrat_config()
        for msg in check_government_config_age(cfg, as_of=as_of):
            log.warning("Regierungskonfig: %s", msg)
    except Exception:
        log.exception("Regierungskonfig-Alterscheck fehlgeschlagen — weiter")

    # Optional, Best-Effort: Diff Ministerpräsidenten-Liste vs. Config
    try:
        from data_pipeline.sources.election_watch import (
            maybe_scrape_ministerpraesidenten_diff,
        )

        notes = maybe_scrape_ministerpraesidenten_diff()
        for note in notes:
            log.warning("Regierungs-Scraper: %s", note)
    except Exception:
        log.exception("Ministerpräsidenten-Scraper fehlgeschlagen — weiter")


def main() -> int:
    """Führt alle Connectoren und Gold-Refresh aus. Rückgabe: 0 ok, 1 Fehler."""
    today = date.today()
    try:
        from data_pipeline.warehouse import uses_motherduck, warehouse_connection_target

        ensure_warehouse()
        log.info(
            "Warehouse-Ziel: %s (%s)",
            warehouse_connection_target(),
            "MotherDuck" if uses_motherduck() else "lokal",
        )
        for adapter in ADAPTERS:
            log.info("Pipeline %s …", adapter.source_id)
            result = adapter.run(as_of=today)
            if adapter.source_id == "dawum":
                log.info(
                    "%s: fetched=%s bronze=%s parliaments=%d parties=%d institutes=%d "
                    "new_surveys=%d new_results=%d last_update=%s",
                    adapter.source_id,
                    result.fetched,
                    result.bronze_path,
                    result.parliaments,
                    result.parties,
                    result.institutes,
                    result.surveys_new,
                    result.results_new,
                    result.last_update,
                )
            else:
                log.info(
                    "%s: bronze=%d new_surveys=%d new_results=%d total_surveys=%d",
                    adapter.source_id,
                    len(result.bronze_paths),
                    result.surveys_new,
                    result.results_new,
                    len(result.surveys),
                )

        _run_freshness_checks(as_of=today)

        n_avg, n_tr = refresh_gold_averages(reference_date=today)
        log.info("Gold: party_averages=%d party_trends=%d", n_avg, n_tr)

        from data_pipeline.export_static import export_all_static

        n_static = export_all_static()
        log.info("Static-JSON-Export: %d Dateien", n_static)

        log.info("Pipeline erfolgreich abgeschlossen.")
        return 0
    except Exception:
        log.exception(
            "Pipeline fehlgeschlagen — Abbruch. "
            "Bitte Connector-Logs, Netzwerk und Schema prüfen."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
