"""Tests für analysis.coalitions — Mehrheiten, Ausschlüsse, Grenzwerte."""

from __future__ import annotations

from analysis.coalitions import (
    CoalitionRulesConfig,
    ExclusionRule,
    ExclusionSet,
    PartyPosition,
    has_majority,
    is_minimal_winning,
    list_active_exclusion_rules,
    load_coalition_rules,
    majority_coalitions,
    majority_threshold,
    possible_majorities,
)


def test_has_majority_strict_over_half():
    seats = {"A": 50, "B": 50}
    assert has_majority(seats, ["A", "B"], total_seats=100) is True
    assert has_majority(seats, ["A"], total_seats=100) is False


def test_exactly_fifty_percent_is_not_majority():
    """Genau 50 % reicht nicht — braucht strikt mehr als die Hälfte."""
    seats = {"A": 50, "B": 30, "C": 20}
    assert majority_threshold(100) == 51
    assert has_majority(seats, ["A"], total_seats=100) is False
    result = possible_majorities(seats, 100, max_parties=2, apply_exclusions=False)
    parties = [c.parties for c in result.coalitions]
    assert ("A",) not in parties
    assert ("A", "B") in parties
    assert ("A", "C") in parties


def test_party_with_zero_seats_ignored():
    """Partei unter Sperrklausel (0 Sitze) erscheint in keiner Koalition."""
    seats = {"A": 40, "B": 35, "C": 25, "D": 0}
    result = possible_majorities(seats, 100, max_parties=3, apply_exclusions=False)
    for c in result.coalitions:
        assert "D" not in c.parties


def test_pruning_omits_supersets():
    seats = {"A": 40, "B": 35, "C": 25}
    result = possible_majorities(seats, 100, max_parties=3, apply_exclusions=False)
    parties = [c.parties for c in result.coalitions]
    assert ("A", "B") in parties
    assert ("A", "B", "C") not in parties  # Obermenge von A+B


def test_minimal_winning_highlighted():
    seats = {"A": 40, "B": 35, "C": 25}
    result = possible_majorities(seats, 100, max_parties=3, apply_exclusions=False)
    assert result.minimal_winning
    assert all(c.is_minimal_winning for c in result.minimal_winning)
    assert is_minimal_winning(seats, ("A", "B"), total_seats=100)
    assert not is_minimal_winning(seats, ("A", "B", "C"), total_seats=100)


def test_seat_majority_and_margin_metrics():
    seats = {"A": 40, "B": 35, "C": 25}
    result = possible_majorities(seats, 100, max_parties=2, apply_exclusions=False)
    ab = next(c for c in result.coalitions if c.parties == ("A", "B"))
    assert ab.seats == 75
    assert ab.seat_majority == 75 - 51  # Sitze über Mehrheitsschwelle
    assert ab.majority_share_percent == 75.0
    assert ab.margin_over_half_pp == 25.0


def test_exclusions_eliminate_all_majorities():
    seats = {"A": 40, "B": 35, "C": 25}
    config = CoalitionRulesConfig(
        party_positions={},
        exclusions=[
            ExclusionSet(
                id="block_all",
                parliament_id=None,
                rules=[
                    ExclusionRule(party="A", excludes=["B", "C"]),
                    ExclusionRule(party="B", excludes=["C"]),
                ],
            )
        ],
    )
    result = possible_majorities(
        seats,
        100,
        max_parties=3,
        rules_config=config,
        apply_exclusions=True,
    )
    assert result.coalitions == []
    assert result.minimal_winning == []
    assert result.excluded_by_rules >= 1


def test_yaml_exclusions_block_afd_union_style():
    seats = {
        "de:cdu_csu": 208,
        "de:afd": 152,
        "de:spd": 120,
        "de:gruene": 85,
        "de:linke": 64,
    }
    total = 630
    config = load_coalition_rules()
    without = possible_majorities(
        seats, total, max_parties=2, apply_exclusions=False, rules_config=config
    )
    with_rules = possible_majorities(
        seats,
        total,
        max_parties=2,
        parliament_id="de_bundestag",
        apply_exclusions=True,
        rules_config=config,
    )
    assert ("de:afd", "de:cdu_csu") in [c.parties for c in without.coalitions] or (
        "de:cdu_csu",
        "de:afd",
    ) in [c.parties for c in without.coalitions]
    afd_cdu = [c for c in with_rules.coalitions if set(c.parties) == {"de:cdu_csu", "de:afd"}]
    assert afd_cdu == []
    assert with_rules.excluded_by_rules >= 1


def test_exclusion_rule_ids_auto_assigned():
    config = load_coalition_rules()
    bund = next(e for e in config.exclusions if e.id == "de_bundestag_default")
    assert all(r.id for r in bund.rules)
    assert bund.rules[0].id == "de_bundestag_default:0"
    assert bund.rules[1].id == "de_bundestag_default:1"


def test_disabled_rule_ids_restores_excluded_coalition():
    """Abgewählte Einzelregel lässt zuvor ausgeschlossene Mehrheit wieder zu."""
    seats = {
        "de:cdu_csu": 208,
        "de:afd": 152,
        "de:spd": 120,
        "de:gruene": 85,
        "de:linke": 64,
    }
    total = 630
    config = load_coalition_rules()
    with_rules = possible_majorities(
        seats,
        total,
        max_parties=2,
        parliament_id="de_bundestag",
        apply_exclusions=True,
        rules_config=config,
    )
    assert not any(set(c.parties) == {"de:cdu_csu", "de:afd"} for c in with_rules.coalitions)

    union_rule = next(
        r
        for r in list_active_exclusion_rules("de_bundestag", rules_config=config)
        if set(r.parties or []) == {"de:afd", "de:cdu_csu"}
        or r.id == "de:afd|de:cdu_csu"
    )
    relaxed = possible_majorities(
        seats,
        total,
        max_parties=2,
        parliament_id="de_bundestag",
        apply_exclusions=True,
        disabled_rule_ids=[union_rule.id or ""],
        rules_config=config,
    )
    assert any(set(c.parties) == {"de:cdu_csu", "de:afd"} for c in relaxed.coalitions)


