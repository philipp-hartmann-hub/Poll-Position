"""Tests für data_pipeline.sources.election_watch."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from data_pipeline.schema import Level, LevelKind, Parliament
from data_pipeline.sources.election_watch import (
    fetch_wikipedia_election_result,
    pending_elections,
    wikipedia_lemma_for,
)
from data_pipeline.sources.wikipedia_parsers import parse_election_result_table

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_wikipedia_lemma_berlin_and_saarland():
    assert (
        wikipedia_lemma_for("de_be_abgeordnetenhaus", date(2026, 9, 20))
        == "Wahl zum Abgeordnetenhaus von Berlin 2026"
    )
    assert (
        wikipedia_lemma_for("de_sl_landtag", date(2027, 4, 18))
        == "Landtagswahl im Saarland 2027"
    )
    assert wikipedia_lemma_for("unknown_parliament", date(2026, 1, 1)) is None


def test_pending_elections_due_without_result(monkeypatch):
    parl = Parliament(
        id="de_st_landtag",
        country="DE",
        level=Level(kind=LevelKind.STATE, state_code="DE-ST"),
        name="Sachsen-Anhalt",
        seats_total=83,
        election_system_key="de_st_lt",
        next_election_date=date(2026, 9, 6),
    )

    class FakeBundle:
        parliaments = [parl]

    class FakeResults:
        elections = []

    monkeypatch.setattr(
        "data_pipeline.sources.election_watch.load_parliament_config",
        lambda: FakeBundle(),
    )
    monkeypatch.setattr(
        "data_pipeline.sources.election_watch.load_election_results",
        lambda: FakeResults(),
    )
    pending = pending_elections(as_of=date(2026, 9, 14))
    assert [p.id for p in pending] == ["de_st_landtag"]


def test_pending_elections_skips_when_result_exists(monkeypatch):
    parl = Parliament(
        id="de_st_landtag",
        country="DE",
        level=Level(kind=LevelKind.STATE, state_code="DE-ST"),
        name="Sachsen-Anhalt",
        seats_total=83,
        election_system_key="de_st_lt",
        next_election_date=date(2026, 9, 6),
    )

    class FakeBundle:
        parliaments = [parl]

    class FakeElection:
        parliament_id = "de_st_landtag"
        election_date = date(2026, 9, 6)

    class FakeResults:
        elections = [FakeElection()]

    monkeypatch.setattr(
        "data_pipeline.sources.election_watch.load_parliament_config",
        lambda: FakeBundle(),
    )
    monkeypatch.setattr(
        "data_pipeline.sources.election_watch.load_election_results",
        lambda: FakeResults(),
    )
    assert pending_elections(as_of=date(2026, 9, 14)) == []


def test_pending_elections_future_not_due(monkeypatch):
    parl = Parliament(
        id="de_be_abgeordnetenhaus",
        country="DE",
        level=Level(kind=LevelKind.STATE, state_code="DE-BE"),
        name="Berlin",
        seats_total=130,
        election_system_key="de_be_agH",
        next_election_date=date(2026, 9, 20),
    )

    class FakeBundle:
        parliaments = [parl]

    class FakeResults:
        elections = []

    monkeypatch.setattr(
        "data_pipeline.sources.election_watch.load_parliament_config",
        lambda: FakeBundle(),
    )
    monkeypatch.setattr(
        "data_pipeline.sources.election_watch.load_election_results",
        lambda: FakeResults(),
    )
    assert pending_elections(as_of=date(2026, 9, 14)) == []


def test_parse_election_result_table_fixture_st_2026():
    html = (FIXTURES / "wikipedia_election_st_2026.html").read_text(encoding="utf-8")
    raw = parse_election_result_table(html)
    assert raw is not None
    assert raw["AfD"] == pytest.approx(43.8)
    assert raw["CDU"] == pytest.approx(17.2)
    assert raw["SPD"] == pytest.approx(9.3)


def test_parse_election_result_table_unparseable_returns_none():
    html = (FIXTURES / "wikipedia_election_unparseable.html").read_text(
        encoding="utf-8"
    )
    assert parse_election_result_table(html) is None


def test_fetch_wikipedia_election_result_from_fixture_html():
    html = (FIXTURES / "wikipedia_election_st_2026.html").read_text(encoding="utf-8")
    draft = fetch_wikipedia_election_result(
        "de_st_landtag",
        date(2026, 9, 6),
        html=html,
    )
    assert draft is not None
    assert draft.parliament_id == "de_st_landtag"
    assert draft.results["de:afd"] == pytest.approx(43.8)
    assert draft.results["de:cdu"] == pytest.approx(17.2)
    assert draft.results["de:gruene"] == pytest.approx(8.9)


def test_fetch_wikipedia_election_result_unparseable_none_no_raise():
    html = (FIXTURES / "wikipedia_election_unparseable.html").read_text(
        encoding="utf-8"
    )
    draft = fetch_wikipedia_election_result(
        "de_st_landtag",
        date(2026, 9, 6),
        html=html,
    )
    assert draft is None
