"""Sainte-Laguë / Schepers — Delegat an analysis.seat_allocation."""

from __future__ import annotations

from analysis.seat_allocation import sainte_lague_schepers


def allocate_sainte_lague(
    votes: dict[str, float],
    seats: int,
    *,
    threshold: float | None = None,
) -> dict[str, int]:
    """Kompatibilitäts-Wrapper; `threshold` als Anteil 0–1."""
    return sainte_lague_schepers(votes, seats, threshold=threshold or 0.0)
