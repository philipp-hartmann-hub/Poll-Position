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


def test_export_parliament_static_writes_core_files(export_warehouse, tmp_path):
    from data_pipeline.export_static import export_parliament_static

    out = tmp_path / "static"
    ok = export_parliament_static("de_bundestag", out_dir=out)
    assert ok["averages"] is True
    assert ok["trend"] is True
    assert ok["seats"] is True
    assert ok["coalitions"] is True
    assert ok["last-election"] is True
    assert ok["party-forecast"] is True
    assert ok["uncertainty"] is True
    assert ok["surveys"] is True
    assert ok["coalition-check-all"] is True
    for name in (
        "averages",
        "trend",
        "seats",
        "coalitions",
        "last-election",
        "party-forecast",
        "uncertainty",
        "surveys",
        "coalition-check-all",
    ):
        path = out / "de_bundestag" / f"{name}.json"
        assert path.is_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["parliament_id"] == "de_bundestag"
    election = json.loads(
        (out / "de_bundestag" / "last-election.json").read_text(encoding="utf-8")
    )
    assert "vote_share_by_name" in election
    assert election["vote_share_by_name"].get("AfD") == pytest.approx(20.8)


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

    def fake_last_election(pid):
        return {
            "parliament_id": pid,
            "election_date": date(2025, 1, 1),
            "label": "Test",
            "source": None,
            "seats": {},
            "seats_by_name": {},
            "vote_share_by_name": {},
            "total_seats": 0,
        }

    def fake_forecast(pid, **_kwargs):
        return {"parliament_id": pid, "parties": []}

    def fake_uncertainty(pid, **_kwargs):
        return {
            "parliament_id": pid,
            "n_simulations": 200,
            "n_deadlock": 0,
            "mean_seats": {},
            "coalition_probabilities": [],
            "party_indispensability": [],
            "current_government_majority_probability": None,
            "current_government_missing_parties": [],
            "_seat_distributions": [{"x": 1}],
        }

    def fake_surveys(pid, **_kwargs):
        return {
            "parliament_id": pid,
            "total": 0,
            "limit": 20,
            "offset": 0,
            "surveys": [],
        }

    def fake_coalition_check_all(pid, **_kwargs):
        return {
            "parliament_id": pid,
            "n_simulations": 0,
            "total_seats": 0,
            "majority_threshold": 0,
            "capped": False,
            "eligible_parties": [],
            "combinations": {},
        }

    monkeypatch.setattr("backend.services.party_averages_payload", fake_averages)
    monkeypatch.setattr("backend.services.party_trend_series_payload", fake_trend)
    monkeypatch.setattr("backend.services.seats_payload", fake_seats)
    monkeypatch.setattr("backend.services.coalitions_payload", fake_coalitions)
    monkeypatch.setattr("backend.services.last_election_payload", fake_last_election)
    monkeypatch.setattr("backend.services.party_forecast_payload", fake_forecast)
    monkeypatch.setattr("backend.services.uncertainty_payload", fake_uncertainty)
    monkeypatch.setattr("backend.services.raw_surveys_payload", fake_surveys)
    monkeypatch.setattr(
        "backend.services.coalition_check_all_payload", fake_coalition_check_all
    )

    ok = export_static.export_parliament_static("dawum:parliament:17", out_dir=out)
    assert all(ok.values())
    assert not (out / "dawum:parliament:17").exists()
    for name in (
        "averages",
        "trend",
        "seats",
        "coalitions",
        "last-election",
        "party-forecast",
        "uncertainty",
        "surveys",
        "coalition-check-all",
    ):
        path = out / "dawum_parliament_17" / f"{name}.json"
        assert path.is_file()
        assert ":" not in str(path.relative_to(out))
    unc = json.loads(
        (out / "dawum_parliament_17" / "uncertainty.json").read_text(encoding="utf-8")
    )
    assert "_seat_distributions" not in unc


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


