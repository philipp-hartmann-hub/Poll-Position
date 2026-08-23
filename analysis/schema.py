"""Einheitliches Rückgabeschema für alle Datenquellen-Adapter."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CountryCode(StrEnum):
    DE = "DE"
    AT = "AT"
    CH = "CH"
    FR = "FR"
    IT = "IT"
    ES = "ES"
    NL = "NL"
    BE = "BE"
    PL = "PL"
    SE = "SE"
    FI = "FI"
    DK = "DK"
    NO = "NO"
    PT = "PT"
    IE = "IE"
    CZ = "CZ"
    HU = "HU"
    EU = "EU"
    OTHER = "OTHER"


class ElectionType(StrEnum):
    BUNDESTAG = "bundestag"
    LANDTAG = "landtag"
    EUROPA = "europa"
    NATIONAL = "national"
    REGIONAL = "regional"
    LOCAL = "local"
    OTHER = "other"


class PartyResult(BaseModel):
    """Ein Parteiergebnis innerhalb einer Umfrage."""

    party: str = Field(..., min_length=1, description="Parteikürzel oder kanonischer Name")
    share: float = Field(..., ge=0.0, le=100.0, description="Stimmanteil in Prozent (0–100)")
    seats_hint: int | None = Field(
        default=None,
        ge=0,
        description="Optionaler Sitz-Hinweis der Quelle (nicht berechnet)",
    )


class PollObservation(BaseModel):
    """
    Einheitliches Schema: Jeder Quellen-Adapter gibt `list[PollObservation]` bzw.
    ein `PollBatch` zurück. Felder sind bewusst eng, damit Bronze→Silver
    ohne Quell-Sonderlocken normalisiert werden kann.
    """

    source: str = Field(..., description="Adapter-ID, z. B. dawum, wikipedia_polls")
    pollster: str = Field(..., description="Institut / Auftraggeber laut Quelle")
    published: date
    fieldwork_start: date | None = None
    fieldwork_end: date | None = None
    country: CountryCode
    region: str | None = Field(
        default=None,
        description="Bundesland / Region; None = nationale Ebene",
    )
    election_type: ElectionType
    sample_size: int | None = Field(default=None, ge=0)
    methodology: str | None = None
    scope_label: str | None = Field(
        default=None,
        description="Freitext der Quelle, z. B. 'Sonntagsfrage Bundestag'",
    )
    results: list[PartyResult] = Field(..., min_length=1)
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=_utc_now)
    raw_id: str | None = Field(
        default=None,
        description="Stabile ID der Quellzeile, falls vorhanden",
    )

    @field_validator("results")
    @classmethod
    def shares_reasonable(cls, value: list[PartyResult]) -> list[PartyResult]:
        total = sum(r.share for r in value)
        if total > 120.0:
            raise ValueError(f"Summe der Anteile unplausibel hoch: {total:.1f}%")
        return value


class PollBatch(BaseModel):
    """Rückgabe eines Adapter-Laufs."""

    source: str
    observations: list[PollObservation]
    fetched_at: datetime = Field(default_factory=_utc_now)
    status: Literal["ok", "partial", "empty"] = "ok"
    notes: str | None = None

    @property
    def n(self) -> int:
        return len(self.observations)
