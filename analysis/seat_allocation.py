"""
Sitzzuteilungsverfahren — reine Funktionen, land-/parlamentsunabhängig.

Sperrklausel (threshold)
------------------------
Parteien unterhalb der Hürde erhalten 0 Sitze. Ihre Stimmen werden **nicht**
auf die übrigen Parteien umverteilt (keine Normierung der verbleibenden Anteile
auf 100 %). Stattdessen nehmen nur die zugelassenen Parteien am Zuteilungsverfahren
teil und teilen sich die festgelegte Sitzzahl nach ihren Stimmenverhältnissen.

Das entspricht dem deutschen Bundeswahlrecht und den betrachteten Landeswahlrechten
(Saarland d’Hondt, Thüringen Hare/Niemeyer, Bundestag Sainte-Laguë/Schepers):
ausgeschlossene Stimmen fließen nicht in die Höchstzahl-/Quote-Berechnung ein,
verringern aber auch nicht die zu vergebende Sitzzahl.

Quellen (Bundestag / Zweitstimmendeckung)
-----------------------------------------
- https://www.bundestag.de/parlament/wahlen/wahlrecht-inhalt-975000
- https://www.bundeswahlleiterin.de/service/glossar/s/sitzverteilung.html

Ab BTW 2025: feste Größe 630; Oberverteilung nach Zweitstimmen (Sainte-Laguë/Schepers);
keine Überhang-/Ausgleichsmandate. Die Zweitstimmendeckung bestimmt, welche
Wahlkreisbewerber:innen innerhalb der landesweiten Sitzkontingente einer Partei
einen Sitz erhalten — die **Parteigesamtsitze** folgen allein aus der Oberverteilung.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from data_pipeline.schema import AllocationMethod, ElectionSystem, Parliament


def _validate_inputs(votes: Mapping[str, float], seats: int) -> None:
    if seats < 0:
        raise ValueError("seats muss >= 0 sein")
    if seats == 0:
        return
    if not votes:
        raise ValueError("votes darf nicht leer sein")
    if any(v < 0 for v in votes.values()):
        raise ValueError("Stimmen dürfen nicht negativ sein")
    if sum(votes.values()) <= 0:
        raise ValueError("Summe der Stimmen muss > 0 sein")


def _eligible_parties(
    votes: Mapping[str, float],
    threshold: float,
    *,
    total_votes: float | None = None,
    exempt_party_ids: Sequence[str] = (),
    constituency_wins: Mapping[str, int] | None = None,
    grundmandat_seats: int | None = None,
) -> dict[str, float]:
    """
    Parteien, die an der Sitzzuteilung teilnehmen.

    threshold: Anteil 0–1 bezogen auf total_votes (Standard: Summe von votes).
    Stimmen unter der Hürde werden nicht umverteilt — sie fehlen nur in der
    Zuteilungsmenge (siehe Modul-Docstring).
    """
    if threshold < 0 or threshold > 1:
        raise ValueError("threshold muss im Intervall [0, 1] liegen (Anteil, nicht Prozent)")

    total = float(total_votes) if total_votes is not None else float(sum(votes.values()))
    if total <= 0:
        raise ValueError("total_votes muss > 0 sein")

    exempt = set(exempt_party_ids)
    wins = constituency_wins or {}
    eligible: dict[str, float] = {}
    for party, weight in votes.items():
        if weight <= 0:
            continue
        share = weight / total
        if party in exempt:
            eligible[party] = float(weight)
            continue
        if share >= threshold:
            eligible[party] = float(weight)
            continue
        if (
            grundmandat_seats is not None
            and grundmandat_seats > 0
            and wins.get(party, 0) >= grundmandat_seats
        ):
            eligible[party] = float(weight)
    return eligible


def _empty_allocation(votes: Mapping[str, float]) -> dict[str, int]:
    return {party: 0 for party in votes}


def sainte_lague_schepers(
    votes: dict[str, float],
    seats: int,
    threshold: float = 0.0,
    *,
    total_votes: float | None = None,
    exempt_party_ids: Sequence[str] = (),
    constituency_wins: Mapping[str, int] | None = None,
    grundmandat_seats: int | None = None,
) -> dict[str, int]:
    """
    Sainte-Laguë/Schepers (Divisorverfahren mit Standardrundung): Höchstzahlen
    votes / (2·s + 1), Divisorenfolge 1, 3, 5, …
    """
    _validate_inputs(votes, seats)
    if seats == 0:
        return _empty_allocation(votes)

    eligible = _eligible_parties(
        votes,
        threshold,
        total_votes=total_votes,
        exempt_party_ids=exempt_party_ids,
        constituency_wins=constituency_wins,
        grundmandat_seats=grundmandat_seats,
    )
    allocation = _empty_allocation(votes)
    if not eligible:
        return allocation

    for _ in range(seats):
        best = max(eligible, key=lambda p: (eligible[p] / (2 * allocation[p] + 1), eligible[p], p))
        allocation[best] += 1
    return allocation


def dhondt(
    votes: dict[str, float],
    seats: int,
    threshold: float = 0.0,
    *,
    total_votes: float | None = None,
    exempt_party_ids: Sequence[str] = (),
) -> dict[str, int]:
    """d’Hondt: Höchstzahlen votes / (s + 1), Divisorenfolge 1, 2, 3, …"""
    _validate_inputs(votes, seats)
    if seats == 0:
        return _empty_allocation(votes)

    eligible = _eligible_parties(
        votes,
        threshold,
        total_votes=total_votes,
        exempt_party_ids=exempt_party_ids,
    )
    allocation = _empty_allocation(votes)
    if not eligible:
        return allocation

    for _ in range(seats):
        best = max(eligible, key=lambda p: (eligible[p] / (allocation[p] + 1), eligible[p], p))
        allocation[best] += 1
    return allocation


def hare_niemeyer(
    votes: dict[str, float],
    seats: int,
    threshold: float = 0.0,
    *,
    total_votes: float | None = None,
    exempt_party_ids: Sequence[str] = (),
) -> dict[str, int]:
    """
    Hare/Niemeyer (Quota-Verfahren mit Restausgleich nach größten Bruchteilen).

    Quote_p = seats * votes_p / sum(eligible votes); ganzzahliger Anteil + Reste.
    """
    _validate_inputs(votes, seats)
    if seats == 0:
        return _empty_allocation(votes)

    eligible = _eligible_parties(
        votes,
        threshold,
        total_votes=total_votes,
        exempt_party_ids=exempt_party_ids,
    )
    allocation = _empty_allocation(votes)
    if not eligible:
        return allocation

    elig_sum = sum(eligible.values())
    quotas = {p: seats * eligible[p] / elig_sum for p in eligible}
    for party, quota in quotas.items():
        allocation[party] = int(math.floor(quota))

    remaining = seats - sum(allocation.values())
    # Größter Bruchteil; bei Gleichheit höhere Stimmenzahl, dann Name (stabil)
    order = sorted(
        eligible,
        key=lambda p: (quotas[p] - allocation[p], eligible[p], p),
        reverse=True,
    )
    for i in range(remaining):
        allocation[order[i]] += 1
    return allocation


@dataclass
class BundestagAllocationResult:
    """Ergebnis der Bundestag-Zuteilung inkl. optionaler Landesebene."""

    party_seats: dict[str, int]
    """Oberverteilung: Sitze je Partei (Summe = seats_total)."""

    land_party_seats: dict[str, dict[str, int]] = field(default_factory=dict)
    """Unterverteilung: Land → Partei → Sitze (leer, wenn keine Landstimmen)."""

    capped_direct_seats: dict[str, dict[str, int]] = field(default_factory=dict)
    """
    Zweitstimmendeckung: Land → Partei → max. berücksichtigte Wahlkreissitze
    (= min(Direktgewinne, Landeskontingent)).
    """


def bundestag_seat_allocation(
    votes: dict[str, float],
    *,
    seats: int = 630,
    threshold: float = 0.05,
    minority_party_ids: Sequence[str] = (),
    constituency_wins: Mapping[str, int] | None = None,
    grundmandat_seats: int = 3,
    land_votes: Mapping[str, Mapping[str, float]] | None = None,
    land_direct_wins: Mapping[str, Mapping[str, int]] | None = None,
    total_votes: float | None = None,
) -> BundestagAllocationResult:
    """
    Bundestagswahlrecht ab 2025 (Reform 2023 + BVerfG-Maßgabe zur Sperrklausel).

    1. **Oberverteilung**: Sainte-Laguë/Schepers auf `seats` (630) nach bundesweiten
       Zweitstimmen. Nur Parteien ≥ threshold, Minderheitenparteien oder mit
       ≥ `grundmandat_seats` Wahlkreiserfolgen (BVerfG 30.07.2024).
    2. **Unterverteilung** (optional, wenn `land_votes`): je Partei die Sitze auf
       Länder nach Sainte-Laguë gemäß Zweitstimmen im Land.
    3. **Zweitstimmendeckung** (optional, wenn `land_direct_wins`): in jedem Land
       höchstens so viele Wahlkreissitze je Partei wie Landeskontingent;
       `capped_direct_seats[land][party] = min(wins, land_seats)`.
       Überzählige Wahlkreissiege bleiben unbesetzt (kein Überhang).

    Ohne Landesdaten entspricht der Rückgabewert `party_seats` der nationalen
    Zweitstimmen-Sitzverteilung — für Umfragen auf Bundesebene ausreichend.
    """
    party_seats = sainte_lague_schepers(
        votes,
        seats,
        threshold,
        total_votes=total_votes,
        exempt_party_ids=minority_party_ids,
        constituency_wins=constituency_wins,
        grundmandat_seats=grundmandat_seats,
    )

    land_party_seats: dict[str, dict[str, int]] = {}
    capped: dict[str, dict[str, int]] = {}

    if land_votes:
        lands = sorted(land_votes.keys())
        for party, n_seats in party_seats.items():
            if n_seats <= 0:
                continue
            land_party_votes = {
                land: float(land_votes[land].get(party, 0.0)) for land in lands
            }
            if sum(land_party_votes.values()) <= 0:
                # Keine Landstimmen → alles auf erstes Land (Fallback)
                land_party_votes = {lands[0]: 1.0}
                for land in lands[1:]:
                    land_party_votes[land] = 0.0
            distributed = sainte_lague_schepers(land_party_votes, n_seats, threshold=0.0)
            for land, s in distributed.items():
                land_party_seats.setdefault(land, {})
                land_party_seats[land][party] = s

        if land_direct_wins:
            for land, wins_by_party in land_direct_wins.items():
                capped[land] = {}
                for party, wins in wins_by_party.items():
                    quota = land_party_seats.get(land, {}).get(party, 0)
                    capped[land][party] = min(int(wins), int(quota))

    return BundestagAllocationResult(
        party_seats=party_seats,
        land_party_seats=land_party_seats,
        capped_direct_seats=capped,
    )


def _threshold_fraction(election_system: ElectionSystem) -> float:
    """ElectionSystem speichert Hürde in Prozent (5.0 → 0.05)."""
    return float(election_system.threshold_percent) / 100.0


def allocate_seats(
    parliament_config: Parliament | ElectionSystem,
    party_votes: dict[str, float],
    *,
    election_system: ElectionSystem | None = None,
    total_votes: float | None = None,
    constituency_wins: Mapping[str, int] | None = None,
    land_votes: Mapping[str, Mapping[str, float]] | None = None,
    land_direct_wins: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, int]:
    """
    Dispatch: wählt das Verfahren anhand der ElectionSystem-Konfiguration.

    `parliament_config` kann ein `Parliament` (dann `election_system` nötig oder
    über `load_parliament_config` aufgelöst) oder direkt ein `ElectionSystem` sein.
    """
    system = election_system
    if isinstance(parliament_config, ElectionSystem):
        system = parliament_config
    elif system is None:
        from data_pipeline.schema import load_parliament_config

        bundle = load_parliament_config()
        key = parliament_config.election_system_key
        system = next(s for s in bundle.election_systems if s.key == key)

    assert system is not None
    thr = _threshold_fraction(system)
    seats = system.seats_total
    minority = list(system.minority_exempt_party_ids)

    if system.zweitstimmendeckung or system.key.startswith("de_bundestag"):
        result = bundestag_seat_allocation(
            party_votes,
            seats=seats,
            threshold=thr,
            minority_party_ids=minority,
            constituency_wins=constituency_wins,
            grundmandat_seats=system.grundmandat_seats or 0,
            land_votes=land_votes,
            land_direct_wins=land_direct_wins,
            total_votes=total_votes,
        )
        return result.party_seats

    method = system.allocation_method
    if method == AllocationMethod.SAINTE_LAGUE_SCHEPERS:
        return sainte_lague_schepers(
            party_votes,
            seats,
            thr,
            total_votes=total_votes,
            exempt_party_ids=minority,
            constituency_wins=constituency_wins,
            grundmandat_seats=system.grundmandat_seats,
        )
    if method == AllocationMethod.DHONDT:
        return dhondt(
            party_votes,
            seats,
            thr,
            total_votes=total_votes,
            exempt_party_ids=minority,
        )
    if method == AllocationMethod.HARE_NIEMEYER:
        return hare_niemeyer(
            party_votes,
            seats,
            thr,
            total_votes=total_votes,
            exempt_party_ids=minority,
        )
    raise ValueError(f"Unbekanntes allocation_method: {method}")
