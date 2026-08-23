"""Tests für analysis.uncertainty."""

from __future__ import annotations

import math

from analysis.seat_allocation import sainte_lague_schepers
from analysis.uncertainty import (
    UncertaintyConfig,
    party_uncertainties_from_means,
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
