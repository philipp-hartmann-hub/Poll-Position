"""Sainte-Laguë / Schepers Sitzzuteilung."""

from __future__ import annotations


def allocate_sainte_lague(
    votes: dict[str, float],
    seats: int,
    *,
    threshold: float | None = None,
) -> dict[str, int]:
    """
    Verteilt `seats` nach Sainte-Laguë (Divisoren 1, 3, 5, …).

    Args:
        votes: Partei → Stimmen oder Prozentanteile (nur relative Größen zählen).
        seats: Zu vergebende Sitze.
        threshold: Optionaler Anteil (0–1), darunter wird die Partei ausgeschlossen.
                   Bezogen auf die Summe von `votes`.

    Returns:
        Partei → Sitzzahl (Parteien ohne Sitz fehlen nicht; Wert 0 möglich).
    """
    if seats < 0:
        raise ValueError("seats muss >= 0 sein")
    if not votes:
        return {}

    total = sum(votes.values())
    if total <= 0:
        raise ValueError("Summe der Stimmen muss > 0 sein")

    eligible = {
        party: weight
        for party, weight in votes.items()
        if weight > 0 and (threshold is None or (weight / total) >= threshold)
    }
    if not eligible:
        return {party: 0 for party in votes}

    allocation = {party: 0 for party in votes}
    # Höchstzahlverfahren: für jeden Sitz den besten Quotienten wählen
    for _ in range(seats):
        best_party = max(
            eligible,
            key=lambda p: eligible[p] / (2 * allocation[p] + 1),
        )
        allocation[best_party] += 1

    return allocation
