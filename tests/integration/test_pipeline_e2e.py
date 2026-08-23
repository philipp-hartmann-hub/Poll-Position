"""
End-to-End: Bronze → Silver → Gold → Sitze → Koalitionen (offline, Fixture-only).

Kein Live-HTTP: Dawum-JSON und Wikipedia-HTML aus tests/data_pipeline/fixtures/.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from analysis.averages import load_poll_points_from_warehouse
from analysis.coalitions import possible_majorities
from analysis.seat_allocation import allocate_seats
from data_pipeline.schema import load_parliament_config
from data_pipeline.sources.dawum import load_silver, parse_dawum_payload, write_bronze_raw
from data_pipeline.sources.wikipedia_polls import (
    WikiPageConfig,
    intermediate_to_surveys,
    parse_page_html,
    surveys_to_silver_rows,
    write_bronze_wikipedia,
)
from data_pipeline.warehouse import (
    ensure_warehouse,
    insert_surveys_incremental,
    refresh_gold_averages,
    upsert_institutes,
    upsert_parties,
)
from tests.data_pipeline.fixtures.pipeline_e2e_payload import PAYLOAD

FIXTURES = Path(__file__).resolve().parents[1] / "data_pipeline" / "fixtures"

# Warehouse-Kurzname → kanonische ID (Koalitionsregeln)
SHORT_TO_CANONICAL = {
    "AfD": "de:afd",
    "CDU/CSU": "de:cdu_csu",
    "SPD": "de:spd",
    "Grüne": "de:gruene",
    "FDP": "de:fdp",
    "Linke": "de:linke",
    "BSW": "de:bsw",
    "Sonstige": "de:sonstige",
}


@pytest.fixture
def e2e_dirs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    raw = data / "raw"
    dawum_raw = raw / "dawum"
    wiki_raw = raw / "wikipedia_polls"
    dawum_raw.mkdir(parents=True)
    wiki_raw.mkdir(parents=True)
    warehouse = data / "warehouse.duckdb"

    monkeypatch.setattr("data_pipeline.warehouse.DATA_DIR", data)
    monkeypatch.setattr("data_pipeline.warehouse.RAW_DIR", raw)
    monkeypatch.setattr("data_pipeline.warehouse.WAREHOUSE", warehouse)
    monkeypatch.setattr("data_pipeline.sources.dawum.RAW_DIR", dawum_raw)
    monkeypatch.setattr(
        "data_pipeline.sources.dawum.LAST_UPDATE_FILE", dawum_raw / "last_update.txt"
    )
    monkeypatch.setattr("data_pipeline.sources.wikipedia_polls.RAW_DIR", wiki_raw)
    return tmp_path, warehouse


def _load_wikipedia_fixture_into_silver() -> int:
    """Österreich-HTML → Bronze + Silver, ohne Netzwerk."""
    from datetime import datetime, timezone

    from data_pipeline.sources.wikipedia_polls import WikipediaFetchMeta

    html = (FIXTURES / "wikipedia_austria.html").read_text(encoding="utf-8")
    page = WikiPageConfig(
        id="at_national",
        country="AT",
        parliament_id="at_nationalrat",
        level="national",
        title="Next Austrian legislative election",
        url="https://en.wikipedia.org/wiki/Next_Austrian_legislative_election",
        parser="austria",
    )
    meta = WikipediaFetchMeta(
        page_id="1",
        title=page.title,
        revision_id=999001,
        permalink=(
            "https://en.wikipedia.org/w/index.php?"
            "title=Next_Austrian_legislative_election&oldid=999001"
        ),
        fetched_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        html=html,
    )
    bronze = write_bronze_wikipedia(meta, page, as_of=date(2026, 8, 1))
    assert bronze.exists()

    polls = parse_page_html(html, page)
    surveys = intermediate_to_surveys(
        polls,
        page=page,
        revision_id=meta.revision_id,
        permalink=meta.permalink,
    )
    institutes, parties, survey_rows, result_rows = surveys_to_silver_rows(
        surveys, country=page.country
    )
    upsert_institutes(institutes)
    upsert_parties(parties)
    n_s, _ = insert_surveys_incremental(
        survey_rows, result_rows, source="wikipedia"
    )
    return n_s


def test_pipeline_bronze_silver_gold_seats_coalitions(e2e_dirs):
    _, warehouse = e2e_dirs
    as_of = date(2026, 8, 1)

    # --- Bronze (Dawum Fixture) ---
    bronze_path = write_bronze_raw(PAYLOAD, as_of=as_of)
    assert bronze_path.exists()
    assert bronze_path.suffix == ".parquet"

    # --- Silver ---
    ensure_warehouse()
    parsed = parse_dawum_payload(PAYLOAD)
    p, pt, i, s, r = load_silver(parsed)
    assert p >= 1 and pt >= 5 and i >= 1
    assert s >= 2 and r >= 10

    wiki_surveys = _load_wikipedia_fixture_into_silver()
    assert wiki_surveys >= 1

    con = duckdb.connect(str(warehouse), read_only=True)
    n_surveys = con.execute("SELECT COUNT(*) FROM surveys").fetchone()[0]
    n_results = con.execute("SELECT COUNT(*) FROM survey_results").fetchone()[0]
    assert n_surveys >= 3
    assert n_results >= 10
    con.close()

    # --- Gold ---
    n_avg, n_tr = refresh_gold_averages(reference_date=as_of)
    assert n_avg >= 5, "Gold party_averages darf nicht leer sein"
    assert n_tr >= 1, "Gold party_trends darf nicht leer sein"

    con = duckdb.connect(str(warehouse), read_only=True)
    avg_rows = con.execute(
        """
        SELECT party_id, average_share
        FROM party_averages
        WHERE parliament_id = 'de_bundestag'
        ORDER BY average_share DESC
        """
    ).fetchall()
    points = load_poll_points_from_warehouse(con)
    party_names = {
        row[0]: row[1]
        for row in con.execute("SELECT id, short_name FROM parties").fetchall()
    }
    con.close()

    assert avg_rows, "Keine Bundestags-Averages"
    assert all(0 < share < 50 for _, share in avg_rows)
    assert sum(share for _, share in avg_rows) > 50
    assert points, "Poll-Punkte aus Silver erwartet"

    # --- Sitzverteilung ---
    votes = {party_id: float(share) for party_id, share in avg_rows}
    bundle = load_parliament_config()
    parliament = next(p for p in bundle.parliaments if p.id == "de_bundestag")
    system = next(s for s in bundle.election_systems if s.key == parliament.election_system_key)
    seats = allocate_seats(parliament, votes, election_system=system)
    assert seats
    total_seats = sum(seats.values())
    assert total_seats == system.seats_total
    assert any(n > 0 for n in seats.values())

    # --- Koalitionen (kanonische IDs für Ausschlussregeln) ---
    canon_seats: dict[str, int] = {}
    for pid, n in seats.items():
        if n <= 0:
            continue
        name = party_names.get(pid, pid)
        canon = SHORT_TO_CANONICAL.get(name, pid)
        canon_seats[canon] = canon_seats.get(canon, 0) + n

    majors = possible_majorities(
        canon_seats,
        total_seats,
        max_parties=4,
        parliament_id="de_bundestag",
        apply_exclusions=True,
    )
    assert majors.majority_threshold > 0
    assert majors.coalitions, "Mindestens eine Mehrheitskoalition erwartet"
    assert all(c.seats >= majors.majority_threshold for c in majors.coalitions)
    # Mit Ausschlussregeln: keine AfD+SPD-Koalition
    for c in majors.coalitions:
        parties = set(c.parties)
        assert not ({"de:afd", "de:spd"} <= parties)
