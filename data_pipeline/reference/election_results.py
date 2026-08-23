"""Loader für historische Wahlergebnisse (Swing-Referenz)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

REFERENCE_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = REFERENCE_DIR / "election_results.yaml"


class ElectionResult(BaseModel):
    parliament_id: str
    election_date: date
    label: str
    source: str | None = None
    results: dict[str, float] = Field(..., min_length=1)


class ElectionResultsBundle(BaseModel):
    version: int = 1
    elections: list[ElectionResult]


def load_election_results(path: Path | None = None) -> ElectionResultsBundle:
    import yaml

    config_path = path or DEFAULT_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return ElectionResultsBundle.model_validate(raw)


def latest_election_for(parliament_id: str, path: Path | None = None) -> ElectionResult | None:
    """Neueste Wahl je Parlament (nach election_date)."""
    bundle = load_election_results(path)
    matches = [e for e in bundle.elections if e.parliament_id == parliament_id]
    if not matches:
        return None
    return max(matches, key=lambda e: e.election_date)
