"""Wikipedia-Umfragen-Tabellen Adapter (Stub — Implementierung folgt)."""

from __future__ import annotations

from datetime import datetime, timezone

from analysis.schema import PollBatch


class WikipediaPollsAdapter:
    source_id = "wikipedia_polls"

    def fetch(self) -> PollBatch:
        # TODO: Tabellen parsen + Mapping auf PollObservation
        return PollBatch(
            source=self.source_id,
            observations=[],
            fetched_at=datetime.now(timezone.utc),
            status="empty",
            notes="Adapter-Stub: noch keine Abruflogik",
        )
