"""Pydantic-Request-/Response-Modelle für die JSON-API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ParliamentOut(BaseModel):
    id: str
    name: str
    country: str
    level_kind: str
    state_code: str | None = None
    seats_total: int | None = None
    election_system_key: str | None = None
    shortcut: str | None = None


class PartyAverageOut(BaseModel):
    parliament_id: str
    party_id: str
    party_name: str
    average_share: float
    n_surveys: int
    swing: float | None = None
    trend_share: float | None = None


class AveragesResponse(BaseModel):
    parliament_id: str
    as_of: date
    parties: list[PartyAverageOut]


class SeatsResponse(BaseModel):
    parliament_id: str
    total_seats: int
    seats: dict[str, int] = Field(description="party_id → Sitze")
    seats_by_name: dict[str, int] = Field(default_factory=dict)


class CoalitionOut(BaseModel):
    parties: list[str]
    seats: int
    is_minimal_winning: bool
    compatibility_span: float | None = None


class CoalitionsResponse(BaseModel):
    parliament_id: str
    total_seats: int
    majority_threshold: int
    excluded_by_rules: int
    coalitions: list[CoalitionOut]


class CoalitionProbabilityOut(BaseModel):
    parties: list[str]
    majority_probability: float
    n_majority: int
    n_simulations: int


class UncertaintyResponse(BaseModel):
    parliament_id: str
    n_simulations: int
    mean_seats: dict[str, float]
    coalition_probabilities: list[CoalitionProbabilityOut]


class HouseEffectOut(BaseModel):
    institute_id: str
    institute_name: str | None = None
    party_id: str
    party_name: str | None = None
    as_of: date
    house_effect: float
    institute_share: float
    peer_average: float


class InstituteAccuracyOut(BaseModel):
    institute_id: str
    institute_name: str | None = None
    parliament_id: str | None = None
    n_comparisons: int
    mae: float
    rmse: float
    score: float


class HouseEffectsResponse(BaseModel):
    parliament_id: str | None = None
    effects: list[HouseEffectOut]
    accuracy: list[InstituteAccuracyOut] = Field(default_factory=list)


class EuropeCountryOut(BaseModel):
    country: str
    top_party_name: str
    top_party_share: float
    top_family: str
    family_share: float


class EuropeOverviewResponse(BaseModel):
    as_of: date
    countries: list[EuropeCountryOut]


class ScenarioRequest(BaseModel):
    parliament_id: str
    party_shares: dict[str, float] = Field(
        description="Partei-ID → Anteil in Prozent",
        min_length=1,
    )
    apply_exclusions: bool = True
    max_coalition_parties: int = 4


class ScenarioResponse(BaseModel):
    parliament_id: str
    party_shares: dict[str, float]
    seats: dict[str, int]
    total_seats: int
    majority_threshold: int
    coalitions: list[CoalitionOut]
