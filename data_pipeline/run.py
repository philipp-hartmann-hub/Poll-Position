"""CLI-Einstieg: python -m data_pipeline.run"""

from __future__ import annotations

import logging
from datetime import date

from data_pipeline.sources.dawum import DawumAdapter
from data_pipeline.sources.wikipedia_polls import WikipediaPollsAdapter
from data_pipeline.warehouse import ensure_warehouse, refresh_gold_averages

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("data_pipeline")

ADAPTERS = [
    DawumAdapter(),
    WikipediaPollsAdapter(),
]


def main() -> None:
    ensure_warehouse()
    today = date.today()
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


if __name__ == "__main__":
    main()
