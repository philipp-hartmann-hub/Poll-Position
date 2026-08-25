"""Bronze/Silver/Gold Persistenz (Parquet + DuckDB / MotherDuck)."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import duckdb
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE = DATA_DIR / "warehouse.duckdb"

DEFAULT_MOTHERDUCK_DATABASE = "poll_position"

_SCHEMA_SQL = """
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


def _maybe_load_dotenv() -> None:
    """Lädt `.env` einmalig, falls vorhanden (python-dotenv ist Projektabhängigkeit)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except Exception:  # noqa: BLE001 — optional für Tests ohne dotenv-Pfad
        return


def motherduck_token() -> str | None:
    """
    Access-Token aus der Umgebung.

    Primär `MOTHERDUCK_TOKEN` (Vercel Marketplace / Pipeline).
    Fallback: `MOTHERDUCK_READONLY_TOKEN` (nur Lesen, Marketplace).
    Entfernt umschließende Anführungszeichen (häufig beim Einfügen aus ``.env``
    in GitHub Actions Secrets).
    """
    _maybe_load_dotenv()
    for key in ("MOTHERDUCK_TOKEN", "MOTHERDUCK_READONLY_TOKEN"):
        token = os.environ.get(key, "").strip()
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
            token = token[1:-1].strip()
        if token:
            return token
    return None


def motherduck_database() -> str:
    """MOTHERDUCK_DATABASE, Default `poll_position`."""
    _maybe_load_dotenv()
    name = os.environ.get("MOTHERDUCK_DATABASE", "").strip()
    return name or DEFAULT_MOTHERDUCK_DATABASE


def uses_motherduck() -> bool:
    """True, wenn Silver/Gold gegen MotherDuck statt lokaler Datei gehen."""
    return motherduck_token() is not None


def warehouse_connection_target() -> str:
    """
    Zielbeschreibung ohne Secrets (Logging/Tests).

    Lokal: Dateipfad. MotherDuck: `md:<database>` (ohne Token).
    """
    if uses_motherduck():
        return f"md:{motherduck_database()}"
    return str(WAREHOUSE)


def _prepare_vercel_duckdb_env() -> None:
    """Auf Vercel: HOME/Extensions nach /tmp (Filesystem sonst oft read-only)."""
    if not os.environ.get("VERCEL"):
        return
    tmp = os.environ.get("TMPDIR") or "/tmp"
    os.environ.setdefault("HOME", tmp)
    os.environ.setdefault("DUCKDB_EXTENSION_DIRECTORY", f"{tmp}/.duckdb/extensions")


class _CachedConnection:
    """Wrapper: close() ist No-Op — echte Verbindung gehört dem Modul-Cache."""

    __slots__ = ("_con",)

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def close(self) -> None:
        return

    def __getattr__(self, name: str) -> Any:
        return getattr(self._con, name)


# Getrennt für read_only=True vs False (Pipeline-Schreibzugriff vs. API-Reads).
_cached_raw: dict[bool, duckdb.DuckDBPyConnection | None] = {False: None, True: None}
_cached_target: dict[bool, str | None] = {False: None, True: None}


def clear_warehouse_connection_cache() -> None:
    """Schließt gecachte Verbindungen (Tests / Zielwechsel)."""
    for read_only in (False, True):
        raw = _cached_raw[read_only]
        if raw is not None:
            try:
                raw.close()
            except Exception:
                pass
        _cached_raw[read_only] = None
        _cached_target[read_only] = None


def _connection_cache_key(*, read_only: bool) -> str:
    return f"{warehouse_connection_target()}|ro={int(read_only)}"


def _ping_connection(con: duckdb.DuckDBPyConnection) -> bool:
    try:
        con.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


def _open_warehouse_connection(*, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Neue DuckDB-/MotherDuck-Verbindung (ohne Cache)."""
    token = motherduck_token()
    if token:
        _prepare_vercel_duckdb_env()
        database = motherduck_database()
        # saas_mode auf Vercel: kein lokales FS / keine lokalen Extensions
        on_vercel = bool(os.environ.get("VERCEL"))
        params = [f"motherduck_token={quote(token, safe='')}"]
        if on_vercel or os.environ.get("MOTHERDUCK_SAAS_MODE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }:
            params.append("saas_mode=true")
        # Kein attach_mode=single: der Bootstrap `md:?…` (DB anlegen) braucht
        # Workspace-Attach — single scheitert mit:
        # "Cannot open 'md:' … in attach_mode=single."
        conn_str = f"md:{database}?{'&'.join(params)}"
        config: dict[str, str] = {"motherduck_token": token}
        try:
            con = duckdb.connect(conn_str, config=config)
        except Exception:
            # DB existiert ggf. noch nicht → Workspace öffnen und DB anlegen
            bootstrap = f"md:?{'&'.join(params)}"
            con = duckdb.connect(bootstrap, config=config)
            safe_name = database.replace('"', "")
            con.execute(f'CREATE DATABASE IF NOT EXISTS "{safe_name}"')
            con.execute(f'USE "{safe_name}"')
        return con

    if read_only and not WAREHOUSE.exists():
        raise FileNotFoundError(f"Warehouse fehlt: {WAREHOUSE}")
    if read_only:
        return duckdb.connect(str(WAREHOUSE), read_only=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(WAREHOUSE))


def connect_warehouse(*, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Zentrale DuckDB-Verbindung: lokal oder MotherDuck.

    MotherDuck: Verbindung wird pro Prozess wiederverwendet (warme Serverless-
    Instanz), getrennt für read_only=True und False. Aufrufer-.close() ist ein
    No-Op auf dem Wrapper; echte Schließung nur bei Cache-Reset oder
    fehlgeschlagenem Health-Check.

    Lokal (Datei): kein Cache — DuckDB erlaubt keine parallelen RO/RW-Handles
    auf derselben Datei; jeder Aufruf öffnet/schließt wie bisher.

    MotherDuck (DuckDB ≥1.1 / hier 1.5.x), laut motherduck.com/docs:
    - `duckdb.connect("md:<db>?motherduck_token=…&saas_mode=true")` auf Vercel
    - config={"motherduck_token": …} parallel

    Token nur über Env — nie hardcoden. Ohne Token: `data/warehouse.duckdb`.
    """
    if not uses_motherduck():
        return _open_warehouse_connection(read_only=read_only)

    key = _connection_cache_key(read_only=read_only)
    raw = _cached_raw[read_only]
    if raw is not None and _cached_target[read_only] == key and _ping_connection(raw):
        return _CachedConnection(raw)  # type: ignore[return-value]

    if raw is not None:
        try:
            raw.close()
        except Exception:
            pass
        _cached_raw[read_only] = None
        _cached_target[read_only] = None

    con = _open_warehouse_connection(read_only=read_only)
    _cached_raw[read_only] = con
    _cached_target[read_only] = key
    return _CachedConnection(con)  # type: ignore[return-value]


def write_bronze(source: str, frame: pl.DataFrame, *, as_of: date | None = None) -> Path:
    """Schreibt einen Parquet-Snapshot unter data/raw/<source>/<datum>.parquet."""
    as_of = as_of or date.today()
    out_dir = RAW_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{as_of.isoformat()}.parquet"
    frame.write_parquet(path)
    return path


def ensure_warehouse() -> Path:
    """Legt Silver/Gold-Tabellen an (lokal und MotherDuck). Rückgabe: lokaler Pfad (API-kompatibel)."""
    if not uses_motherduck():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        RAW_DIR.mkdir(parents=True, exist_ok=True)
    con = connect_warehouse()
    try:
        con.execute(_SCHEMA_SQL)
    finally:
        con.close()
    return WAREHOUSE


def load_bronze_into_silver(parquet_path: Path) -> None:
    """Lädt einen Bronze-Snapshot in polls_silver (Append)."""
    ensure_warehouse()
    con = connect_warehouse()
    try:
        con.execute(
            """
            INSERT INTO polls_silver
            SELECT * FROM read_parquet(?)
            """,
            [str(parquet_path)],
        )
    finally:
        con.close()


def _upsert_rows(con: duckdb.DuckDBPyConnection, table: str, rows: list[dict[str, Any]]) -> int:
    """Bulk-Upsert via Arrow (kein executemany — zu langsam gegen MotherDuck)."""
    if not rows:
        return 0
    staging = f"_staging_{table}"
    con.register(staging, pl.DataFrame(rows).to_arrow())
    try:
        con.execute(f"INSERT OR REPLACE INTO {table} BY NAME SELECT * FROM {staging}")
    finally:
        con.unregister(staging)
    return len(rows)


def upsert_parliaments(rows: list[dict[str, Any]]) -> int:
    ensure_warehouse()
    con = connect_warehouse()
    try:
        return _upsert_rows(con, "parliaments", rows)
    finally:
        con.close()


def upsert_parties(rows: list[dict[str, Any]]) -> int:
    ensure_warehouse()
    con = connect_warehouse()
    try:
        return _upsert_rows(con, "parties", rows)
    finally:
        con.close()


def upsert_institutes(rows: list[dict[str, Any]]) -> int:
    ensure_warehouse()
    con = connect_warehouse()
    try:
        return _upsert_rows(con, "institutes", rows)
    finally:
        con.close()


def insert_surveys_incremental(
    survey_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    *,
    source: str = "dawum",
) -> tuple[int, int]:
    """Fügt nur neue Surveys (nach source_id) hinzu; Dimensionen werden upserted."""
    ensure_warehouse()
    con = connect_warehouse()
    try:
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
            _upsert_rows(con, "survey_results", new_results)
        return len(new_surveys), len(new_results)
    finally:
        con.close()


def existing_dawum_survey_ids() -> set[str]:
    ensure_warehouse()
    con = connect_warehouse()
    try:
        rows = con.execute(
            "SELECT source_id FROM surveys WHERE source = 'dawum'"
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        con.close()


def copy_local_warehouse_to_motherduck(*, tables: list[str] | None = None) -> dict[str, int]:
    """
    Kopiert die lokale DuckDB nach MotherDuck (Bulk SELECT, kein Row-Insert).

    Voraussetzung: MOTHERDUCK_TOKEN gesetzt und lokale `data/warehouse.duckdb` vorhanden.
    """
    if not uses_motherduck():
        raise RuntimeError("MOTHERDUCK_TOKEN fehlt — kein MotherDuck-Ziel")
    if not WAREHOUSE.exists():
        raise FileNotFoundError(f"Lokales Warehouse fehlt: {WAREHOUSE}")

    ensure_warehouse()
    target_tables = tables or [
        "parliaments",
        "parties",
        "institutes",
        "surveys",
        "survey_results",
        "party_averages",
        "party_trends",
    ]
    con = connect_warehouse()
    counts: dict[str, int] = {}
    try:
        # Absolute Path — MotherDuck kann lokale Dateien ohne saas_mode lesen
        local_path = str(WAREHOUSE.resolve()).replace("'", "''")
        con.execute(f"ATTACH '{local_path}' AS local_wh (READ_ONLY)")
        for table in target_tables:
            exists = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_catalog = 'local_wh' AND table_name = ?",
                [table],
            ).fetchone()[0]
            if not exists:
                counts[table] = 0
                continue
            con.execute(f"DELETE FROM {table}")
            con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM local_wh.{table}")
            counts[table] = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        con.execute("DETACH local_wh")
    finally:
        con.close()
    return counts


def replace_party_averages(rows: list[dict[str, Any]]) -> int:
    """Ersetzt Gold-Tabelle party_averages vollständig."""
    ensure_warehouse()
    con = connect_warehouse()
    try:
        con.execute("DELETE FROM party_averages")
        return _upsert_rows(con, "party_averages", rows)
    finally:
        con.close()


def replace_party_trends(rows: list[dict[str, Any]]) -> int:
    """Ersetzt Gold-Tabelle party_trends vollständig."""
    ensure_warehouse()
    con = connect_warehouse()
    try:
        con.execute("DELETE FROM party_trends")
        return _upsert_rows(con, "party_trends", rows)
    finally:
        con.close()


def refresh_gold_averages(*, reference_date: date | None = None) -> tuple[int, int]:
    """Berechnet Averages/Trends aus Silver und schreibt Gold-Tabellen."""
    from analysis.averages import (
        averages_to_rows,
        compute_all_averages_and_trends,
        load_poll_points_from_warehouse,
        trends_to_rows,
    )

    ensure_warehouse()
    con = connect_warehouse()
    try:
        points = load_poll_points_from_warehouse(con)
    finally:
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
