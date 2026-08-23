"""Tests für Wikipedia-Adapter und landesspezifische Parser (offline)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_pipeline.sources.base import PollSourceAdapter
from data_pipeline.sources.dawum import DawumAdapter
from data_pipeline.sources.wikipedia_parsers import (
    parse_austria,
    parse_fieldwork_dates,
    parse_spain,
)
from data_pipeline.sources.wikipedia_polls import (
    CC_BY_SA_ATTRIBUTION,
    WikiPageConfig,
    WikipediaPollsAdapter,
    intermediate_to_surveys,
    load_page_configs,
    parse_page_html,
)
from data_pipeline.schema import Survey

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def austria_html() -> str:
    return (FIXTURES / "wikipedia_austria.html").read_text(encoding="utf-8")


@pytest.fixture
def spain_html() -> str:
    return (FIXTURES / "wikipedia_spain.html").read_text(encoding="utf-8")


def test_adapters_share_poll_source_interface():
    assert issubclass(DawumAdapter, PollSourceAdapter)
    assert issubclass(WikipediaPollsAdapter, PollSourceAdapter)


def test_wikipedia_config_lists_at_least_five_countries():
    pages = load_page_configs()
    countries = {p.country for p in pages}
    assert len(pages) >= 5
    assert {"AT", "FR", "IT", "ES", "NL"} <= countries


def test_parse_fieldwork_dates():
    start, end = parse_fieldwork_dates("15–17 Jul 2026")
    assert start is not None and end is not None
    assert start.isoformat() == "2026-07-15"
    assert end.isoformat() == "2026-07-17"


def test_parse_austria_fixture(austria_html):
    polls = parse_austria(austria_html)
    assert len(polls) == 3
    first = polls[0]
    assert first.institute == "IFDD"
    assert first.sample_size == 1000
    assert first.method == "Online"
    assert first.results["FPÖ"] == 37.0
    assert first.results["ÖVP"] == 20.0
    assert first.results["Others"] == 3.0
    assert first.field_date_from.isoformat() == "2026-07-15"

    market = polls[2]
    assert market.institute == "Market"
    assert market.tasker == "ORF"


def test_parse_spain_fixture_extracts_percent_before_seats(spain_html):
    polls = parse_spain(spain_html)
    assert len(polls) == 2
    first = polls[0]
    assert first.institute == "EM-Analytics"
    assert first.tasker == "Electomanía"
    assert first.results["PP"] == 32.0
    assert first.results["PSOE"] == 26.1
    assert first.results["Vox"] == 19.0
    assert "Lead" not in first.results


def test_intermediate_to_surveys_sets_permalink_and_party_ids(austria_html):
    page = WikiPageConfig(
        id="at_national",
        country="AT",
        parliament_id="at_nationalrat",
        level="national",
        title="Next Austrian legislative election",
        url="https://en.wikipedia.org/wiki/Next_Austrian_legislative_election",
        parser="austria",
    )
    polls = parse_page_html(austria_html, page)
    surveys = intermediate_to_surveys(
        polls,
        page=page,
        revision_id=123456,
        permalink="https://en.wikipedia.org/w/index.php?title=Next_Austrian_legislative_election&oldid=123456",
    )
    assert surveys
    assert all(isinstance(s, Survey) for s in surveys)
    assert all(s.source == "wikipedia" for s in surveys)
    assert "oldid=123456" in surveys[0].source_url
    assert "at:fp" in surveys[0].results or "at:fpö" in {
        k for s in surveys for k in s.results
    } or any(k.startswith("at:") for k in surveys[0].results)
    assert any(k.endswith(":others") for k in surveys[0].results)


def test_wikipedia_adapter_fetch_uses_mocked_api(austria_html, monkeypatch, tmp_path):
    page = WikiPageConfig(
        id="at_national",
        country="AT",
        parliament_id="at_nationalrat",
        level="national",
        title="Next Austrian legislative election",
        url="https://en.wikipedia.org/wiki/Next_Austrian_legislative_election",
        parser="austria",
    )
    api_payload = {
        "parse": {
            "pageid": 1,
            "title": "Next Austrian legislative election",
            "revid": 999001,
            "text": austria_html,
        }
    }
    session = MagicMock()
    response = MagicMock()
    response.raise_for_status = lambda: None
    response.json.return_value = api_payload
    session.get.return_value = response
    session.headers = {}

    monkeypatch.setattr(
        "data_pipeline.sources.wikipedia_polls.RAW_DIR",
        tmp_path / "raw",
    )

    adapter = WikipediaPollsAdapter(session=session, pages=[page])
    surveys = adapter.fetch()
    assert len(surveys) == 3
    assert surveys[0].source_url.endswith("oldid=999001")
    assert "CC BY-SA" in CC_BY_SA_ATTRIBUTION


def test_wikipedia_adapter_run_writes_bronze_with_revision(austria_html, monkeypatch, tmp_path):
    page = WikiPageConfig(
        id="at_national",
        country="AT",
        parliament_id="at_nationalrat",
        level="national",
        title="Next Austrian legislative election",
        url="https://en.wikipedia.org/wiki/Next_Austrian_legislative_election",
        parser="austria",
    )
    api_payload = {
        "parse": {
            "pageid": 1,
            "title": "Next Austrian legislative election",
            "revid": 999002,
            "text": austria_html,
        }
    }
    session = MagicMock()
    response = MagicMock()
    response.raise_for_status = lambda: None
    response.json.return_value = api_payload
    session.get.return_value = response
    session.headers = {}

    raw_dir = tmp_path / "raw"
    monkeypatch.setattr("data_pipeline.sources.wikipedia_polls.RAW_DIR", raw_dir)
    monkeypatch.setattr("data_pipeline.warehouse.DATA_DIR", tmp_path / "data")
    monkeypatch.setattr("data_pipeline.warehouse.RAW_DIR", tmp_path / "data" / "raw")
    monkeypatch.setattr(
        "data_pipeline.warehouse.WAREHOUSE", tmp_path / "data" / "warehouse.duckdb"
    )

    adapter = WikipediaPollsAdapter(session=session, pages=[page])
    result = adapter.run()
    assert result.surveys_new == 3
    assert result.bronze_paths
    assert "r999002" in result.bronze_paths[0].name
    assert "attribution" in (result.notes or "")
