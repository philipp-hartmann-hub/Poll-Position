"""Globale Test-Fixtures: kein echter MotherDuck-Zugriff in CI/lokal."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_motherduck_for_tests(monkeypatch):
    """
    Alle Tests ohne MOTHERDUCK_TOKEN — auch wenn lokal eine .env existiert.
    Silver/Gold bleiben damit auf der jeweiligen Test-DuckDB-Datei.
    """
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_DATABASE", raising=False)
    monkeypatch.setattr(
        "data_pipeline.warehouse._maybe_load_dotenv",
        lambda: None,
    )
