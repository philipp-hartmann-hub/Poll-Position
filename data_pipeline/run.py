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
        log.info("Fetch %s …", adapter.source_id)
        batch = adapter.fetch()
        frame = observations_to_frame(batch.observations)
        path = write_bronze(adapter.source_id, frame, as_of=today)
        log.info("Bronze → %s (%d Zeilen, status=%s)", path, frame.height, batch.status)
        if frame.height > 0:
            load_bronze_into_silver(path)
            log.info("Silver aktualisiert")


if __name__ == "__main__":
    main()
