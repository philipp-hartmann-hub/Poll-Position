"""Tests für Wahlabend-SD-Interpolation (analysis.uncertainty)."""

from __future__ import annotations

import pytest

from analysis.uncertainty import election_night_sd_pp, party_uncertainties_election_night


def test_election_night_sd_monotone_in_count_progress():
    """0 % → 50 % → 95 %: SD fällt monoton (Modellannahme)."""
    sd0 = election_night_sd_pp(0.0)
    sd50 = election_night_sd_pp(50.0)
    sd95 = election_night_sd_pp(95.0)
    assert 1.5 <= sd0 <= 2.0
    assert 0.05 <= sd95 <= 0.25
    assert sd0 > sd50 > sd95


def test_election_night_sd_clamps_progress():
    assert election_night_sd_pp(-10.0) == election_night_sd_pp(0.0)
    assert election_night_sd_pp(150.0) == election_night_sd_pp(100.0)


def test_election_night_uncertainties_use_fixed_sd():
    parties = party_uncertainties_election_night(
        {"a": 35.0, "b": 30.0}, count_progress_percent=20.0
    )
    sd = election_night_sd_pp(20.0)
    assert all(p.fixed_sd_pp == pytest.approx(sd) for p in parties)
    assert all(p.house_variance == 0.0 for p in parties)
