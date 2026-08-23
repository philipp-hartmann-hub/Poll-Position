"""Einheitliches kanonisches Datenmodell für Poll-Position (Bronze→Silver).

Adapter (Dawum, Wikipedia, …) mappen ihre Rohdaten auf diese Strukturen.
Das leichtere Abruf-Schema in `analysis.schema` (PollObservation) bleibt für
ETL-Zwischenformate; persistente/kanonische Entitäten leben hier.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SONSTIGE_PARTY_ID = "de:sonstige"
CONFIG_DIR = Path(__file__).resolve().parent / "config"


class SourceId(StrEnum):
    DAWUM = "dawum"
    WIKIPEDIA = "wikipedia"
    OTHER = "other"


class LevelKind(StrEnum):
    NATIONAL = "national"
    STATE = "state"
    EU_PARLIAMENT = "eu_parliament"
    REGIONAL = "regional"
    LOCAL = "local"


class AllocationMethod(StrEnum):
    SAINTE_LAGUE_SCHEPERS = "sainte_lague_schepers"
    DHONDT = "dhondt"
    HARE_NIEMEYER = "hare_niemeyer"


class Country(BaseModel):
    iso_code: Annotated[str, Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")]
    name: str


class Level(BaseModel):
    """Politische Ebene; bei Deutschland zusätzlich optionaler Bundesland-Code (ISO 3166-2)."""

    kind: LevelKind
    state_code: str | None = Field(
        default=None,
        description="z. B. DE-BY für Bayern; nur bei kind=state gesetzt",
        pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$",
    )

    @model_validator(mode="after")
    def state_requires_code(self) -> Level:
        if self.kind == LevelKind.STATE and not self.state_code:
            raise ValueError("Level.kind=state erfordert state_code (ISO 3166-2)")
        if self.kind != LevelKind.STATE and self.state_code is not None:
            raise ValueError("state_code nur bei Level.kind=state erlaubt")
        return self


class ElectionSystem(BaseModel):
    """Wahlrechts-Parameter eines Parlaments (für Sitzzuteilung in analysis/)."""

    key: str = Field(..., description="Stabiler Schlüssel, referenziert von Parliament.election_system_key")
    allocation_method: AllocationMethod
    threshold_percent: float = Field(..., ge=0.0, le=100.0)
    seats_total: int = Field(..., gt=0, description="Gesetzliche Regel-/Mindestsitzzahl")
    zweitstimmendeckung: bool = Field(
        default=False,
        description="True beim Bundestag nach Wahlrechtsreform 2023 (BTW ab 2025)",
    )
    direct_seats: int | None = Field(
        default=None,
        ge=0,
        description="Wahlkreismandate in der Regelgröße, falls personalisierte VW",
    )
    grundmandat_seats: int | None = Field(
        default=None,
        ge=0,
        description="Anzahl Direkt-/Wahlkreiserfolge als Ausnahme von der Sperrklausel",
    )
    threshold_includes_invalid: bool = Field(
        default=False,
        description="True z. B. Berlin: Hürde bezogen auf abgegebene Stimmen inkl. ungültige",
    )
    minority_exempt_party_ids: list[str] = Field(
        default_factory=list,
        description="Parteien nationaler Minderheiten ohne Sperrklausel (z. B. SSW)",
    )
    notes: str | None = None
    sources: list[str] = Field(default_factory=list)


class Parliament(BaseModel):
    id: str
    country: str = Field(..., description="ISO-3166-1 alpha-2, z. B. DE")
    level: Level
    name: str
    seats_total: int = Field(..., gt=0)
    election_system_key: str


class Party(BaseModel):
    id: str
    country: str
    short_name: str
    full_name: str
    european_party_family: str | None = None


class Pollster(BaseModel):
    """Institut / Pollster."""

    id: str
    name: str
    country: str
    house_effect_score: float | None = Field(
        default=None,
        description="Optionaler House-Effect-Indikator (projektspezifische Skala)",
    )


class Survey(BaseModel):
    """Eine Umfrage mit Prozent-Ergebnissen je party_id; 'sonstige' als eigene Partei."""

    id: str
    parliament_id: str
    institute_id: str
    tasker: str | None = Field(default=None, description="Auftraggeber, falls bekannt")
    method: str | None = None
    field_date_from: date | None = None
    field_date_to: date | None = None
    publication_date: date
    sample_size: int | None = Field(default=None, ge=0)
    source: Literal["dawum", "wikipedia"] | str
    source_url: str | None = None
    results: dict[str, float] = Field(
        ...,
        min_length=1,
        description="party_id → Stimmanteil in Prozent (0–100); Sonstige über SONSTIGE_PARTY_ID",
    )

    @field_validator("results")
    @classmethod
    def validate_shares(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("results darf nicht leer sein")
        for party_id, share in value.items():
            if share < 0.0 or share > 100.0:
                raise ValueError(f"Ungültiger Anteil für {party_id}: {share}")
        total = sum(value.values())
        if total > 105.0:
            raise ValueError(f"Summe der Anteile unplausibel hoch: {total:.1f}%")
        return value


class ParliamentConfigBundle(BaseModel):
    """YAML/JSON-Wurzel: Länder, Wahlrechtssysteme, Parlamente."""

    version: int = 1
    as_of: date | None = None
    sources_bibliography: list[str] = Field(default_factory=list)
    countries: list[Country]
    election_systems: list[ElectionSystem]
    parliaments: list[Parliament]

    @model_validator(mode="after")
    def referential_integrity(self) -> ParliamentConfigBundle:
        country_codes = {c.iso_code for c in self.countries}
        system_keys = {s.key for s in self.election_systems}
        if len(system_keys) != len(self.election_systems):
            raise ValueError("election_systems.key muss eindeutig sein")
        parliament_ids = {p.id for p in self.parliaments}
        if len(parliament_ids) != len(self.parliaments):
            raise ValueError("parliaments.id muss eindeutig sein")
        for p in self.parliaments:
            if p.country not in country_codes:
                raise ValueError(f"Parliament {p.id}: unbekanntes Land {p.country}")
            if p.election_system_key not in system_keys:
                raise ValueError(
                    f"Parliament {p.id}: unbekanntes election_system_key {p.election_system_key}"
                )
            system = next(s for s in self.election_systems if s.key == p.election_system_key)
            if p.seats_total != system.seats_total:
                raise ValueError(
                    f"Parliament {p.id}: seats_total ({p.seats_total}) "
                    f"≠ ElectionSystem.seats_total ({system.seats_total})"
                )
        return self


def load_parliament_config(
    path: Path | None = None,
) -> ParliamentConfigBundle:
    """Lädt die Parlament-/Wahlrechts-Konfiguration (YAML)."""
    import yaml

    config_path = path or (CONFIG_DIR / "de_parliaments.yaml")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return ParliamentConfigBundle.model_validate(raw)
