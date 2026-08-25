"""Tests für analysis.bundesrat."""

from __future__ import annotations

from analysis.bundesrat import (
    coalition_key,
    load_bundesrat_config,
    simulate_bundesrat,
)


def test_load_bundesrat_config_16_states_69_votes():
    cfg = load_bundesrat_config()
    assert len(cfg.states) == 16
    assert sum(s.votes for s in cfg.states) == 69
    assert cfg.majority_simple == 35
    assert cfg.majority_two_thirds == 46
    assert {s.votes for s in cfg.states} <= {3, 4, 5, 6}


def test_default_all_yes_has_simple_majority():
    cfg = load_bundesrat_config()
    tally = simulate_bundesrat(cfg)
    assert tally.yes == 69
    assert tally.no == 0
    assert tally.abstain == 0
    assert tally.has_simple_majority
    assert tally.has_two_thirds_majority


def test_abstain_and_reject_split_votes():
    cfg = load_bundesrat_config()
    # NW=6, BY=6, SL=3
    tally = simulate_bundesrat(
        cfg,
        choices={
            "de_nw_landtag": "abstain",
            "de_by_landtag": "nein",
            "de_sl_landtag": "default",
        },
    )
    assert tally.abstain == 6
    assert tally.no == 6
    assert tally.yes == 69 - 12
    assert tally.has_simple_majority  # 57 >= 35
    assert tally.has_two_thirds_majority  # 57 >= 46


def test_coalition_override_key():
    cfg = load_bundesrat_config()
    key = coalition_key(["de:spd", "de:gruene"])
    assert key == "de:gruene+de:spd"
    tally = simulate_bundesrat(
        cfg,
        choices={"de_hh_buergerschaft": key},
        coalition_labels={key: "SPD + Grüne (Umfrage)"},
    )
    hh = next(s for s in tally.states if s.parliament_id == "de_hh_buergerschaft")
    assert hh.source == "override"
    assert set(hh.parties) == {"de:spd", "de:gruene"}
    assert hh.stance == "yes"
    assert "Umfrage" in hh.government_label
