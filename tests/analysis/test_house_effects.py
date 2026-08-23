"""Tests für analysis.house_effects."""

from __future__ import annotations

from datetime import date

from analysis.averages import PollObservationPoint
from analysis.house_effects import (
    backtest_institutes,
    compute_house_effects,
    institute_accuracy_scores,
)


def test_house_effect_deviation_from_peer_average():
    points = [
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:spd",
            share=20.0,
            as_of=date(2026, 1, 10),
            institute_id="inst_a",
            survey_id="s1",
        ),
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:spd",
            share=16.0,
            as_of=date(2026, 1, 11),
            institute_id="inst_b",
            survey_id="s2",
        ),
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:spd",
            share=16.0,
            as_of=date(2026, 1, 12),
            institute_id="inst_c",
            survey_id="s3",
        ),
    ]
    effects = compute_house_effects(points, window_days=14, reference_dates=[date(2026, 1, 12)])
    by_inst = {(e.institute_id, e.party_id): e for e in effects}
    assert by_inst[("inst_a", "de:spd")].house_effect == 20.0 - 16.0
    assert by_inst[("inst_a", "de:spd")].peer_average == 16.0


def test_backtest_accuracy_score():
    points = [
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:spd",
            share=18.0,
            as_of=date(2025, 2, 1),
            institute_id="fgw",
            survey_id="pre",
        ),
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="de:cdu_csu",
            share=30.0,
            as_of=date(2025, 2, 1),
            institute_id="fgw",
            survey_id="pre",
        ),
    ]
    elections = [
        (
            "de_bundestag",
            date(2025, 2, 23),
            {"de:spd": 16.4, "de:cdu_csu": 28.5},
        )
    ]
    records = backtest_institutes(points, elections, max_days_before=40)
    assert len(records) == 2
    assert records[0].error_pp == 18.0 - 16.4 or any(r.error_pp == 18.0 - 16.4 for r in records)
    scores = institute_accuracy_scores(records)
    assert scores[0].institute_id == "fgw"
    assert scores[0].mae > 0
    assert 0 < scores[0].score < 1
