"""Tests für analysis.scenario (Was-wäre-wenn)."""

from __future__ import annotations

from analysis.coalitions import CoalitionRulesConfig
from analysis.scenario import ScenarioInput, run_scenario


def test_run_scenario_override_changes_seats_and_coalitions():
    base = run_scenario(
        {"A": 36.0, "B": 34.0, "C": 26.0, "D": 4.0},
        total_seats=100,
        threshold=0.05,
        apply_exclusions=False,
        parliament_id="toy",
    )
    assert sum(base.seats.values()) == 100
    assert base.seats["D"] == 0  # 4 % unter 5 %-Hürde → 0 Sitze

    boosted = run_scenario(
        ScenarioInput(
            party_shares={"A": 36.0, "B": 34.0, "C": 26.0, "D": 4.0},
            parliament_id="toy",
            total_seats=100,
            threshold=0.0,  # Override: keine Hürde
        ),
        apply_exclusions=False,
    )
    assert boosted.seats["D"] > 0
    assert sum(boosted.seats.values()) == 100

    # User-Override: A stark erhöhen → Einparteienmehrheit möglich
    landslide = run_scenario(
        {"A": 55.0, "B": 25.0, "C": 20.0},
        total_seats=100,
        threshold=0.0,
        apply_exclusions=False,
        rules_config=CoalitionRulesConfig(),
    )
    singles = [c for c in landslide.majorities.minimal_winning if c.parties == ("A",)]
    assert singles
    assert singles[0].seats > 50