def test_compatibility_heuristic_marked_as_estimate():
    seats = {"de:spd": 200, "de:gruene": 150, "de:linke": 100, "de:cdu_csu": 180}
    config = load_coalition_rules()
    result = possible_majorities(
        seats,
        630,
        max_parties=2,
        apply_exclusions=False,
        rules_config=config,
    )
    rg = next(c for c in result.coalitions if set(c.parties) == {"de:spd", "de:gruene"})
    assert rg.compatibility_span is not None
    assert rg.compatibility_heuristic is not None
    assert "Heuristik" in rg.compatibility_heuristic
    assert any("heuristisch" in n.lower() or "Heuristik" in n or "kein empirischer" in n for n in rg.notes)


def test_residual_sonstige_never_gets_seats():
    """Sonstige/Others ist Restkategorie — auch über der Hürde keine Sitze."""
    from analysis.seat_allocation import is_residual_party_id, sainte_lague_schepers

    assert is_residual_party_id("de:sonstige")
    assert is_residual_party_id("at:others")
    assert not is_residual_party_id("de:spd")
    votes = {"de:cdu_csu": 35.0, "de:spd": 25.0, "de:sonstige": 12.0, "de:gruene": 15.0}
    seats = sainte_lague_schepers(votes, 100, threshold=0.05)
    assert seats["de:sonstige"] == 0
    assert sum(seats.values()) == 100


def test_union_linke_exclusion_in_default_rules():
    seats = {
        "de:cdu_csu": 280,
        "de:linke": 50,
        "de:spd": 100,
        "de:gruene": 80,
        "de:afd": 120,
    }
    config = load_coalition_rules()
    with_rules = possible_majorities(
        seats,
        630,
        max_parties=2,
        parliament_id="de_bundestag",
        apply_exclusions=True,
        rules_config=config,
    )
    assert not any(set(c.parties) == {"de:cdu_csu", "de:linke"} for c in with_rules.coalitions)
    without = possible_majorities(
        seats,
        630,
        max_parties=2,
        parliament_id="de_bundestag",
        apply_exclusions=False,
        rules_config=config,
    )
    assert any(set(c.parties) == {"de:cdu_csu", "de:linke"} for c in without.coalitions)


def test_majority_coalitions_compat_wrapper():
    seats = {"A": 40, "B": 35, "C": 25}
    combos = majority_coalitions(seats, max_parties=2)
    assert ("A", "B") in combos
    assert ("A",) not in combos


def test_europe_placeholder_exclusion_sets_load():
    cfg = load_coalition_rules()
    for parliament_id in (
        "at_nationalrat",
        "nl_tweede_kamer",
        "it_camera",
        "es_congreso",
        "pl_sejm",
        "se_riksdag",
        "pt_assembleia",
    ):
        rules = list_active_exclusion_rules(parliament_id, rules_config=cfg)
        assert rules, f"erwartete Platzhalter-Regeln für {parliament_id}"
        assert all(r.id and "|" in r.id for r in rules)
        assert all("Platzhalter" in (r.note or "") for r in rules)


def test_laender_exclusion_rules_apply_to_all_landtage():
    cfg = load_coalition_rules()
    landtage = [
        "de_bw_landtag",
        "de_by_landtag",
        "de_be_abgeordnetenhaus",
        "de_bb_landtag",
        "de_hb_buergerschaft",
        "de_hh_buergerschaft",
        "de_he_landtag",
        "de_mv_landtag",
        "de_ni_landtag",
        "de_nw_landtag",
        "de_rp_landtag",
        "de_sl_landtag",
        "de_sn_landtag",
        "de_st_landtag",
        "de_sh_landtag",
        "de_th_landtag",
    ]
    for pid in landtage:
        rules = list_active_exclusion_rules(pid, rules_config=cfg)
        assert rules, f"erwartete Länder-Ausschlüsse für {pid}"
        assert all(r.id and "|" in r.id and r.parties and len(r.parties) == 2 for r in rules)
        assert any(set(r.parties or []) == {"de:afd", "de:cdu"} for r in rules)

    # Bundestag behält Union-Paar (cdu_csu), nicht nur Länder-CDU
    bund = list_active_exclusion_rules("de_bundestag", rules_config=cfg)
    assert bund
    assert any(set(r.parties or []) == {"de:afd", "de:cdu_csu"} for r in bund)
    assert all(r.id and "|" in r.id for r in bund)


def test_laender_cdu_afd_excluded_by_default():
    seats = {
        "de:cdu": 50,
        "de:afd": 40,
        "de:spd": 30,
        "de:gruene": 20,
    }
    cfg = load_coalition_rules()
    with_rules = possible_majorities(
        seats,
        140,
        max_parties=2,
        parliament_id="de_by_landtag",
        apply_exclusions=True,
        rules_config=cfg,
    )
    without = possible_majorities(
        seats,
        140,
        max_parties=2,
        parliament_id="de_by_landtag",
        apply_exclusions=False,
        rules_config=cfg,
    )
    assert with_rules.excluded_by_rules >= 1
    assert not any(set(c.parties) == {"de:cdu", "de:afd"} for c in with_rules.coalitions)
    assert any(set(c.parties) == {"de:cdu", "de:afd"} for c in without.coalitions)
