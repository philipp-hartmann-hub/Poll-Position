"""Europäische Parteienfamilien und Cross-Country-Vergleiche."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Sequence

import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "data_pipeline" / "config" / "party_families.yaml"
)


class EuropeanPartyFamily(StrEnum):
    EPP = "EPP"
    SD = "S&D"
    RENEW = "Renew"
    GREENS_EFA = "Greens/EFA"
    ECR = "ECR"
    ID = "ID"
    LEFT = "Left"
    NI = "NI"  # fraktionslos / non-inscrits


# Rechtspopulistisch im Sinne der Familien ID (+ optional ECR) — heuristische Gruppierung
RIGHT_POPULIST_FAMILIES = frozenset({EuropeanPartyFamily.ID, EuropeanPartyFamily.ECR})


class PartyFamilyEntry(BaseModel):
    party_id: str
    country: str
    short_name: str
    family: EuropeanPartyFamily
    notes: str | None = None


class PartyFamilyConfig(BaseModel):
    version: int = 1
    parties: list[PartyFamilyEntry] = Field(default_factory=list)


@dataclass(frozen=True)
class CountryFamilyShare:
    country: str
    as_of: date
    family: EuropeanPartyFamily
    share: float
    """Summierter Umfrage-/Ergebnisanteil der Familie im Land."""


@dataclass(frozen=True)
class RightPopulistSeriesPoint:
    country: str
    as_of: date
    share: float
    """Anteil ID+ECR (rechtspopulistisch, heuristisch)."""


def load_party_families(path: Path | None = None) -> PartyFamilyConfig:
    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return PartyFamilyConfig.model_validate(raw)


def family_index(config: PartyFamilyConfig | None = None) -> dict[str, EuropeanPartyFamily]:
    cfg = config or load_party_families()
    return {p.party_id: p.family for p in cfg.parties}


def map_party_to_family(
    party_id: str,
    *,
    config: PartyFamilyConfig | None = None,
) -> EuropeanPartyFamily | None:
    return family_index(config).get(party_id)


def aggregate_by_family(
    shares: Mapping[str, float],
    *,
    config: PartyFamilyConfig | None = None,
    unmapped_as: EuropeanPartyFamily | None = EuropeanPartyFamily.NI,
) -> dict[EuropeanPartyFamily, float]:
    """Summiert Partei-Anteile zu Familien-Anteilen."""
    idx = family_index(config)
    out: dict[EuropeanPartyFamily, float] = {f: 0.0 for f in EuropeanPartyFamily}
    for party_id, share in shares.items():
        fam = idx.get(party_id, unmapped_as)
        if fam is None:
            continue
        out[fam] = out.get(fam, 0.0) + float(share)
    return {k: v for k, v in out.items() if v != 0.0}


def cross_country_family_share(
    observations: Sequence[tuple[str, date, Mapping[str, float]]],
    *,
    family: EuropeanPartyFamily,
    config: PartyFamilyConfig | None = None,
) -> list[CountryFamilyShare]:
    """
    Cross-Country: Anteil einer Parteienfamilie je Land/Zeitpunkt.

    observations: (country, as_of, {party_id: share}).
    """
    cfg = config or load_party_families()
    rows: list[CountryFamilyShare] = []
    for country, as_of, shares in observations:
        agg = aggregate_by_family(shares, config=cfg)
        rows.append(
            CountryFamilyShare(
                country=country,
                as_of=as_of,
                family=family,
                share=agg.get(family, 0.0),
            )
        )
    rows.sort(key=lambda r: (r.country, r.as_of))
    return rows


def right_populist_share_series(
    observations: Sequence[tuple[str, date, Mapping[str, float]]],
    *,
    config: PartyFamilyConfig | None = None,
    families: frozenset[EuropeanPartyFamily] = RIGHT_POPULIST_FAMILIES,
) -> list[RightPopulistSeriesPoint]:
    """Zeitreihe: Anteil rechtspopulistischer Familien (ID+ECR, heuristisch) je Land."""
    cfg = config or load_party_families()
    series: list[RightPopulistSeriesPoint] = []
    for country, as_of, shares in observations:
        agg = aggregate_by_family(shares, config=cfg)
        total = sum(agg.get(f, 0.0) for f in families)
        series.append(RightPopulistSeriesPoint(country=country, as_of=as_of, share=total))
    series.sort(key=lambda r: (r.country, r.as_of))
    return series
