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
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_READONLY_TOKEN", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)

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
    body = r.json()
    assert body["status"] == "ok"
    assert body["motherduck_configured"] is False
    assert body.get("surveys", 0) >= 1


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


def test_party_trend_series_chrono_and_days_filter(api_warehouse):
    from datetime import date, datetime

    from backend import services
    from data_pipeline.warehouse import connect_warehouse

    con = connect_warehouse()
    try:
        row = con.execute(
            "SELECT party_id FROM party_trends WHERE parliament_id = ? LIMIT 1",
            ["de_bundestag"],
        ).fetchone()
        assert row, "Fixture muss party_trends füllen"
        party_id = row[0]
        con.execute(
            """
            INSERT INTO party_trends
                (parliament_id, party_id, as_of, trend_share, n_surveys_in_window, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ["de_bundestag", party_id, date(2019, 1, 15), 99.0, 1, datetime.now()],
        )
    finally:
        con.close()

    wide = services.party_trend_series_payload("de_bundestag", days=4000)
    series = next(p for p in wide["parties"] if p["party_id"] == party_id)
    dates = [p["as_of"] for p in series["points"]]
    assert dates == sorted(dates)
    assert date(2019, 1, 15) in dates
    assert len(dates) >= 2

    recent = services.party_trend_series_payload("de_bundestag", days=365)
    recent_series = next(p for p in recent["parties"] if p["party_id"] == party_id)
    recent_dates = [p["as_of"] for p in recent_series["points"]]
    assert recent_dates == sorted(recent_dates)
    assert date(2019, 1, 15) not in recent_dates


def test_trend_series_endpoint(client):
    r = client.get(
        "/api/parties/trend-series",
        params={"parliament_id": "de_bundestag", "days": 365},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["parliament_id"] == "de_bundestag"
    assert body["parties"]
    assert all(p["points"] for p in body["parties"])


def test_raw_surveys_sort_and_pagination(api_warehouse):
    from datetime import date

    from backend import services

    full = services.raw_surveys_payload("de_bundestag", limit=50, offset=0)
    assert full["total"] == 2
    pub = [s["publication_date"] for s in full["surveys"]]
    assert pub == sorted(pub, reverse=True)
    assert pub[0] == date(2026, 7, 28)
    assert pub[1] == date(2026, 7, 20)
    assert full["surveys"][0]["results"]
    shares = [r["share"] for r in full["surveys"][0]["results"]]
    assert shares == sorted(shares, reverse=True)

    page1 = services.raw_surveys_payload("de_bundestag", limit=1, offset=0)
    page2 = services.raw_surveys_payload("de_bundestag", limit=1, offset=1)
    assert page1["total"] == 2
    assert len(page1["surveys"]) == 1
    assert len(page2["surveys"]) == 1
    assert page1["surveys"][0]["publication_date"] == date(2026, 7, 28)
    assert page2["surveys"][0]["publication_date"] == date(2026, 7, 20)
    assert page1["surveys"][0]["id"] != page2["surveys"][0]["id"]


def test_surveys_endpoint(client):
    r = client.get(
        "/api/surveys",
        params={"parliament_id": "de_bundestag", "limit": 1, "offset": 0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert len(body["surveys"]) == 1
    assert body["surveys"][0]["institute_name"]
    assert body["surveys"][0]["results"]


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


def test_coalition_rules_endpoint(client):
    r = client.get("/api/coalitions/rules", params={"parliament_id": "de_bundestag"})
    assert r.status_code == 200
    body = r.json()
    assert body["parliament_id"] == "de_bundestag"
    assert len(body["rules"]) >= 1
    assert all(rule["id"] and rule["party"] and rule["excludes"] for rule in body["rules"])
    assert any(rule["id"].startswith("de_bundestag_default:") for rule in body["rules"])


def test_disabled_rule_ids_via_api(client):
    """E2E: abgewählte Union–AfD-Regel lässt CDU/CSU+AfD wieder in /api/coalitions erscheinen."""
    seats = client.get("/api/seats", params={"parliament_id": "de_bundestag"}).json()
    # Fixture muss rechnerisch Mehrheit Union+AfD erlauben (kanonische Sitze via Namen)
    by_name = seats["seats_by_name"]
    assert by_name.get("CDU/CSU", 0) + by_name.get("AfD", 0) >= seats["total_seats"] // 2 + 1

    rules = client.get(
        "/api/coalitions/rules", params={"parliament_id": "de_bundestag"}
    ).json()["rules"]
    union_rule = next(
        r for r in rules if r["party"] == "de:cdu_csu" and "de:afd" in r["excludes"]
    )

    blocked = client.get(
        "/api/coalitions",
        params={"parliament_id": "de_bundestag", "apply_exclusions": True, "max_parties": 2},
    ).json()
    assert not any(
        set(c["parties"]) == {"de:cdu_csu", "de:afd"} for c in blocked["coalitions"]
    )

    relaxed = client.get(
        "/api/coalitions",
        params=[
            ("parliament_id", "de_bundestag"),
            ("apply_exclusions", "true"),
            ("max_parties", "2"),
            ("disabled_rule_ids", union_rule["id"]),
        ],
    ).json()
    assert any(
        set(c["parties"]) == {"de:cdu_csu", "de:afd"} for c in relaxed["coalitions"]
    ), relaxed["coalitions"]


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
    # Koalitions-IDs müssen kanonisch sein (wie coalitions_payload), nicht dawum:party:…
    for entry in body["coalition_probabilities"]:
        assert entry["parties"], "leere Koalition"
        for pid in entry["parties"]:
            assert not pid.startswith("dawum:"), pid
            assert pid.startswith("de:"), pid


def test_uncertainty_payload_canonical_coalition_ids(api_warehouse):
    """Direktes Service-API: coalition_probabilities nur mit kanonischen IDs."""
    from backend import services

    payload = services.uncertainty_payload("de_bundestag", n_simulations=60)
    assert payload["coalition_probabilities"], "Fixture sollte Mehrheiten liefern"
    canonical = set(services.SHORT_TO_CANONICAL.values())
    for entry in payload["coalition_probabilities"]:
        for pid in entry["parties"]:
            assert pid in canonical or (
                pid.startswith("de:") and not pid.startswith("dawum:")
            ), f"erwartete kanonische ID, got {pid!r}"
            assert not pid.startswith("dawum:party:"), pid


def test_threshold_watch_payload_band_and_exempt(monkeypatch):
    from types import SimpleNamespace

    from backend import services

    votes = {"near_u": 4.2, "near_o": 6.8, "far": 22.0, "ssw": 4.0}
    names = {
        "near_u": "FDP",
        "near_o": "BSW",
        "far": "CDU/CSU",
        "ssw": "SSW",
    }
    monkeypatch.setattr(services, "_votes_from_averages", lambda _pid: (votes, names))
    monkeypatch.setattr(
        services,
        "_election_system_for",
        lambda _pid: (
            None,
            SimpleNamespace(
                threshold_percent=5.0,
                minority_exempt_party_ids=["de:ssw"],
                grundmandat_seats=3,
            ),
        ),
    )
    payload = services.threshold_watch_payload("de_bundestag", band_points=3.0, n_simulations=80)
    ids = {p["party_id"] for p in payload["parties"]}
    assert ids == {"near_u", "near_o"}
    assert payload["threshold_percent"] == 5.0


def test_threshold_watch_endpoint(client):
    r = client.get(
        "/api/threshold-watch",
        params={"parliament_id": "de_bundestag", "band": 3},
    )
    assert r.status_code == 200
    body = r.json()
    names = {p["party_name"] for p in body["parties"]}
    assert "CDU/CSU" not in names
    assert "AfD" not in names
    assert "FDP" in names
    assert "BSW" in names
    for p in body["parties"]:
        assert abs(p["average_share"] - body["threshold_percent"]) <= body["band_points"] + 1e-6


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


def test_institute_leaderboard_endpoint(client):
    r = client.get("/api/institutes/leaderboard")
    assert r.status_code == 200
    body = r.json()
    assert "institutes" in body
    assert isinstance(body["institutes"], list)


def test_institute_leaderboard_payload_aggregates_two_parliaments(monkeypatch):
    """institute_leaderboard_payload: ein Rangplatz, n = Summe über zwei Parlamente."""
    from datetime import date

    from analysis.averages import PollObservationPoint
    from backend import services

    points = [
        PollObservationPoint(
            parliament_id="de_bundestag",
            party_id="wh:spd",
            share=18.0,
            as_of=date(2025, 2, 1),
            institute_id="inst_a",
            survey_id="s-bund",
        ),
        PollObservationPoint(
            parliament_id="de_by_landtag",
            party_id="wh:spd",
            share=22.0,
            as_of=date(2025, 2, 1),
            institute_id="inst_a",
            survey_id="s-by",
        ),
    ]
    monkeypatch.setattr(services, "_load_points", lambda parliament_id=None: points)
    monkeypatch.setattr(services, "ensure_warehouse", lambda: None)

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class _FakeCon:
        def execute(self, sql, params=None):
            if "FROM institutes" in sql:
                return _Result([("inst_a", "Institut A")])
            return _Result([("wh:spd", "SPD")])

        def close(self):
            return None

    monkeypatch.setattr(services, "connect_warehouse", lambda **k: _FakeCon())

    class _El:
        def __init__(self, parliament_id, election_date, results):
            self.parliament_id = parliament_id
            self.election_date = election_date
            self.results = results

    class _Bundle:
        elections = [
            _El("de_bundestag", date(2025, 2, 23), {"de:spd": 16.0}),
            _El("de_by_landtag", date(2025, 2, 23), {"de:spd": 20.0}),
        ]

    monkeypatch.setattr(services, "load_election_results", lambda: _Bundle())

    payload = services.institute_leaderboard_payload()
    assert len(payload["institutes"]) == 1
    row = payload["institutes"][0]
    assert row["rank"] == 1
    assert row["institute_id"] == "inst_a"
    assert row["n_comparisons"] == 2
    assert len(row["by_parliament"]) == 2
    parls = {d["parliament_id"] for d in row["by_parliament"]}
    assert parls == {"de_bundestag", "de_by_landtag"}
    # Gewichteter Score ≠ bloßes Aneinanderhängen zweier Zeilen
    scores = [d["score"] for d in row["by_parliament"]]
    assert row["score"] == pytest.approx(sum(scores) / 2)


def test_europe_overview(client):
    r = client.get("/api/europe/overview")
    assert r.status_code == 200
    body = r.json()
    assert "countries" in body
    assert any(c["country"] == "DE" for c in body["countries"])


def test_bundesrat_status(client):
    r = client.get("/api/bundesrat/status")
    assert r.status_code == 200
    body = r.json()
    assert body["total_votes"] == 69
    assert body["majority_threshold"] == 35
    assert body["two_thirds_threshold"] == 46
    assert len(body["laender"]) == 16
    assert body["simulation"]["yes_votes"] == 69
    assert "amtierenden" in body["disclaimer"].lower()


def test_bundesrat_simulate(client):
    r = client.post(
        "/api/bundesrat/simulate",
        json={
            "choices": {
                "de_nw_landtag": "abstain",
                "de_by_landtag": "reject",
            }
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["abstain_votes"] == 6
    assert body["no_votes"] == 6
    assert body["yes_votes"] == 57
    assert body["has_majority"] is True


def test_bundesrat_simulate_unknown_land(client):
    r = client.post(
        "/api/bundesrat/simulate",
        json={"choices": {"de_bundestag": "abstain"}},
    )
    assert r.status_code == 400


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
