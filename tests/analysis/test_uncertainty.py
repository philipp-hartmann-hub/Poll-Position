"""Tests für analysis.uncertainty."""

from __future__ import annotations

import math

from analysis.seat_allocation import sainte_lague_schepers
from analysis.uncertainty import (
    UncertaintyConfig,
    party_uncertainties_from_means,
    simulate_party_forecast,
    simulate_threshold_watch,
    simulate_uncertainty,
    standard_error_pp,
    total_sd_pp,
)


def test_standard_error_and_house_variance():
    se = standard_error_pp(50.0, 100)
    assert se == math.sqrt(0.5 * 0.5 / 100) * 100
    sd = total_sd_pp(50.0, 100, house_variance=4.0)
    assert sd == math.sqrt(se**2 + 4.0)


def test_monte_carlo_coalition_probability_deterministic_seed():
    means = {"A": 40.0, "B": 35.0, "C": 25.0}
    parties = party_uncertainties_from_means(means, sample_size=2000, house_variance=0.25)
    coalitions = [("A", "B"), ("A", "C"), ("B", "C")]

    def alloc(votes: dict[str, float]) -> dict[str, int]:
        return sainte_lague_schepers(votes, 100, threshold=0.0)

    result = simulate_uncertainty(
        parties,
        coalitions,
        allocate=alloc,
        total_seats=100,
        config=UncertaintyConfig(n_simulations=200, seed=7, renormalize=True),
    )
    assert result.n_simulations == 200
    assert len(result.seat_distributions) == 200
    assert abs(sum(result.mean_seats.values()) - 100) < 1e-6
    probs = {c.parties: c.majority_probability for c in result.coalition_probabilities}
    # A+B ist klar über 50 % — Wahrscheinlichkeit sollte hoch sein
    assert probs[("A", "B")] > 0.8
    assert 0.0 <= probs[("B", "C")] <= 1.0


def test_simulate_threshold_watch_band_and_exempt():
    """Nur Parteien im Band; Exempt und weit entfernte fehlen."""
    means = {
        "near_under": 4.2,
        "near_over": 6.5,
        "far": 25.0,
        "exempt": 4.1,
    }
    parties = party_uncertainties_from_means(
        means, sample_size=8000, house_variance=0.05
    )
    rows = simulate_threshold_watch(
        parties,
        threshold_percent=5.0,
        band_points=3.0,
        exempt_party_ids=["exempt"],
        config=UncertaintyConfig(n_simulations=300, seed=1, renormalize=False),
    )
    ids = {r.party_id for r in rows}
    assert ids == {"near_under", "near_over"}
    under = next(r for r in rows if r.party_id == "near_under")
    over = next(r for r in rows if r.party_id == "near_over")
    assert under.probability_below_threshold > 0.5
    assert over.probability_below_threshold < 0.5


def test_simulate_party_forecast_strongest_sums_near_one():
    means = {"A": 38.0, "B": 28.0, "C": 22.0, "D": 12.0}
    parties = party_uncertainties_from_means(
        means, sample_size=5000, house_variance=0.2
    )
    rows = simulate_party_forecast(
        parties,
        threshold_percent=5.0,
        config=UncertaintyConfig(n_simulations=500, seed=11, renormalize=True),
    )
    assert len(rows) == 4
    total_strongest = sum(r.probability_strongest for r in rows)
    assert abs(total_strongest - 1.0) < 1e-9
    assert rows[0].party_id == "A"
    assert all(0.0 <= r.probability_strongest <= 1.0 for r in rows)
    assert all(0.0 <= r.probability_above_threshold <= 1.0 for r in rows)


def test_simulate_party_forecast_clear_leader_near_one():
    means = {"leader": 48.0, "mid": 22.0, "low": 18.0, "tiny": 12.0}
    parties = party_uncertainties_from_means(
        means, sample_size=20000, house_variance=0.05
    )
    rows = simulate_party_forecast(
        parties,
        threshold_percent=5.0,
        residual_party_ids=[],
        config=UncertaintyConfig(n_simulations=400, seed=3, renormalize=True),
    )
    leader = next(r for r in rows if r.party_id == "leader")
    assert leader.probability_strongest > 0.95
    assert leader.probability_above_threshold > 0.99
