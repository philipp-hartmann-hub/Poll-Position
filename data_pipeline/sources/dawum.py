"""Dawum-API/-Feed Adapter (Stub — Implementierung folgt)."""

from __future__ import annotations

from datetime import datetime, timezone

from analysis.schema import PollBatch


class DawumAdapter:
    source_id = "dawum"

    def fetch(self) -> PollBatch:
        # TODO: HTTP-Abruf + Mapping auf PollObservation
        return PollBatch(
            source=self.source_id,
            observations=[],
            fetched_at=datetime.now(timezone.utc),
            status="empty",
            notes="Adapter-Stub: noch keine Abruflogik",
        )
