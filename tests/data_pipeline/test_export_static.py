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


def test_static_path_segment_strips_artifact_unsafe_chars():
    from data_pipeline.export_static import static_path_segment

    assert static_path_segment("de_bundestag") == "de_bundestag"
    assert static_path_segment("dawum:parliament:17") == "dawum_parliament_17"
    assert static_path_segment('a:"b*<c>') == "a__b__c_"


def test_export_parliament_static_sanitizes_colon_ids(
    export_warehouse, tmp_path, monkeypatch
):
    """Colon-IDs dürfen keine Artifact-/NTFS-ungültigen Verzeichnisnamen erzeugen."""
    from data_pipeline import export_static

    out = tmp_path / "static"

    def fake_averages(pid, *, days=365):
        return {"parliament_id": pid, "as_of": date(2026, 8, 1), "parties": []}

    def fake_trend(pid, *, days=365):
        return {"parliament_id": pid, "series": []}

    def fake_seats(pid):
        return {"parliament_id": pid, "parties": []}

    def fake_coalitions(pid, **_kwargs):
        return {"parliament_id": pid, "coalitions": []}

    monkeypatch.setattr("backend.services.party_averages_payload", fake_averages)
    monkeypatch.setattr("backend.services.party_trend_series_payload", fake_trend)
    monkeypatch.setattr("backend.services.seats_payload", fake_seats)
    monkeypatch.setattr("backend.services.coalitions_payload", fake_coalitions)

    ok = export_static.export_parliament_static("dawum:parliament:17", out_dir=out)
    assert all(ok.values())
    assert not (out / "dawum:parliament:17").exists()
    for name in ("averages", "trend", "seats", "coalitions"):
        path = out / "dawum_parliament_17" / f"{name}.json"
        assert path.is_file()
        assert ":" not in str(path.relative_to(out))


def test_export_all_static_purges_leftover_colon_dirs(
    export_warehouse, tmp_path, monkeypatch
):
    from data_pipeline.export_static import export_all_static

    out = tmp_path / "static"
    stale = out / "dawum:parliament:17"
    stale.mkdir(parents=True)
    (stale / "averages.json").write_text("{}", encoding="utf-8")

    export_all_static(out_dir=out)
    assert not stale.exists()
    assert ":" not in "".join(p.name for p in out.iterdir() if p.is_dir())


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

    for child in out.iterdir():
        if child.is_dir():
            assert ":" not in child.name
