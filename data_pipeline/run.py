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