def test_export_all_static_writes_government_and_bundesrat(
    export_warehouse, tmp_path
):
    """Top-Level government/bundesrat/institute-leaderboard entsprechen Live-Payloads."""
    from backend import services
    from data_pipeline.export_static import _json_default, export_all_static

    services.clear_payload_caches()
    out = tmp_path / "static"
    export_all_static(out_dir=out)

    gov_path = out / "government.json"
    br_path = out / "bundesrat-status.json"
    mc_path = out / "bundesrat-majority-check.json"
    lb_path = out / "institute-leaderboard.json"
    assert gov_path.is_file()
    assert br_path.is_file()
    assert mc_path.is_file()
    assert lb_path.is_file()

    exported_gov = json.loads(gov_path.read_text(encoding="utf-8"))
    live_gov = json.loads(
        json.dumps(services.government_payload(), default=_json_default)
    )
    assert exported_gov == live_gov

    exported_br = json.loads(br_path.read_text(encoding="utf-8"))
    live_br = json.loads(
        json.dumps(services.bundesrat_status_payload(), default=_json_default)
    )
    assert exported_br == live_br
    assert "laender" in exported_br
    assert isinstance(exported_br["laender"], list)

    exported_mc = json.loads(mc_path.read_text(encoding="utf-8"))
    live_mc = json.loads(
        json.dumps(
            services.bundesrat_majority_check_payload(), default=_json_default
        )
    )
    assert exported_mc == live_mc
    assert "coalitions" in exported_mc
    assert "coalition_balance" in exported_mc

    exported_lb = json.loads(lb_path.read_text(encoding="utf-8"))
    live_lb = json.loads(
        json.dumps(services.institute_leaderboard_payload(), default=_json_default)
    )
    assert exported_lb == live_lb


def test_export_skips_last_election_when_none(export_warehouse, tmp_path, monkeypatch):
    from data_pipeline.export_static import export_parliament_static

    monkeypatch.setattr("backend.services.last_election_payload", lambda _pid: None)
    out = tmp_path / "static"
    ok = export_parliament_static("de_bundestag", out_dir=out)
    assert ok["last-election"] is False
    assert not (out / "de_bundestag" / "last-election.json").exists()
    assert (out / "de_bundestag" / "averages.json").is_file()


def test_export_uncertainty_matches_live_public_payload(export_warehouse, tmp_path):
    """uncertainty.json entspricht dem Live-Payload ohne interne ``_``-Felder."""
    from backend import services
    from data_pipeline.export_static import export_parliament_static

    services.clear_payload_caches()
    out = tmp_path / "static"
    ok = export_parliament_static("de_bundestag", out_dir=out)
    assert ok["uncertainty"] is True

    path = out / "de_bundestag" / "uncertainty.json"
    assert path.is_file()
    exported = json.loads(path.read_text(encoding="utf-8"))
    assert not any(str(k).startswith("_") for k in exported)

    live = services.uncertainty_payload("de_bundestag", n_simulations=200)
    live_public = {k: v for k, v in live.items() if not str(k).startswith("_")}
    assert exported == live_public
    assert exported.get("n_simulations") == 200
    assert "current_government_majority_probability" in exported
    assert "coalition_probabilities" in exported


def test_export_surveys_matches_live_first_page(export_warehouse, tmp_path):
    """surveys.json entspricht raw_surveys_payload(limit=20, offset=0)."""
    from backend import services
    from data_pipeline.export_static import _json_default, export_parliament_static

    services.clear_payload_caches()
    out = tmp_path / "static"
    ok = export_parliament_static("de_bundestag", out_dir=out)
    assert ok["surveys"] is True

    path = out / "de_bundestag" / "surveys.json"
    assert path.is_file()
    exported = json.loads(path.read_text(encoding="utf-8"))
    live = services.raw_surveys_payload("de_bundestag", limit=20, offset=0)
    live_json = json.loads(json.dumps(live, default=_json_default))
    assert exported == live_json
    assert exported.get("limit") == 20
    assert exported.get("offset") == 0
    assert len(exported.get("surveys") or []) <= 20
