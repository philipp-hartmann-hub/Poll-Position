"""FastAPI TestClient — alle Endpunkte gegen lokale Fixture-DuckDB (kein MotherDuck)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from data_pipeline.sources.dawum import load_silver, parse_dawum_payload, write_bronze_raw
from data_pipeline.warehouse import ensure_warehouse, refresh_gold_averages
from tests.data_pipeline.fixtures.pipeline_e2e_payload import PAYLOAD


@pytest.fixture
def api_warehouse(tmp_path, monkeypatch):
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

    write_bronze_raw(PAYLOAD, as_of=date(2026, 8, 1))
    ensure_warehouse()
    load_silver(parse_dawum_payload(PAYLOAD))
    refresh_gold_averages(reference_date=date(2026, 8, 1))
    return warehouse


@pytest.fixture
def client(api_warehouse):
    from backend.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_parliaments(client):
    r = client.get("/api/parliaments")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(p["id"] == "de_bundestag" for p in data)


def test_party_averages(client):
    r = client.get("/api/parties/averages", params={"parliament_id": "de_bundestag"})
    assert r.status_code == 200
    body = r.json()
    assert body["parliament_id"] == "de_bundestag"
    assert len(body["parties"]) >= 5
    assert body["parties"][0]["average_share"] > 0


def test_seats(client):
    r = client.get("/api/seats", params={"parliament_id": "de_bundestag"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_seats"] == 630
    assert sum(body["seats"].values()) == 630
    assert body["seats_by_name"]


def test_coalitions(client):
    r = client.get("/api/coalitions", params={"parliament_id": "de_bundestag"})
    assert r.status_code == 200
    body = r.json()
    assert body["majority_threshold"] > 0
    assert isinstance(body["coalitions"], list)
    assert len(body["coalitions"]) >= 1
    assert all(c["seats"] >= body["majority_threshold"] for c in body["coalitions"])


def test_uncertainty(client):
    r = client.get(
        "/api/uncertainty",
        params={"parliament_id": "de_bundestag", "n_simulations": 80},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["n_simulations"] == 80
    assert body["mean_seats"]
    assert isinstance(body["coalition_probabilities"], list)


def test_house_effects(client):
    r = client.get(
        "/api/institutes/house-effects",
        params={"parliament_id": "de_bundestag", "window_days": 30},
    )
    assert r.status_code == 200
    body = r.json()
    assert "effects" in body
    assert "accuracy" in body
    # Mit nur 2 Instituten können Effects leer sein — Endpoint muss trotzdem 200 liefern


def test_europe_overview(client):
    r = client.get("/api/europe/overview")
    assert r.status_code == 200
    body = r.json()
    assert "countries" in body
    assert any(c["country"] == "DE" for c in body["countries"])


def test_scenario(client):
    r = client.post(
        "/api/scenario",
        json={
            "parliament_id": "de_bundestag",
            "party_shares": {
                "dawum:party:1": 30.0,
                "dawum:party:7": 20.0,
                "dawum:party:2": 18.0,
                "dawum:party:4": 14.0,
                "dawum:party:5": 8.0,
                "de:sonstige": 10.0,
            },
            "apply_exclusions": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_seats"] == 630
    assert sum(body["seats"].values()) == 630
    assert isinstance(body["coalitions"], list)


def test_scenario_validation_error(client):
    r = client.post(
        "/api/scenario",
        json={"parliament_id": "de_bundestag", "party_shares": {}},
    )
    assert r.status_code == 422
