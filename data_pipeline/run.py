"""CLI-Einstieg: python -m data_pipeline.run"""

from __future__ import annotations

import logging
from datetime import date

from data_pipeline.schema_bridge import observations_to_frame
from data_pipeline.sources.dawum import DawumAdapter
from data_pipeline.sources.wikipedia_polls import WikipediaPollsAdapter
from data_pipeline.warehouse import ensure_warehouse, load_bronze_into_silver, write_bronze

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
        if hasattr(adapter, "run"):
            result = adapter.run(as_of=today)
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
            continue

        batch = adapter.fetch()
        frame = observations_to_frame(batch.observations)
        path = write_bronze(adapter.source_id, frame, as_of=today)
        log.info("Bronze → %s (%d Zeilen, status=%s)", path, frame.height, batch.status)
        if frame.height > 0:
            load_bronze_into_silver(path)
            log.info("Silver aktualisiert")


if __name__ == "__main__":
    main()
