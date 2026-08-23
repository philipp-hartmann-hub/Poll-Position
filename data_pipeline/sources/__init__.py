"""Adapter-Protokoll und Registry für Datenquellen."""

from __future__ import annotations

from typing import Protocol

from analysis.schema import PollBatch


class SourceAdapter(Protocol):
    """Jeder Adapter in `data_pipeline/sources/` implementiert dieses Minimum."""

    source_id: str

    def fetch(self) -> PollBatch:
        """Rohdaten holen und als einheitliches PollBatch zurückgeben."""
        ...
