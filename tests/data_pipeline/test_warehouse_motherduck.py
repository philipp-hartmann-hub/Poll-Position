"""Tests für MotherDuck-/Lokal-Routing der Warehouse-Verbindung (ohne Live-Cloud)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from data_pipeline import warehouse


@pytest.fixture(autouse=True)
def _clear_motherduck_env(monkeypatch):
    """Tests laufen immer ohne echten MotherDuck-Zugriff."""
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_READONLY_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_DATABASE", raising=False)
    monkeypatch.delenv("MOTHERDUCK_SAAS_MODE", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(warehouse, "_maybe_load_dotenv", lambda: None)


def test_uses_motherduck_false_without_token():
    assert warehouse.uses_motherduck() is False
    assert warehouse.warehouse_connection_target().endswith("warehouse.duckdb")


def test_uses_motherduck_true_with_token(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "test-token-not-real")
    monkeypatch.setenv("MOTHERDUCK_DATABASE", "poll_position")
    assert warehouse.uses_motherduck() is True
    assert warehouse.motherduck_database() == "poll_position"
    assert warehouse.warehouse_connection_target() == "md:poll_position"


def test_uses_motherduck_true_with_readonly_token(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_READONLY_TOKEN", "ro-token")
    assert warehouse.uses_motherduck() is True
    assert warehouse.motherduck_token() == "ro-token"


def test_motherduck_database_default(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "tok")
    assert warehouse.motherduck_database() == "poll_position"


def test_connect_warehouse_local_path(tmp_path, monkeypatch):
    wh = tmp_path / "warehouse.duckdb"
    monkeypatch.setattr(warehouse, "WAREHOUSE", wh)
    monkeypatch.setattr(warehouse, "DATA_DIR", tmp_path)
    monkeypatch.setattr(warehouse, "RAW_DIR", tmp_path / "raw")

    con = warehouse.connect_warehouse()
    try:
        con.execute("CREATE TABLE t (x INT)")
        con.execute("INSERT INTO t VALUES (1)")
        assert con.execute("SELECT x FROM t").fetchone() == (1,)
    finally:
        con.close()
    assert wh.exists()


def test_connect_warehouse_motherduck_uses_md_string(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "secret-token")
    monkeypatch.setenv("MOTHERDUCK_DATABASE", "poll_position")
    fake = MagicMock()

    with patch("data_pipeline.warehouse.duckdb.connect", return_value=fake) as mocked:
        con = warehouse.connect_warehouse()
        assert con is fake
        mocked.assert_called_once()
        args, kwargs = mocked.call_args
        assert args[0].startswith("md:poll_position?")
        assert "motherduck_token=" in args[0]
        assert "secret-token" in args[0]
        assert "attach_mode=single" in args[0]
        assert "saas_mode=true" not in args[0]
        assert kwargs.get("config", {}).get("motherduck_token") == "secret-token"


def test_connect_warehouse_motherduck_saas_mode_on_vercel(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "secret-token")
    monkeypatch.setenv("VERCEL", "1")
    fake = MagicMock()

    with patch("data_pipeline.warehouse.duckdb.connect", return_value=fake) as mocked:
        warehouse.connect_warehouse()
        args, _ = mocked.call_args
        assert "saas_mode=true" in args[0]


def test_ensure_warehouse_local_creates_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(warehouse, "WAREHOUSE", tmp_path / "warehouse.duckdb")
    monkeypatch.setattr(warehouse, "DATA_DIR", tmp_path)
    monkeypatch.setattr(warehouse, "RAW_DIR", tmp_path / "raw")

    path = warehouse.ensure_warehouse()
    assert path == tmp_path / "warehouse.duckdb"
    con = warehouse.connect_warehouse()
    try:
        names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    finally:
        con.close()
    assert {"parliaments", "surveys", "party_averages", "party_trends"} <= names
