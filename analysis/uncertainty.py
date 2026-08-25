"""Monte-Carlo-Unsicherheit um gewichtete Parteimittelwerte."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from analysis.coalitions import has_majority
from analysis.seat_allocation import sainte_lague_schepers


@dataclass(frozen=True)
class PartyUncertainty:
    """Verteilungsparameter einer Partei um den gewichteten Mittelwert."""

    party_id: str
    mean_share: float
    """Gewichteter Mittelwert in Prozent (0–100)."""

    sample_size: int
    """Effektive Stichprobe für den Standardfehler."""

    house_variance: float = 1.0
    """Zusätzliche Haus-/Methoden-Varianz in Prozentpunkt²."""


@dataclass(frozen=True)
class UncertaintyConfig:
    n_simulations: int = 1000
    seed: int | None = 42
    min_share: float = 0.0
    max_share: float = 100.0
    renormalize: bool = True
    """Nach dem Ziehen Anteile auf Summe der Ausgangssumme skalieren (optional)."""


def standard_error_pp(mean_share: float, sample_size: int) -> float:
    """
    Binomial-Standardfehler in Prozentpunkten: sqrt(p*(1-p)/n) * 100,
    wobei p = mean_share/100.
    """
    if sample_size <= 0:
        raise ValueError("sample_size muss > 0 sein")
    p = min(max(mean_share / 100.0, 1e-6), 1.0 - 1e-6)
    return 100.0 * math.sqrt(p * (1.0 - p) / sample_size)


def total_sd_pp(mean_share: float, sample_size: int, house_variance: float) -> float:
    """Gesamt-SD = sqrt(SE² + house_variance)."""
    se = standard_error_pp(mean_share, sample_size)
    return math.sqrt(se**2 + max(house_variance, 0.0))


def draw_share_vector(
    parties: Sequence[PartyUncertainty],
    rng: random.Random,
    *,
    min_share: float = 0.0,
    max_share: float = 100.0,
    renormalize: bool = True,
) -> dict[str, float]:
    """Zieht eine Anteilswerte-Vektor aus Normalverteilungen je Partei."""
    raw: dict[str, float] = {}
    for party in parties:
        sd = total_sd_pp(party.mean_share, party.sample_size, party.house_variance)
        drawn = rng.gauss(party.mean_share, sd)
        raw[party.party_id] = min(max(drawn, min_share), max_share)

    if renormalize and raw:
        target = sum(p.mean_share for p in parties)
        current = sum(raw.values())
        if current > 0 and target > 0:
            scale = target / current
            raw = {k: v * scale for k, v in raw.items()}
    return raw


SeatAllocator = Callable[[dict[str, float]], dict[str, int]]


def default_seat_allocator(
    seats: int = 630,
    threshold: float = 0.05,
) -> SeatAllocator:
    def _alloc(votes: dict[str, float]) -> dict[str, int]:
        return sainte_lague_schepers(votes, seats, threshold)

    return _alloc


@dataclass(frozen=True)
class CoalitionProbability:
    parties: tuple[str, ...]
    majority_probability: float
    """Anteil der Simulationen mit strikter Mehrheit (> 50 %)."""

    n_majority: int
    n_simulations: int


@dataclass(frozen=True)
class MonteCarloResult:
    n_simulations: int
    seat_distributions: list[dict[str, int]]
    mean_seats: dict[str, float]
    coalition_probabilities: list[CoalitionProbability]


def simulate_uncertainty(
    parties: Sequence[PartyUncertainty],
    coalitions: Sequence[Sequence[str]],
    *,
    allocate: SeatAllocator | None = None,
    total_seats: int | None = None,
    config: UncertaintyConfig | None = None,
) -> MonteCarloResult:
    """
    Monte-Carlo: Anteile ziehen → Sitzzuteilung → Mehrheitswahrscheinlichkeiten.

    `coalitions` sind feste Parteimengen (z. B. aus possible_majorities), deren
    Mehrheitsquote über die Simulationen geschätzt wird.
    """
    cfg = config or UncertaintyConfig()
    if cfg.n_simulations < 1:
        raise ValueError("n_simulations muss >= 1 sein")
    if not parties:
        raise ValueError("parties darf nicht leer sein")

    rng = random.Random(cfg.seed)
    allocator = allocate or default_seat_allocator()
    seat_runs: list[dict[str, int]] = []
    coalition_hits = {tuple(sorted(c)): 0 for c in coalitions}

    for _ in range(cfg.n_simulations):
        shares = draw_share_vector(
            parties,
            rng,
            min_share=cfg.min_share,
            max_share=cfg.max_share,
            renormalize=cfg.renormalize,
        )
        seats = allocator(shares)
        seat_runs.append(seats)
        chamber = total_seats if total_seats is not None else sum(seats.values())
        for key in coalition_hits:
            if has_majority(seats, list(key), total_seats=chamber):
                coalition_hits[key] += 1

    # Mittlere Sitze
    all_parties = sorted({p.party_id for p in parties} | {p for run in seat_runs for p in run})
    mean_seats = {
        p: sum(run.get(p, 0) for run in seat_runs) / cfg.n_simulations for p in all_parties
    }

    probs = [
        CoalitionProbability(
            parties=key,
            majority_probability=hits / cfg.n_simulations,
            n_majority=hits,
            n_simulations=cfg.n_simulations,
        )
        for key, hits in sorted(coalition_hits.items(), key=lambda kv: -kv[1])
    ]
    return MonteCarloResult(
        n_simulations=cfg.n_simulations,
        seat_distributions=seat_runs,
        mean_seats=mean_seats,
        coalition_probabilities=probs,
    )


def party_uncertainties_from_means(
    means: Mapping[str, float],
    *,
    sample_size: int,
    house_variance: float = 1.0,
) -> list[PartyUncertainty]:
    """Hilfsbauer: gleiche n/Hausvarianz für alle Parteien."""
    return [
        PartyUncertainty(
            party_id=pid,
            mean_share=float(share),
            sample_size=sample_size,
            house_variance=house_variance,
        )
        for pid, share in means.items()
    ]


@dataclass(frozen=True)
class ThresholdWatchRow:
    party_id: str
    mean_share: float
    threshold_percent: float
    probability_below_threshold: float
    n_below: int
    n_simulations: int


def simulate_threshold_watch(
    parties: Sequence[PartyUncertainty],
    *,
    threshold_percent: float,
    band_points: float = 3.0,
    exempt_party_ids: Sequence[str] = (),
    config: UncertaintyConfig | None = None,
) -> list[ThresholdWatchRow]:
    """
    Monte-Carlo: P(Anteil < Sperrklausel) für Parteien im ±band-Fenster.

    `exempt_party_ids` (Minderheiten / Grundmandat-Ausnahmen) werden nicht gewarnt.
    """
    if band_points < 0:
        raise ValueError("band_points muss >= 0 sein")
    cfg = config or UncertaintyConfig(n_simulations=400, seed=42)
    exempt = set(exempt_party_ids)
    watched = [
        p
        for p in parties
        if p.party_id not in exempt
        and abs(p.mean_share - threshold_percent) <= band_points
    ]
    if not watched:
        return []

    rng = random.Random(cfg.seed)
    hits = {p.party_id: 0 for p in watched}
    for _ in range(cfg.n_simulations):
        shares = draw_share_vector(
            parties,
            rng,
            min_share=cfg.min_share,
            max_share=cfg.max_share,
            renormalize=cfg.renormalize,
        )
        for p in watched:
            if shares.get(p.party_id, 0.0) < threshold_percent:
                hits[p.party_id] += 1

    rows = [
        ThresholdWatchRow(
            party_id=p.party_id,
            mean_share=p.mean_share,
            threshold_percent=threshold_percent,
            probability_below_threshold=hits[p.party_id] / cfg.n_simulations,
            n_below=hits[p.party_id],
            n_simulations=cfg.n_simulations,
        )
        for p in watched
    ]
    rows.sort(key=lambda r: -min(r.probability_below_threshold, 1.0 - r.probability_below_threshold))
    return rows


@dataclass(frozen=True)
class PartyForecastRow:
    party_id: str
    mean_share: float
    threshold_percent: float
    probability_strongest: float
    probability_above_threshold: float
    n_simulations: int


def simulate_party_forecast(
    parties: Sequence[PartyUncertainty],
    *,
    threshold_percent: float,
    exempt_party_ids: Sequence[str] = (),
    residual_party_ids: Sequence[str] = (),
    config: UncertaintyConfig | None = None,
) -> list[PartyForecastRow]:
    """Monte-Carlo: P(stärkste Kraft) und P(über Sperrklausel) aus denselben Ziehungen."""
    cfg = config or UncertaintyConfig(n_simulations=400, seed=42)
    residual = set(residual_party_ids)
    exempt = set(exempt_party_ids)
    ranked_ids = {p.party_id for p in parties if p.party_id not in residual}
    strongest_hits = {p.party_id: 0 for p in parties}
    above_hits = {p.party_id: 0 for p in parties}
    rng = random.Random(cfg.seed)
    for _ in range(cfg.n_simulations):
        shares = draw_share_vector(
            parties,
            rng,
            min_share=cfg.min_share,
            max_share=cfg.max_share,
            renormalize=cfg.renormalize,
        )
        candidates = {pid: s for pid, s in shares.items() if pid in ranked_ids}
        if candidates:
            strongest_hits[max(candidates, key=lambda pid: candidates[pid])] += 1
        for pid, s in shares.items():
            if pid in exempt or s >= threshold_percent:
                above_hits[pid] += 1
    n = cfg.n_simulations
    rows = [
        PartyForecastRow(
            party_id=p.party_id,
            mean_share=p.mean_share,
            threshold_percent=threshold_percent,
            probability_strongest=strongest_hits[p.party_id] / n,
            probability_above_threshold=above_hits[p.party_id] / n,
            n_simulations=n,
        )
        for p in parties
    ]
    rows.sort(key=lambda r: -r.mean_share)
    return rows
