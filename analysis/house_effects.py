"""Institut-House-Effects und Backtesting gegen Wahlergebnisse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Mapping, Sequence

from analysis.averages import PollObservationPoint


@dataclass(frozen=True)
class HouseEffectEstimate:
    institute_id: str
    party_id: str
    as_of: date
    window_days: int
    institute_share: float
    peer_average: float
    house_effect: float
    """institut_share − peer_average (Prozentpunkte)."""

    n_peer_surveys: int


@dataclass(frozen=True)
class BacktestRecord:
    institute_id: str
    parliament_id: str
    election_date: date
    party_id: str
    poll_share: float
    election_share: float
    error_pp: float
    """poll − election in Prozentpunkten."""

    poll_date: date
    survey_id: str | None


@dataclass(frozen=True)
class InstituteAccuracy:
    institute_id: str
    parliament_id: str | None
    n_comparisons: int
    mae: float
    """Mean Absolute Error in Prozentpunkten."""

    rmse: float
    score: float
    """Genauigkeits-Score: 1 / (1 + mae), höher = besser."""


def _in_window(as_of: date, center: date, window_days: int) -> bool:
    return abs((as_of - center).days) <= window_days


def compute_house_effects(
    points: Sequence[PollObservationPoint],
    *,
    window_days: int = 14,
    reference_dates: Sequence[date] | None = None,
) -> list[HouseEffectEstimate]:
    """
    Rollierendes Fenster: je Institut/Partei Abweichung vom Durchschnitt
    der *anderen* Institute im Zeitfenster um `as_of`.
    """
    if window_days < 0:
        raise ValueError("window_days muss >= 0 sein")

    usable = [p for p in points if p.institute_id and p.share is not None]
    if not usable:
        return []

    dates = reference_dates or sorted({p.as_of for p in usable})
    results: list[HouseEffectEstimate] = []

    for center in dates:
        window = [p for p in usable if _in_window(p.as_of, center, window_days)]
        by_party: dict[str, list[PollObservationPoint]] = {}
        for p in window:
            by_party.setdefault(p.party_id, []).append(p)

        for party_id, party_points in by_party.items():
            institutes = sorted({p.institute_id for p in party_points if p.institute_id})
            for inst in institutes:
                own = [p.share for p in party_points if p.institute_id == inst]
                peers = [p.share for p in party_points if p.institute_id != inst]
                if not own or not peers:
                    continue
                own_avg = sum(own) / len(own)
                peer_avg = sum(peers) / len(peers)
                results.append(
                    HouseEffectEstimate(
                        institute_id=inst,
                        party_id=party_id,
                        as_of=center,
                        window_days=window_days,
                        institute_share=own_avg,
                        peer_average=peer_avg,
                        house_effect=own_avg - peer_avg,
                        n_peer_surveys=len(peers),
                    )
                )
    return results


def latest_poll_before_election(
    points: Sequence[PollObservationPoint],
    *,
    institute_id: str,
    parliament_id: str,
    election_date: date,
) -> dict[str, PollObservationPoint]:
    """Letzte Umfrage des Instituts vor dem Wahltag, je Partei (gleicher Survey bevorzugt)."""
    candidates = [
        p
        for p in points
        if p.institute_id == institute_id
        and p.parliament_id == parliament_id
        and p.as_of < election_date
    ]
    if not candidates:
        return {}

    # Bevorzuge den neuesten Survey (nach Datum, dann survey_id)
    latest_date = max(p.as_of for p in candidates)
    on_day = [p for p in candidates if p.as_of == latest_date]
    if any(p.survey_id for p in on_day):
        # häufigster/lexikographisch letzter survey_id an dem Tag
        survey_ids = sorted({p.survey_id for p in on_day if p.survey_id})
        chosen_id = survey_ids[-1]
        on_day = [p for p in on_day if p.survey_id == chosen_id]

    return {p.party_id: p for p in on_day}


def backtest_institutes(
    points: Sequence[PollObservationPoint],
    elections: Sequence[tuple[str, date, Mapping[str, float]]],
    *,
    max_days_before: int = 30,
) -> list[BacktestRecord]:
    """
    Vergleicht die letzte Umfrage jedes Instituts vor einer Wahl mit dem Ergebnis.

    elections: Iterable von (parliament_id, election_date, {party_id: share}).
    """
    records: list[BacktestRecord] = []
    institutes = sorted({p.institute_id for p in points if p.institute_id})

    for parliament_id, election_date, result in elections:
        for inst in institutes:
            latest = latest_poll_before_election(
                points,
                institute_id=inst,
                parliament_id=parliament_id,
                election_date=election_date,
            )
            if not latest:
                continue
            poll_date = next(iter(latest.values())).as_of
            if (election_date - poll_date).days > max_days_before:
                continue
            for party_id, election_share in result.items():
                if party_id not in latest:
                    continue
                poll_share = latest[party_id].share
                records.append(
                    BacktestRecord(
                        institute_id=inst,
                        parliament_id=parliament_id,
                        election_date=election_date,
                        party_id=party_id,
                        poll_share=poll_share,
                        election_share=float(election_share),
                        error_pp=poll_share - float(election_share),
                        poll_date=poll_date,
                        survey_id=latest[party_id].survey_id,
                    )
                )
    return records


def institute_accuracy_scores(
    records: Sequence[BacktestRecord],
    *,
    by_parliament: bool = False,
) -> list[InstituteAccuracy]:
    """Aggregiert MAE/RMSE und einen Genauigkeits-Score je Institut."""
    groups: dict[tuple[str, str | None], list[BacktestRecord]] = {}
    for r in records:
        key = (r.institute_id, r.parliament_id if by_parliament else None)
        groups.setdefault(key, []).append(r)

    scores: list[InstituteAccuracy] = []
    for (inst, parliament_id), rows in sorted(groups.items()):
        errors = [abs(r.error_pp) for r in rows]
        sq = [r.error_pp**2 for r in rows]
        mae = sum(errors) / len(errors)
        rmse = (sum(sq) / len(sq)) ** 0.5
        scores.append(
            InstituteAccuracy(
                institute_id=inst,
                parliament_id=parliament_id,
                n_comparisons=len(rows),
                mae=mae,
                rmse=rmse,
                score=1.0 / (1.0 + mae),
            )
        )
    scores.sort(key=lambda s: (-s.score, s.institute_id))
    return scores
