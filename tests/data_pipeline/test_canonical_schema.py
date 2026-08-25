from datetime import date

import pytest
from pydantic import ValidationError

from data_pipeline.schema import (
    SONSTIGE_PARTY_ID,
    AllocationMethod,
    Level,
    LevelKind,
    Party,
    Pollster,
    Survey,
    load_parliament_config,
)


def test_load_de_parliaments_config():
    bundle = load_parliament_config()
    assert bundle.countries[0].iso_code == "DE"
    de_parliaments = [p for p in bundle.parliaments if p.country == "DE"]
    assert len(de_parliaments) == 17  # Bundestag + 16 Landtage
    assert len([s for s in bundle.election_systems if s.key.startswith("de_")]) == 17
    assert any(p.id == "at_nationalrat" for p in bundle.parliaments)
    assert any(p.id == "fr_assemblee" for p in bundle.parliaments)
    st = next(p for p in de_parliaments if p.id == "de_st_landtag")
    assert st.next_election_date == date(2026, 9, 6)

    bt = next(p for p in bundle.parliaments if p.id == "de_bundestag")
    assert bt.seats_total == 630
    assert bt.level.kind == LevelKind.NATIONAL

    system = next(s for s in bundle.election_systems if s.key == bt.election_system_key)
    assert system.zweitstimmendeckung is True
    assert system.allocation_method == AllocationMethod.SAINTE_LAGUE_SCHEPERS
    assert system.threshold_percent == 5.0

    state_codes = {
        p.level.state_code
        for p in bundle.parliaments
        if p.level.kind == LevelKind.STATE
    }
    assert len(state_codes) == 16
    assert "DE-BY" in state_codes


def test_survey_requires_sonstige_as_party_id_convention():
    survey = Survey(
        id="s1",
        parliament_id="de_bundestag",
        institute_id="fgw",
        publication_date=date(2026, 1, 1),
        source="dawum",
        results={"de:cdu": 30.0, "de:spd": 20.0, SONSTIGE_PARTY_ID: 5.0},
    )
    assert SONSTIGE_PARTY_ID in survey.results


def test_survey_rejects_share_over_100():
    with pytest.raises(ValidationError):
        Survey(
            id="s1",
            parliament_id="de_bundestag",
            institute_id="fgw",
            publication_date=date(2026, 1, 1),
            source="wikipedia",
            results={"de:cdu": 101.0},
        )


def test_level_state_requires_code():
    with pytest.raises(ValidationError):
        Level(kind=LevelKind.STATE)


def test_party_pollster_roundtrip():
    party = Party(
        id=SONSTIGE_PARTY_ID,
        country="DE",
        short_name="Sonstige",
        full_name="Sonstige / Andere",
    )
    institute = Pollster(id="infratest", name="Infratest dimap", country="DE")
    assert party.short_name == "Sonstige"
    assert institute.house_effect_score is None


def test_election_system_saarland_dhondt():
    bundle = load_parliament_config()
    sl = next(s for s in bundle.election_systems if s.key == "de_sl_lt")
    assert sl.allocation_method == AllocationMethod.DHONDT
    assert sl.seats_total == 51
