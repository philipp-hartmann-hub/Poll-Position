"""Regression: P(unverzichtbar für eine Mehrheit) aus Sitzverteilungen."""

from __future__ import annotations

import pytest

from analysis.coalitions import (
    CoalitionRulesConfig,
    ExclusionRule,
    ExclusionSet,
    PartyPosition,
    assign_exclusion_rule_ids,
)
from backend.services import party_indispensability_from_seat_distributions


def _kingmaker_config() -> CoalitionRulesConfig:
    """Zwei Blöcke schließen sich aus; nur die kleine Partei verbindet beide."""
    return assign_exclusion_rule_ids(
        CoalitionRulesConfig(
            version=1,
            party_positions={
                "de:linke": PartyPosition(left_right=1.0),
                "de:cdu_csu": PartyPosition(left_right=7.0),
                "de:fdp": PartyPosition(left_right=6.0),
            },
            exclusions=[
                ExclusionSet(
                    id="toy_blocks",
                    parliament_id="toy",
                    rules=[
                        ExclusionRule(party="de:linke", excludes=["de:cdu_csu"]),
                        ExclusionRule(party="de:cdu_csu", excludes=["de:linke"]),
                    ],
                )
            ],
        )
    )


def test_indispensability_kingmaker_near_one():
    """Kleine Partei ist in jeder erlaubten Mehrheit → ~100 %."""
    names = {
        "left": "Linke",
        "right": "CDU/CSU",
        "king": "FDP",
    }
    # 40+40+21 = 101; Mehrheit ab 51. Erlaubt: Linke+FDP, CDU+FDP. Nie Linke+CDU.
    draws = [{"left": 40, "right": 40, "king": 21} for _ in range(40)]
    out = party_indispensability_from_seat_distributions(
        draws,
        names,
        total_seats=101,
        parliament_id="toy",
        apply_exclusions=True,
        rules_config=_kingmaker_config(),
    )
    assert out["n_deadlock"] == 0
    assert out["n_simulations_considered"] == 40
    by_id = {e["party_id"]: e["probability"] for e in out["party_indispensability"]}
    assert by_id["de:fdp"] == 1.0
    assert by_id["de:linke"] == 0.0
    assert by_id["de:cdu_csu"] == 0.0


def test_indispensability_replaceable_near_zero():
    """Drei Parteien, jede Paar-Mehrheit möglich → niemand unverzichtbar."""
    names = {
        "a": "SPD",
        "b": "Grüne",
        "c": "FDP",
    }
    draws = [{"a": 35, "b": 35, "c": 30} for _ in range(30)]
    out = party_indispensability_from_seat_distributions(
        draws,
        names,
        total_seats=100,
        parliament_id="toy",
        apply_exclusions=False,
    )
    assert out["n_deadlock"] == 0
    by_id = {e["party_id"]: e["probability"] for e in out["party_indispensability"]}
    assert by_id["de:spd"] == 0.0
    assert by_id["de:gruene"] == 0.0
    assert by_id["de:fdp"] == 0.0


def test_indispensability_deadlock_excluded_from_denominator():
    """Ziehungen ohne erlaubte Mehrheit zählen nicht zum Nenner."""
    names = {
        "left": "Linke",
        "right": "CDU/CSU",
    }
    # Nur zwei Blöcke, die sich ausschließen → Deadlock.
    draws = [{"left": 50, "right": 50} for _ in range(25)]
    out = party_indispensability_from_seat_distributions(
        draws,
        names,
        total_seats=100,
        parliament_id="toy",
        apply_exclusions=True,
        rules_config=_kingmaker_config(),
    )
    assert out["n_deadlock"] == 25
    assert out["n_simulations_considered"] == 0
    assert out["party_indispensability"] == []


def test_indispensable_probability_prefers_id_to_canonical_over_raw_name():
    """DB-short_name ≠ Anzeigename → trotzdem Treffer über party_id_to_canonical."""
    from backend.services import _indispensable_probability_for_party

    indis = {"de:cdu": 0.815, "de:spd": 0.12}
    id_map = {"wh:cdu": "de:cdu", "wh:spd": "de:spd"}
    # Rohname absichtlich nicht in SHORT_TO_CANONICAL
    raw_names = {"wh:cdu": "Christlich Demokratische Union", "wh:spd": "SPD-Roh"}

    assert _indispensable_probability_for_party(
        "wh:cdu",
        indis_by_canon=indis,
        party_id_to_canonical=id_map,
        names=raw_names,
    ) == pytest.approx(0.815)
    # Ohne ID-Map und ohne bekannten Namen → 0
    assert (
        _indispensable_probability_for_party(
            "wh:cdu",
            indis_by_canon=indis,
            party_id_to_canonical={},
            names=raw_names,
        )
        == 0.0
    )
