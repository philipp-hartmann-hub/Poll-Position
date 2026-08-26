"""Gewichtete Umfrage-Durchschnitte, Trends und Swing (UI-frei)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable, Sequence

from data_pipeline.reference.election_results import (
    ElectionResult,
    latest_election_for,
    load_election_results,
)


@dataclass(frozen=True)
class AverageConfig:
    """Konfiguration der Gewichtungsformel."""

    half_life_days: float = 14.0
    """Exponentieller Zeitverfall: Gewicht halbiert sich alle `half_life_days`."""

    sample_size_floor: int = 1
    """Mindest-n, falls Stichprobe fehlt oder 0."""

    use_house_effect: bool = True
    """Wenn False, immer Institutsgewicht 1.0."""

    trend_bandwidth_days: float = 21.0
    """Bandbreite für LOESS-/Kernel-Trend (in Tagen)."""


@dataclass(frozen=True)
class PollObservationPoint:
    """Eine Partei-Beobachtung aus einer Umfrage (für Averaging)."""

    parliament_id: str
    party_id: str
    share: float
    as_of: date
    sample_size: int | None = None
    house_effect_score: float | None = None
    survey_id: str | None = None
    institute_id: str | None = None


@dataclass(frozen=True)
class WeightBreakdown:
    recency: float
    sample: float
    house: float

    @property
    def total(self) -> float:
        return self.recency * self.sample * self.house


@dataclass(frozen=True)
class PartyAverage:
    parliament_id: str
    party_id: str
    as_of: date
    average_share: float
    n_surveys: int
    total_weight: float
    swing: float | None
    election_share: float | None
    election_date: date | None
    election_label: str | None


@dataclass(frozen=True)
class PartyTrendPoint:
    parliament_id: str
    party_id: str
    as_of: date
    trend_share: float
    n_surveys_in_window: int


def recency_weight(age_days: float, half_life_days: float) -> float:
    """Exponentieller Verfall: w = 2^(-age / half_life) = exp(-ln(2) * age / half_life)."""
    if half_life_days <= 0:
        raise ValueError("half_life_days muss > 0 sein")
    if age_days < 0:
        age_days = 0.0
    return math.exp(-math.log(2.0) * age_days / half_life_days)


def sample_weight(sample_size: int | None, *, floor: int = 1) -> float:
    """Gewicht ∝ sqrt(n); fehlende Stichprobe → sqrt(floor)."""
    n = sample_size if sample_size is not None and sample_size > 0 else floor
    return math.sqrt(float(n))


def house_weight(house_effect_score: float | None, *, enabled: bool = True) -> float:
    """
    Instituts-Zuverlässigkeit.

    - None oder disabled → 1.0 (neutral)
    - sonst max(score, ε), Score als multiplikativer Faktor (höher = vertrauenswürdiger)
    """
    if not enabled or house_effect_score is None:
        return 1.0
    return max(float(house_effect_score), 1e-6)


def point_weight(
    point: PollObservationPoint,
    *,
    reference_date: date,
    config: AverageConfig | None = None,
) -> WeightBreakdown:
    cfg = config or AverageConfig()
    age = (reference_date - point.as_of).days
    return WeightBreakdown(
        recency=recency_weight(float(age), cfg.half_life_days),
        sample=sample_weight(point.sample_size, floor=cfg.sample_size_floor),
        house=house_weight(point.house_effect_score, enabled=cfg.use_house_effect),
    )


def weighted_mean(shares: Sequence[float], weights: Sequence[float]) -> float:
    if len(shares) != len(weights):
        raise ValueError("shares und weights müssen gleich lang sein")
    if not shares:
        raise ValueError("keine Beobachtungen")
    total_w = sum(weights)
    if total_w <= 0:
        raise ValueError("Summe der Gewichte muss > 0 sein")
    return sum(s * w for s, w in zip(shares, weights, strict=True)) / total_w


def weighted_party_average(
    points: Sequence[PollObservationPoint],
    *,
    reference_date: date | None = None,
    config: AverageConfig | None = None,
) -> tuple[float, float, int]:
    """
    Gewichteter Mittelwert für eine Partei.

    Returns:
        (average_share, total_weight, n_surveys)
    """
    if not points:
        raise ValueError("points darf nicht leer sein")
    cfg = config or AverageConfig()
    ref = reference_date or max(p.as_of for p in points)
    weights = [point_weight(p, reference_date=ref, config=cfg).total for p in points]
    avg = weighted_mean([p.share for p in points], weights)
    return avg, sum(weights), len(points)


def weighted_variance(
    shares: Sequence[float], weights: Sequence[float], mean: float
) -> float:
    total_w = sum(weights)
    if total_w <= 0:
        return 0.0
    return sum(w * (s - mean) ** 2 for s, w in zip(shares, weights, strict=True)) / total_w


def party_dispersion_for_parliament(
    points: Sequence[PollObservationPoint],
    *,
    parliament_id: str,
    reference_date: date | None = None,
    config: AverageConfig | None = None,
    min_observations: int = 3,
    fallback_variance_pp2: float = 4.0,
    floor_variance_pp2: float = 1.0,
    cap_variance_pp2: float = 25.0,
) -> dict[str, float]:
    """
    Empirische Streuung je Partei (Prozentpunkt^2) aus den einzelnen Umfrage-
    Beobachtungen — ersetzt eine für alle Parteien gleiche Pauschal-Varianz in
    der Monte-Carlo-Unsicherheit. Bei < min_observations Beobachtungen (zu
    wenig, um Streuung zu schätzen) wird fallback_variance_pp2 verwendet.
    Ergebnis wird auf [floor_variance_pp2, cap_variance_pp2] geklemmt, damit
    weder zufällig übereinstimmende Institute falsche Präzision vorgaukeln
    noch ein einzelner Ausreißer die Unsicherheit sprengt.
    """
    cfg = config or AverageConfig()
    scoped = [p for p in points if p.parliament_id == parliament_id]
    if not scoped:
        return {}
    ref = reference_date or max(p.as_of for p in scoped)
    by_party: dict[str, list[PollObservationPoint]] = {}
    for p in scoped:
        by_party.setdefault(p.party_id, []).append(p)

    out: dict[str, float] = {}
    for party_id, party_points in by_party.items():
        if len(party_points) < min_observations:
            out[party_id] = fallback_variance_pp2
            continue
        weights = [
            point_weight(p, reference_date=ref, config=cfg).total for p in party_points
        ]
        mean, _, _ = weighted_party_average(
            party_points, reference_date=ref, config=cfg
        )
        var = weighted_variance([p.share for p in party_points], weights, mean)
        out[party_id] = min(max(var, floor_variance_pp2), cap_variance_pp2)
    return out


def _tricube(u: float) -> float:
    """Tricube-Kernel für LOESS: (1 - |u|^3)^3 für |u| < 1."""
    au = abs(u)
    if au >= 1.0:
        return 0.0
    return (1.0 - au**3) ** 3


def loess_smooth(
    dates: Sequence[date],
    values: Sequence[float],
    *,
    bandwidth_days: float,
    eval_dates: Sequence[date] | None = None,
    point_weights: Sequence[float] | None = None,
) -> list[tuple[date, float, int]]:
    """
    Einfache LOESS-ähnliche Glättung (lokal gewichteter Mittelwert mit Tricube-Kernel).

    Keine externe Stats-Abhängigkeit; für lineare Trends reicht der gewichtete Mittelwert
    in der Bandbreite. `point_weights` multipliziert den Kernel (z. B. Survey-Gewichte).
    """
    if len(dates) != len(values):
        raise ValueError("dates und values müssen gleich lang sein")
    if not dates:
        return []
    if bandwidth_days <= 0:
        raise ValueError("bandwidth_days muss > 0 sein")

    base_w = list(point_weights) if point_weights is not None else [1.0] * len(dates)
    if len(base_w) != len(dates):
        raise ValueError("point_weights muss gleich lang wie dates sein")

    targets = list(eval_dates) if eval_dates is not None else sorted(set(dates))
    origin = min(dates)
    xs = [(d - origin).days for d in dates]
    out: list[tuple[date, float, int]] = []

    for target in targets:
        xt = (target - origin).days
        kernel_weights: list[float] = []
        for x, bw in zip(xs, base_w, strict=True):
            u = (x - xt) / bandwidth_days
            kernel_weights.append(_tricube(u) * bw)
        n_eff = sum(1 for w in kernel_weights if w > 0)
        if n_eff == 0 or sum(kernel_weights) <= 0:
            # Fallback: nächster Punkt
            nearest = min(range(len(dates)), key=lambda i: abs(xs[i] - xt))
            out.append((target, values[nearest], 1))
        else:
            out.append((target, weighted_mean(values, kernel_weights), n_eff))
    return out


def compute_swing(average_share: float, election_share: float) -> float:
    """Swing in Prozentpunkten: aktueller Schnitt − Wahlergebnis."""
    return average_share - election_share


def party_averages_for_parliament(
    points: Sequence[PollObservationPoint],
    *,
    parliament_id: str,
    reference_date: date | None = None,
    config: AverageConfig | None = None,
    election: ElectionResult | None = None,
) -> list[PartyAverage]:
    """Gewichtete Durchschnitte je Partei für ein Parlament inkl. optionalem Swing."""
    cfg = config or AverageConfig()
    scoped = [p for p in points if p.parliament_id == parliament_id]
    if not scoped:
        return []
    ref = reference_date or max(p.as_of for p in scoped)
    election = election or latest_election_for(parliament_id)

    by_party: dict[str, list[PollObservationPoint]] = {}
    for p in scoped:
        by_party.setdefault(p.party_id, []).append(p)

    rows: list[PartyAverage] = []
    for party_id, party_points in sorted(by_party.items()):
        avg, total_w, n = weighted_party_average(
            party_points, reference_date=ref, config=cfg
        )
        election_share = None
        swing = None
        election_date = None
        election_label = None
        if election is not None and party_id in election.results:
            election_share = election.results[party_id]
            swing = compute_swing(avg, election_share)
            election_date = election.election_date
            election_label = election.label
        rows.append(
            PartyAverage(
                parliament_id=parliament_id,
                party_id=party_id,
                as_of=ref,
                average_share=avg,
                n_surveys=n,
                total_weight=total_w,
                swing=swing,
                election_share=election_share,
                election_date=election_date,
                election_label=election_label,
            )
        )
    return rows


def party_trends_for_parliament(
    points: Sequence[PollObservationPoint],
    *,
    parliament_id: str,
    config: AverageConfig | None = None,
    eval_dates: Sequence[date] | None = None,
) -> list[PartyTrendPoint]:
    """Geglättete Trendlinie je Partei (LOESS-/Tricube über der Zeit)."""
    cfg = config or AverageConfig()
    scoped = [p for p in points if p.parliament_id == parliament_id]
    by_party: dict[str, list[PollObservationPoint]] = {}
    for p in scoped:
        by_party.setdefault(p.party_id, []).append(p)

    rows: list[PartyTrendPoint] = []
    for party_id, party_points in sorted(by_party.items()):
        ordered = sorted(party_points, key=lambda p: p.as_of)
        ref = ordered[-1].as_of
        weights = [
            point_weight(p, reference_date=ref, config=cfg).total for p in ordered
        ]
        smoothed = loess_smooth(
            [p.as_of for p in ordered],
            [p.share for p in ordered],
            bandwidth_days=cfg.trend_bandwidth_days,
            eval_dates=eval_dates,
            point_weights=weights,
        )
        for as_of, trend_share, n_win in smoothed:
            rows.append(
                PartyTrendPoint(
                    parliament_id=parliament_id,
                    party_id=party_id,
                    as_of=as_of,
                    trend_share=trend_share,
                    n_surveys_in_window=n_win,
                )
            )
    return rows


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def averages_to_rows(averages: Iterable[PartyAverage]) -> list[dict]:
    now = _utc_now()
    return [
        {
            "parliament_id": a.parliament_id,
            "party_id": a.party_id,
            "as_of": a.as_of,
            "average_share": a.average_share,
            "n_surveys": a.n_surveys,
            "total_weight": a.total_weight,
            "swing": a.swing,
            "election_share": a.election_share,
            "election_date": a.election_date,
            "election_label": a.election_label,
            "updated_at": now,
        }
        for a in averages
    ]


def trends_to_rows(trends: Iterable[PartyTrendPoint]) -> list[dict]:
    now = _utc_now()
    return [
        {
            "parliament_id": t.parliament_id,
            "party_id": t.party_id,
            "as_of": t.as_of,
            "trend_share": t.trend_share,
            "n_surveys_in_window": t.n_surveys_in_window,
            "updated_at": now,
        }
        for t in trends
    ]


def load_poll_points_from_warehouse(con) -> list[PollObservationPoint]:
    """Liest Silver-Surveys (+ optionales house_effect) als Averaging-Punkte."""
    rows = con.execute(
        """
        SELECT
            s.parliament_id,
            r.party_id,
            r.share,
            COALESCE(s.field_date_to, s.publication_date) AS as_of,
            s.sample_size,
            i.house_effect_score,
            s.id AS survey_id,
            s.institute_id
        FROM surveys s
        JOIN survey_results r ON r.survey_id = s.id
        LEFT JOIN institutes i ON i.id = s.institute_id
        WHERE r.share IS NOT NULL
        """
    ).fetchall()
    points: list[PollObservationPoint] = []
    for row in rows:
        points.append(
            PollObservationPoint(
                parliament_id=row[0],
                party_id=row[1],
                share=float(row[2]),
                as_of=row[3],
                sample_size=row[4],
                house_effect_score=row[5],
                survey_id=row[6],
                institute_id=row[7],
            )
        )
    return points


def compute_all_averages_and_trends(
    points: Sequence[PollObservationPoint],
    *,
    reference_date: date | None = None,
    config: AverageConfig | None = None,
) -> tuple[list[PartyAverage], list[PartyTrendPoint]]:
    cfg = config or AverageConfig()
    parliaments = sorted({p.parliament_id for p in points})
    # Wahlen einmal laden (Cache für latest_election_for)
    _ = load_election_results()
    averages: list[PartyAverage] = []
    trends: list[PartyTrendPoint] = []
    for pid in parliaments:
        averages.extend(
            party_averages_for_parliament(
                points,
                parliament_id=pid,
                reference_date=reference_date,
                config=cfg,
            )
        )
        trends.extend(
            party_trends_for_parliament(points, parliament_id=pid, config=cfg)
        )
    return averages, trends
