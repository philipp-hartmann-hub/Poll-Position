"""Tests für Wahlabend-Unsicherheit (feste 18-Uhr-SD)."""

from __future__ import annotations

import pytest

from analysis.uncertainty import (
    WAHLABEND_SD_PP,
    party_uncertainties_election_night,
    party_uncertainties_from_means,
    total_sd_pp,
)


def test_wahlabend_sd_in_target_band():
    """Modell-SD liegt im Band 1,5–2 Pp (WAHLABEND_SD_PP)."""
    assert 1.5 <= WAHLABEND_SD_PP <= 2.0
    parties = party_uncertainties_election_night({"a": 35.0, "b": 5.0, "c": 12.0})
    for p in parties:
        sd = total_sd_pp(p.mean_share, p.sample_size, p.house_variance)
        assert sd == pytest.approx(WAHLABEND_SD_PP, abs=1e-9)


def test_wahlabend_sd_tighter_than_poll_sd():
    """Wahlabend-SD ist spürbar enger als typische Umfrage-SD (gleiche Mittelwerte)."""
    means = {"x": 30.0, "y": 4.8}
    night = party_uncertainties_election_night(means)
    # Typische Umfrage: sample_size=1000 + Institutsstreuung → Gesamt-SD ~4–6 Pp
    poll = party_uncertainties_from_means(means, sample_size=1000, house_variance=16.0)
    for n, p in zip(night, poll, strict=True):
        night_sd = total_sd_pp(n.mean_share, n.sample_size, n.house_variance)
        poll_sd = total_sd_pp(p.mean_share, p.sample_size, p.house_variance)
        assert night_sd < poll_sd - 1.5
        assert 1.5 <= night_sd <= 2.0
