"""Bronze/Silver/Gold Persistenz (Parquet + DuckDB)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE = DATA_DIR / "warehouse.duckdb"


def write_bronze(source: str, frame: pl.DataFrame, *, as_of: date | None = None) -> Path:
    """Schreibt einen Parquet-Snapshot unter data/raw/<source>/<datum>.parquet."""
    as_of = as_of or date.today()
    out_dir = RAW_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{as_of.isoformat()}.parquet"
    frame.write_parquet(path)
    return path


def ensure_warehouse() -> Path:
    """Legt die DuckDB-Datei und Silver-Tabellen an, falls fehlend."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS polls_silver (
            source VARCHAR,
            pollster VARCHAR,
            published DATE,
            fieldwork_start DATE,
            fieldwork_end DATE,
            country VARCHAR,
            region VARCHAR,
            election_type VARCHAR,
            sample_size BIGINT,
            methodology VARCHAR,
            scope_label VARCHAR,
            source_url VARCHAR,
            retrieved_at TIMESTAMP,
            raw_id VARCHAR,
            party VARCHAR,
            share DOUBLE,
            seats_hint BIGINT
        );

        CREATE TABLE IF NOT EXISTS parliaments (
            id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            country VARCHAR NOT NULL,
            level_kind VARCHAR NOT NULL,
            state_code VARCHAR,
            name VARCHAR NOT NULL,
            shortcut VARCHAR,
            election_label VARCHAR,
            seats_total INTEGER,
            election_system_key VARCHAR,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS parties (
            id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            country VARCHAR NOT NULL,
            short_name VARCHAR NOT NULL,
            full_name VARCHAR NOT NULL,
            european_party_family VARCHAR,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS institutes (
            id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            country VARCHAR NOT NULL,
            house_effect_score DOUBLE,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS surveys (
            id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            parliament_id VARCHAR NOT NULL,
            institute_id VARCHAR NOT NULL,
            tasker VARCHAR,
            method VARCHAR,
            field_date_from DATE,
            field_date_to DATE,
            publication_date DATE NOT NULL,
            sample_size BIGINT,
            source_url VARCHAR,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS survey_results (
            survey_id VARCHAR NOT NULL,
            party_id VARCHAR NOT NULL,
            share DOUBLE NOT NULL,
            PRIMARY KEY (survey_id, party_id)
        );

        CREATE TABLE IF NOT EXISTS party_averages (
            parliament_id VARCHAR NOT NULL,
            party_id VARCHAR NOT NULL,
            as_of DATE NOT NULL,
            average_share DOUBLE NOT NULL,
            n_surveys INTEGER NOT NULL,
            total_weight DOUBLE NOT NULL,
            swing DOUBLE,
            election_share DOUBLE,
            election_date DATE,
            election_label VARCHAR,
            updated_at TIMESTAMP NOT NULL,
            PRIMARY KEY (parliament_id, party_id, as_of)
        );

        CREATE TABLE IF NOT EXISTS party_trends (
            parliament_id VARCHAR NOT NULL,
            party_id VARCHAR NOT NULL,
            as_of DATE NOT NULL,
            trend_share DOUBLE NOT NULL,
            n_surveys_in_window INTEGER NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            PRIMARY KEY (parliament_id, party_id, as_of)
        );
        """
    )
    con.close()
    return WAREHOUSE


def load_bronze_into_silver(parquet_path: Path) -> None:
    """Lädt einen Bronze-Snapshot in polls_silver (Append)."""
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    con.execute(
        """
        INSERT INTO polls_silver
        SELECT * FROM read_parquet(?)
        """,
        [str(parquet_path)],
    )
    con.close()


def _upsert_rows(con: duckdb.DuckDBPyConnection, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    con.executemany(
        f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
        [tuple(row[c] for c in columns) for row in rows],
    )
    return len(rows)


def upsert_parliaments(rows: list[dict[str, Any]]) -> int:
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    n = _upsert_rows(con, "parliaments", rows)
    con.close()
    return n


def upsert_parties(rows: list[dict[str, Any]]) -> int:
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    n = _upsert_rows(con, "parties", rows)
    con.close()
    return n


def upsert_institutes(rows: list[dict[str, Any]]) -> int:
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    n = _upsert_rows(con, "institutes", rows)
    con.close()
    return n


def insert_surveys_incremental(
    survey_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    *,
    source: str = "dawum",
) -> tuple[int, int]:
    """Fügt nur neue Surveys (nach source_id) hinzu; Dimensionen werden upserted."""
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    existing = {
        row[0]
        for row in con.execute(
            "SELECT source_id FROM surveys WHERE source = ?",
            [source],
        ).fetchall()
    }
    new_surveys = [r for r in survey_rows if r["source_id"] not in existing]
    new_ids = {r["id"] for r in new_surveys}
    new_results = [r for r in result_rows if r["survey_id"] in new_ids]

    if new_surveys:
        _upsert_rows(con, "surveys", new_surveys)
    if new_results:
        con.executemany(
            "INSERT OR REPLACE INTO survey_results (survey_id, party_id, share) VALUES (?, ?, ?)",
            [(r["survey_id"], r["party_id"], r["share"]) for r in new_results],
        )
    con.close()
    return len(new_surveys), len(new_results)


def existing_dawum_survey_ids() -> set[str]:
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    rows = con.execute(
        "SELECT source_id FROM surveys WHERE source = 'dawum'"
    ).fetchall()
    con.close()
    return {row[0] for row in rows}


def replace_party_averages(rows: list[dict[str, Any]]) -> int:
    """Ersetzt Gold-Tabelle party_averages vollständig."""
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    con.execute("DELETE FROM party_averages")
    n = _upsert_rows(con, "party_averages", rows)
    con.close()
    return n


def replace_party_trends(rows: list[dict[str, Any]]) -> int:
    """Ersetzt Gold-Tabelle party_trends vollständig."""
    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    con.execute("DELETE FROM party_trends")
    n = _upsert_rows(con, "party_trends", rows)
    con.close()
    return n


def refresh_gold_averages(*, reference_date: date | None = None) -> tuple[int, int]:
    """Berechnet Averages/Trends aus Silver und schreibt Gold-Tabellen."""
    from analysis.averages import (
        averages_to_rows,
        compute_all_averages_and_trends,
        load_poll_points_from_warehouse,
        trends_to_rows,
    )

    ensure_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    points = load_poll_points_from_warehouse(con)
    con.close()
    if not points:
        replace_party_averages([])
        replace_party_trends([])
        return 0, 0
    averages, trends = compute_all_averages_and_trends(
        points, reference_date=reference_date
    )
    n_avg = replace_party_averages(averages_to_rows(averages))
    n_tr = replace_party_trends(trends_to_rows(trends))
    return n_avg, n_tr
