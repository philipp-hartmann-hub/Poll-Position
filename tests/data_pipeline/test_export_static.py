"""Tests für den Static-JSON-Export nach dem Pipeline-Lauf."""

from __future__ import annotations

import json
from datetime import date

import pytest

from data_pipeline.sources.dawum import load_silver, parse_dawum_payload, write_bronze_raw
from data_pipeline.warehouse import ensure_warehouse, refresh_gold_averages
from tests.data_pipeline.fixtures.pipeline_e2e_payload import PAYLOAD


@pytest.fixture
def export_warehouse(tmp_path, monkeypatch):
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_READONLY_TOKEN", raising=False)

    data = tmp_path / "data"
    raw = data / "raw" / "dawum"
    raw.mkdir(parents=True)
    warehouse = data / "warehouse.duckdb"

    monkeypatch.setattr("data_pipeline.warehouse.DATA_DIR", data)
    monkeypatch.setattr("data_pipeline.warehouse.RAW_DIR", data / "raw")
    monkeypatch.setattr("data_pipeline.warehouse.WAREHOUSE", warehouse)
    monkeypatch.setattr("data_pipeline.sources.dawum.RAW_DIR", raw)
    monkeypatch.setattr(
        "data_pipeline.sources.dawum.LAST_UPDATE_FILE", raw / "last_update.txt"
    )

    from data_pipeline.warehouse import clear_warehouse_connection_cache
    from backend import services

    clear_warehouse_connection_cache()
    services.clear_payload_caches()

    write_bronze_raw(PAYLOAD, as_of=date(2026, 8, 1))
    ensure_warehouse()
    load_silver(parse_dawum_payload(PAYLOAD))
    refresh_gold_averages(reference_date=date(2026, 8, 1))
    return tmp_path


def test_export_parliament_static_writes_four_files(export_warehouse, tmp_path):
    from data_pipeline.export_static import export_parliament_static

    out = tmp_path / "static"
    ok = export_parliament_static("de_bundestag", out_dir=out)
    assert ok == {
        "averages": True,
        "trend": True,
        "seats": True,
        "coalitions": True,
    }
    for name in ("averages", "trend", "seats", "coalitions"):
        path = out / "de_bundestag" / f"{name}.json"
        assert path.is_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["parliament_id"] == "de_bundestag"


def test_export_all_static_writes_parliaments_index(export_warehouse, tmp_path):
    from data_pipeline.export_static import export_all_static

    out = tmp_path / "static"
    written = export_all_static(out_dir=out)
    assert written >= 1
    index = out / "parliaments.json"
    assert index.is_file()
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert any(p["id"] == "de_bundestag" for p in payload)
