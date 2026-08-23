"""Unit-Tests für analysis.averages — isolierte Gewichtungsformel."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from analysis.averages import (
    AverageConfig,
    PollObservationPoint,
    compute_swing,
    house_weight,
    loess_smooth,
    party_averages_for_parliament,
    point_weight,
    recency_weight,
    sample_weight,
    weighted_mean,
    weighted_party_average,
)
from data_pipeline.reference.election_results import (
    ElectionResult,
    load_election_results,
)


def test_recency_weight_halves_at_half_life():
    half_life = 14.0
    assert recency_weight(0.0, half_life) == pytest.approx(1.0)
    assert recency_weight(half_life, half_life) == pytest.approx(0.5)
    assert recency_weight(2 * half_life, half_life) == pytest.approx(0.25)


def test_sample_weight_sqrt():
    assert sample_weight(100) == pytest.approx(10.0)
    assert sample_weight(None, floor=1) == pytest.approx(1.0)
    assert sample_weight(0, floor=4) == pytest.approx(2.0)


def test_house_weight_neutral_when_missing():
    assert house_weight(None) == 1.0
    assert house_weight(1.5) == pytest.approx(1.5)
    assert house_weight(0.0) == pytest.approx(1e-6)
    assert house_weight(2.0, enabled=False) == 1.0


def test_weighted_mean_known_values():
    assert weighted_mean([40.0, 20.0], [10.0, 5.0]) == pytest.approx(100.0 / 3.0)


def test_weighted_party_average_with_known_formula():
    """
    Zwei Umfragen, gleiches n, Referenz = Tag der neueren Umfrage.
    Halbwertszeit 10 Tage, ältere Umfrage genau 10 Tage alt → recency 0.5.
    house neutral.

    w_A = 1.0 * 10 * 1 = 10
    w_B = 0.5 * 10 * 1 = 5
    avg = (40*10 + 20*5) / 15 = 33.333…
    """
    ref = date(2026, 1, 20)
    points = [
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:cdu_csu",
            share=40.0,
            as_of=ref,
            sample_size=100,
        ),
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:cdu_csu",
            share=20.0,
            as_of=ref - timedelta(days=10),
            sample_size=100,
        ),
    ]
    cfg = AverageConfig(half_life_days=10.0)
    avg, total_w, n = weighted_party_average(points, reference_date=ref, config=cfg)
    assert n == 2
    assert total_w == pytest.approx(15.0)
    assert avg == pytest.approx(100.0 / 3.0)


def test_point_weight_combines_all_factors():
    ref = date(2026, 1, 1)
    point = PollObservationPoint(
        parliament_id="x",
        party_id="p",
        share=10.0,
        as_of=ref - timedelta(days=14),
        sample_size=100,
        house_effect_score=2.0,
    )
    cfg = AverageConfig(half_life_days=14.0)
    w = point_weight(point, reference_date=ref, config=cfg)
    assert w.recency == pytest.approx(0.5)
    assert w.sample == pytest.approx(10.0)
    assert w.house == pytest.approx(2.0)
    assert w.total == pytest.approx(0.5 * 10.0 * 2.0)


def test_swing_vs_election():
    assert compute_swing(32.0, 28.5) == pytest.approx(3.5)
    assert compute_swing(20.0, 20.8) == pytest.approx(-0.8)


def test_party_averages_include_swing_from_reference():
    ref = date(2026, 6, 1)
    election = ElectionResult(
        parliament_id="de_bundestag",
        election_date=date(2025, 2, 23),
        label="Testwahl",
        results={"de:spd": 16.4, "de:afd": 20.8},
    )
    points = [
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:spd",
            share=18.0,
            as_of=ref,
            sample_size=1000,
        ),
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:afd",
            share=22.0,
            as_of=ref,
            sample_size=1000,
        ),
    ]
    rows = party_averages_for_parliament(
        points,
        parliament_id="de_bundestag",
        reference_date=ref,
        election=election,
    )
    by_party = {r.party_id: r for r in rows}
    assert by_party["de:spd"].average_share == pytest.approx(18.0)
    assert by_party["de:spd"].swing == pytest.approx(18.0 - 16.4)
    assert by_party["de:afd"].swing == pytest.approx(22.0 - 20.8)


def test_loess_smooth_constant_series():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(5)]
    values = [30.0] * 5
    smoothed = loess_smooth(dates, values, bandwidth_days=7.0)
    assert len(smoothed) == 5
    for _, trend, _ in smoothed:
        assert trend == pytest.approx(30.0)


def test_election_results_yaml_loads_bundestag():
    bundle = load_election_results()
    bt = next(e for e in bundle.elections if e.parliament_id == "de_bundestag")
    assert bt.election_date == date(2025, 2, 23)
    assert bt.results["de:afd"] == pytest.approx(20.8)
    assert bt.results["de:cdu_csu"] == pytest.approx(28.52)
