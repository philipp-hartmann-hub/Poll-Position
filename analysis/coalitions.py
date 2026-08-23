"""Koalitions- und Mehrheitslogik (UI-frei)."""

from __future__ import annotations

from itertools import combinations


def has_majority(seats: dict[str, int], coalition: list[str], *, total_seats: int | None = None) -> bool:
    """True, wenn die Koalition strikt mehr als die Hälfte der Sitze hält."""
    chamber = total_seats if total_seats is not None else sum(seats.values())
    if chamber <= 0:
        return False
    coalition_seats = sum(seats.get(p, 0) for p in coalition)
    return coalition_seats > chamber / 2


def majority_coalitions(
    seats: dict[str, int],
    *,
    max_parties: int = 3,
    total_seats: int | None = None,
) -> list[tuple[str, ...]]:
    """Alle Mehrheitskoalitionen bis `max_parties` Parteien, sortiert nach Sitzsumme desc."""
    parties = [p for p, s in seats.items() if s > 0]
    found: list[tuple[str, ...]] = []
    for k in range(1, min(max_parties, len(parties)) + 1):
        for combo in combinations(sorted(parties), k):
            if has_majority(seats, list(combo), total_seats=total_seats):
                found.append(combo)
    found.sort(key=lambda c: (-sum(seats[p] for p in c), len(c), c))
    return found
