"""Bronze/Silver/Gold Persistenz (Parquet + DuckDB)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

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
    """Legt die DuckDB-Datei an, falls fehlend."""
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
