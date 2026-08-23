"""Tests für data_pipeline.sources.dawum (offline mit Fixture)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import polars as pl
import pytest

from data_pipeline.schema import SONSTIGE_PARTY_ID
from data_pipeline.sources.dawum import (
    DawumAdapter,
    load_silver,
    parse_dawum_payload,
    read_local_last_update,
    write_bronze_raw,
)
from data_pipeline.warehouse import existing_dawum_survey_ids

FIXTURE = Path(__file__).parent / "fixtures" / "dawum_sample.json"


@pytest.fixture
def sample_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def tmp_dawum_dirs(tmp_path, monkeypatch):
    raw_dir = tmp_path / "data" / "raw" / "dawum"
    raw_dir.mkdir(parents=True)
    monkeypatch.setattr("data_pipeline.sources.dawum.RAW_DIR", raw_dir)
    monkeypatch.setattr("data_pipeline.sources.dawum.LAST_UPDATE_FILE", raw_dir / "last_update.txt")
    monkeypatch.setattr("data_pipeline.warehouse.RAW_DIR", tmp_path / "data" / "raw")
    monkeypatch.setattr("data_pipeline.warehouse.DATA_DIR", tmp_path / "data")
    monkeypatch.setattr("data_pipeline.warehouse.WAREHOUSE", tmp_path / "data" / "warehouse.duckdb")
    return tmp_path


def test_parse_dawum_payload_maps_entities(sample_payload):
    parsed = parse_dawum_payload(sample_payload)

    assert len(parsed["parliament_rows"]) == 2
    assert parsed["parliament_rows"][0]["id"] == "de_bundestag"
    assert parsed["parliament_rows"][0]["level_kind"] == "national"
    assert parsed["parliament_rows"][1]["state_code"] == "DE-BE"

    assert len(parsed["party_rows"]) == 4
    sonstige = next(r for r in parsed["party_rows"] if r["source_id"] == "0")
    assert sonstige["id"] == SONSTIGE_PARTY_ID
    assert sonstige["short_name"] == "Sonstige"

    assert len(parsed["institute_rows"]) == 2
    assert parsed["institute_rows"][0]["name"] == "INSA"

    assert len(parsed["survey_rows"]) == 2
    survey = parsed["survey_rows"][0]
    assert survey["source_id"] == "100"
    assert survey["parliament_id"] == "de_bundestag"
    assert survey["institute_id"] == "dawum:institute:5"
    assert survey["tasker"] == "BILD am Sonntag"
    assert survey["method"] == "Telefon & Online"
    assert survey["sample_size"] == 1203

    results = {r["party_id"]: r["share"] for r in parsed["result_rows"] if r["survey_id"] == survey["id"]}
    assert results[SONSTIGE_PARTY_ID] == 6.0
    assert results["dawum:party:7"] == 29.0


def test_write_bronze_raw_preserves_json(sample_payload, tmp_dawum_dirs):
    path = write_bronze_raw(sample_payload, as_of=date(2026, 1, 15))
    row = pl.read_parquet(path).row(0, named=True)
    restored = json.loads(row["raw_json"])
    assert restored == sample_payload
    assert row["last_update"] == sample_payload["Database"]["Last_Update"]


def test_incremental_load_skips_existing_surveys(sample_payload, tmp_dawum_dirs):
    parsed = parse_dawum_payload(sample_payload)
    *_, s1, r1 = load_silver(parsed)
    assert s1 == 2
    assert r1 == 8

    *_, s2, r2 = load_silver(parsed)
    assert s2 == 0
    assert r2 == 0
    assert existing_dawum_survey_ids() == {"100", "101"}


def test_dawum_adapter_run_with_mocked_http(sample_payload, tmp_dawum_dirs, monkeypatch):
    session = MagicMock()
    session.get.side_effect = [
        MagicMock(text="2026-01-15T10:00:00+01:00", status_code=200, raise_for_status=lambda: None),
        MagicMock(text=json.dumps(sample_payload), status_code=200, raise_for_status=lambda: None),
    ]

    adapter = DawumAdapter(session=session)
    result = adapter.run(as_of=date(2026, 1, 15))

    assert result.fetched is True
    assert result.bronze_path is not None
    assert result.surveys_new == 2
    assert read_local_last_update() == "2026-01-15T10:00:00+01:00"

    # Zweiter Lauf: gleiches last_update → kein erneuter Voll-Abruf
    session.get.reset_mock()
    session.get.side_effect = None
    session.get.return_value = MagicMock(
        text="2026-01-15T10:00:00+01:00",
        status_code=200,
        raise_for_status=lambda: None,
    )
    result2 = adapter.run(as_of=date(2026, 1, 16))
    assert result2.fetched is False
    assert result2.surveys_new == 0
    assert session.get.call_count == 1
    assert session.get.call_args[0][0] == "https://api.dawum.de/last_update.txt"


def test_survey_pydantic_validation(sample_payload):
    parsed = parse_dawum_payload(sample_payload)
    survey = parsed["surveys"][0]
    assert survey.source == "dawum"
    assert SONSTIGE_PARTY_ID in survey.results
