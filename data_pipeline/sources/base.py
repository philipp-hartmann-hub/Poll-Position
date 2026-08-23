"""Gemeinsames Adapter-Interface für alle Umfragequellen."""

from __future__ import annotations

from abc import ABC, abstractmethod

from data_pipeline.schema import Survey


class PollSourceAdapter(ABC):
    """
    Abstrakte Basis für Dawum, Wikipedia und künftige Quellen
    (PolitPro, Europe-Elects-Export, …).

    `fetch()` liefert kanonische `Survey`-Objekte; Persistenz (Bronze/Silver)
    liegt in optionalen `run()`-Methoden der konkreten Adapter.
    """

    source_id: str

    @abstractmethod
    def fetch(self) -> list[Survey]:
        """Rohdaten abrufen und als Liste von Survey normalisieren."""
        ...
