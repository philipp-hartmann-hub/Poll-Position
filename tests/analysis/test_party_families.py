"""Tests für analysis.party_families."""

from __future__ import annotations

from datetime import date

from analysis.party_families import (
    EuropeanPartyFamily,
    aggregate_by_family,
    cross_country_family_share,
    load_party_families,
    map_party_to_family,
    right_populist_share_series,
)


def test_map_german_parties_to_families():
    assert map_party_to_family("de:cdu_csu") == EuropeanPartyFamily.EPP
    assert map_party_to_family("de:spd") == EuropeanPartyFamily.SD
    assert map_party_to_family("de:afd") == EuropeanPartyFamily.ID
    cfg = load_party_families()
    assert any(p.party_id == "it:fdi" and p.family == EuropeanPartyFamily.ECR for p in cfg.parties)


def test_right_populist_cross_country_series():
    obs = [
        ("DE", date(2024, 1, 1), {"de:afd": 18.0, "de:cdu_csu": 30.0, "de:spd": 16.0}),
        ("DE", date(2025, 1, 1), {"de:afd": 21.0, "de:cdu_csu": 28.0, "de:spd": 15.0}),
        ("IT", date(2025, 1, 1), {"it:fdi": 28.0, "it:lega": 9.0, "it:pd": 22.0}),
    ]
    series = right_populist_share_series(obs)
    de = [p for p in series if p.country == "DE"]
    assert de[0].share == 18.0  # nur AfD = ID
    assert de[1].share == 21.0
    it = next(p for p in series if p.country == "IT")
    # FdI=ECR + Lega=ID
    assert it.share == 28.0 + 9.0

    epp = cross_country_family_share(obs, family=EuropeanPartyFamily.EPP)
    assert next(r for r in epp if r.country == "DE" and r.as_of == date(2024, 1, 1)).share == 30.0

    agg = aggregate_by_family({"de:gruene": 12.0, "de:linke": 8.0})
    assert agg[EuropeanPartyFamily.GREENS_EFA] == 12.0
    assert agg[EuropeanPartyFamily.LEFT] == 8.0
