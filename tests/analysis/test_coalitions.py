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
        if r.party == "de:cdu_csu" and "de:afd" in r.excludes
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
        assert all("Platzhalter" in (r.note or "") for r in rules)
