"""Adapter-Paket: Basisklasse + konkrete Quellen."""

from data_pipeline.sources.base import PollSourceAdapter
from data_pipeline.sources.dawum import DawumAdapter
from data_pipeline.sources.wikipedia_polls import WikipediaPollsAdapter

__all__ = [
    "PollSourceAdapter",
    "DawumAdapter",
    "WikipediaPollsAdapter",
]
