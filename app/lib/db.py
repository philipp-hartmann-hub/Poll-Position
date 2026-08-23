"""Gecachte DuckDB-Zugriffe für die Streamlit-App."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"


def warehouse_path() -> Path:
    return WAREHOUSE


def warehouse_exists() -> bool:
    return WAREHOUSE.exists()


@st.cache_data(ttl=300, show_spinner=False)
def load_parliaments() -> pd.DataFrame:
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return con.execute(
            """
            SELECT id, source, source_id, country, level_kind, state_code,
                   name, shortcut, election_label, seats_total, election_system_key
            FROM parliaments
            ORDER BY level_kind, name
            """
        ).df()
    finally:
        con.close()


@st.cache_data(ttl=300, show_spinner=False)
def load_parties() -> pd.DataFrame:
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return con.execute(
            "SELECT id, short_name, full_name, country, source FROM parties ORDER BY short_name"
        ).df()
    finally:
        con.close()


@st.cache_data(ttl=300, show_spinner=False)
def load_institutes() -> pd.DataFrame:
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return con.execute(
            "SELECT id, name, country, house_effect_score FROM institutes ORDER BY name"
        ).df()
    finally:
        con.close()


@st.cache_data(ttl=300, show_spinner=False)
def load_survey_series(parliament_id: str, since: date | None = None) -> pd.DataFrame:
    """Zeitreihe: eine Zeile je Survey×Partei mit Anteil."""
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        q = """
            SELECT
                s.id AS survey_id,
                s.parliament_id,
                s.institute_id,
                i.name AS institute_name,
                s.publication_date,
                COALESCE(s.field_date_to, s.publication_date) AS as_of,
                s.sample_size,
                r.party_id,
                COALESCE(p.short_name, r.party_id) AS party_name,
                r.share
            FROM surveys s
            JOIN survey_results r ON r.survey_id = s.id
            LEFT JOIN parties p ON p.id = r.party_id
            LEFT JOIN institutes i ON i.id = s.institute_id
            WHERE s.parliament_id = ?
        """
        params: list = [parliament_id]
        if since is not None:
            q += " AND s.publication_date >= ?"
            params.append(since)
        q += " ORDER BY s.publication_date, r.party_id"
        return con.execute(q, params).df()
    finally:
        con.close()


@st.cache_data(ttl=300, show_spinner=False)
def load_party_averages(parliament_id: str | None = None) -> pd.DataFrame:
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "party_averages" not in tables:
            return pd.DataFrame()
        if parliament_id:
            return con.execute(
                "SELECT * FROM party_averages WHERE parliament_id = ? ORDER BY average_share DESC",
                [parliament_id],
            ).df()
        return con.execute("SELECT * FROM party_averages").df()
    finally:
        con.close()


@st.cache_data(ttl=300, show_spinner=False)
def load_party_trends(parliament_id: str) -> pd.DataFrame:
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "party_trends" not in tables:
            return pd.DataFrame()
        return con.execute(
            "SELECT * FROM party_trends WHERE parliament_id = ? ORDER BY as_of",
            [parliament_id],
        ).df()
    finally:
        con.close()


@st.cache_data(ttl=300, show_spinner=False)
def load_all_latest_shares_by_country() -> pd.DataFrame:
    """Neueste Survey-Anteile je parliament (für Europa-Übersicht)."""
    if not warehouse_exists():
        return pd.DataFrame()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return con.execute(
            """
            WITH latest AS (
                SELECT parliament_id, MAX(publication_date) AS max_date
                FROM surveys
                GROUP BY parliament_id
            )
            SELECT
                s.parliament_id,
                par.country,
                par.name AS parliament_name,
                par.level_kind,
                r.party_id,
                COALESCE(p.short_name, r.party_id) AS party_name,
                AVG(r.share) AS share
            FROM surveys s
            JOIN latest l ON l.parliament_id = s.parliament_id AND l.max_date = s.publication_date
            JOIN survey_results r ON r.survey_id = s.id
            LEFT JOIN parties p ON p.id = r.party_id
            LEFT JOIN parliaments par ON par.id = s.parliament_id
            GROUP BY 1, 2, 3, 4, 5, 6
            """
        ).df()
    finally:
        con.close()
