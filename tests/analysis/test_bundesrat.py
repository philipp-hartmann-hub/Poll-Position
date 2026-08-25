"""Tests für analysis.bundesrat."""

from __future__ import annotations

import pytest

from analysis.bundesrat import (
    choices_for_coalition,
    coalition_key,
    group_votes_by_coalition,
    informal_coalition_label,
    load_bundesrat_config,
    normalize_parties_for_color,
    simulate_bundesrat,
)


@pytest.fixture
def bundesrat_cfg():
    """Aktuelle 16-Länder-Konfiguration aus bundesrat.yaml."""
    return load_bundesrat_config()


def test_load_bundesrat_config_16_states_69_votes(bundesrat_cfg):
    cfg = bundesrat_cfg
    assert len(cfg.states) == 16
    assert sum(s.votes for s in cfg.states) == 69
    assert cfg.majority_simple == 35
    assert cfg.majority_two_thirds == 46
    assert {s.votes for s in cfg.states} <= {3, 4, 5, 6}
    assert cfg.bundesregierung is not None
    assert set(cfg.bundesregierung.parties) >= {"de:cdu", "de:csu", "de:spd"}


def test_default_all_yes_has_simple_majority(bundesrat_cfg):
    tally = simulate_bundesrat(bundesrat_cfg)
    assert tally.yes == 69
    assert tally.no == 0
    assert tally.abstain == 0
    assert tally.has_simple_majority
    assert tally.has_two_thirds_majority


def test_abstain_and_reject_split_votes(bundesrat_cfg):
    cfg = bundesrat_cfg
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
    assert tally.has_simple_majority
    assert tally.has_two_thirds_majority


def test_coalition_override_key(bundesrat_cfg):
    cfg = bundesrat_cfg
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


def test_choices_for_coalition_all_16_states(bundesrat_cfg):
    """Jede der 16 Länder-IDs bekommt default|abstain|reject; Summe prüfbar."""
    cfg = bundesrat_cfg
    ids = {s.parliament_id for s in cfg.states}
    assert len(ids) == 16

    # Explizite CDU+CSU+SPD wie in bundesregierung.yaml-Feld
    choices = choices_for_coalition(cfg, ["de:cdu", "de:csu", "de:spd"])
    assert set(choices) == ids
    assert all(v in {"default", "abstain", "reject"} for v in choices.values())

    # Schwarz-rote Landesregierungen → Ja
    assert choices["de_he_landtag"] == "default"
    assert choices["de_be_abgeordnetenhaus"] == "default"
    # Rot-Grün (nur SPD überlappt) → Enthaltung
    assert choices["de_hh_buergerschaft"] == "abstain"
    assert choices["de_ni_landtag"] == "abstain"
    # CSU+FW → Teilüberschneidung
    assert choices["de_by_landtag"] == "abstain"
    # SPD allein → Ja (SPD ⊆ Bundeskoalition)
    assert choices["de_sl_landtag"] == "default"

    tally = simulate_bundesrat(cfg, choices=choices)
    assert tally.yes + tally.no + tally.abstain == 69
    assert tally.yes == sum(
        s.votes for s in cfg.states if choices[s.parliament_id] == "default"
    )


def test_choices_for_coalition_union_alias(bundesrat_cfg):
    cfg = bundesrat_cfg
    via_union = choices_for_coalition(cfg, ["de:cdu_csu", "de:spd"])
    via_split = choices_for_coalition(cfg, ["de:cdu", "de:csu", "de:spd"])
    assert via_union == via_split


def test_group_votes_by_coalition_current_16_states(bundesrat_cfg):
    """Kräfteverhältnis: Summe 69, informelle Namen, Union-Normalisierung."""
    cfg = bundesrat_cfg
    groups = group_votes_by_coalition(cfg)
    assert sum(g.votes for g in groups) == 69
    by_label = {g.label: g for g in groups}

    assert by_label["Schwarz-Rot"].votes == 21  # BE+BB+HE+RP+SN
    assert by_label["Schwarz-Grün"].votes == 16  # BW+NW+SH
    assert by_label["Rot-Grün"].votes == 9  # HH+NI
    assert by_label["Rot-Rot-Grün"].votes == 3  # HB
    assert by_label["Rot-Rot"].votes == 3  # MV
    assert by_label["Alleinregierung (SPD)"].votes == 3  # SL
    assert by_label["Deutschland-Koalition"].votes == 4  # ST
    assert by_label["CSU + Freie Wähler"].votes == 6  # BY
    assert by_label["CDU + BSW + SPD"].votes == 4  # TH — kein etablierter Name

    # Bundesregierung Schwarz-Rot → Slice markiert
    assert by_label["Schwarz-Rot"].matches_federal is True
    assert sum(1 for g in groups if g.matches_federal) == 1

    # Grün-Schwarz und Schwarz-Grün landen im selben Key
    assert normalize_parties_for_color(["de:gruene", "de:cdu"]) == normalize_parties_for_color(
        ["de:cdu", "de:gruene"]
    )
    assert informal_coalition_label(["de:csu", "de:spd"]) == "Schwarz-Rot"
