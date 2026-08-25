"""Smoke-Tests für Vercel-Bundle-Pfade (Config-YAMLs erreichbar)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "rel",
    [
        "data_pipeline/config/de_parliaments.yaml",
        "data_pipeline/config/coalition_rules.yaml",
        "data_pipeline/config/party_families.yaml",
        "data_pipeline/config/bundesrat.yaml",
        "data_pipeline/reference/election_results.yaml",
        "backend/main.py",
        "analysis/coalitions.py",
        "analysis/bundesrat.py",
    ],
)
def test_runtime_paths_exist(rel: str):
    path = ROOT / rel
    assert path.exists(), f"Deployment-Bundle braucht {rel}"


def test_coalition_rules_loadable():
    from analysis.coalitions import load_coalition_rules

    cfg = load_coalition_rules()
    assert cfg.party_positions


def test_parliament_config_loadable():
    from data_pipeline.schema import load_parliament_config

    bundle = load_parliament_config()
    assert any(p.id == "de_bundestag" for p in bundle.parliaments)
