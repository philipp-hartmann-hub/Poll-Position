"""Referenzdaten (Wahlergebnisse u. a.)."""

from data_pipeline.reference.election_results import (
    ElectionResult,
    ElectionResultsBundle,
    latest_election_for,
    load_election_results,
)

__all__ = [
    "ElectionResult",
    "ElectionResultsBundle",
    "latest_election_for",
    "load_election_results",
]
