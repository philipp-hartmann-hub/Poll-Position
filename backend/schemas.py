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


class TrendPointOut(BaseModel):
    as_of: date
    trend_share: float


class PartyTrendSeriesOut(BaseModel):
    party_id: str
    party_name: str
    points: list[TrendPointOut]


class TrendSeriesResponse(BaseModel):
    parliament_id: str
    days: int
    parties: list[PartyTrendSeriesOut]


class SurveyResultOut(BaseModel):
    party_id: str
    party_name: str
    share: float


class RawSurveyOut(BaseModel):
    id: str
    institute_id: str
    institute_name: str | None = None
    field_date_from: date | None = None
    field_date_to: date | None = None
    publication_date: date
    sample_size: int | None = None
    source_url: str | None = None
    results: list[SurveyResultOut] = Field(default_factory=list)


class RawSurveysResponse(BaseModel):
    parliament_id: str
    total: int
    limit: int
    offset: int
    surveys: list[RawSurveyOut]


class SeatsResponse(BaseModel):
    parliament_id: str
    total_seats: int
    seats: dict[str, int] = Field(description="party_id → Sitze")
    seats_by_name: dict[str, int] = Field(default_factory=dict)
    reason: str | None = Field(
        default=None,
        description="Nur bei leeren Sitze: no_averages | all_below_threshold | no_seat_projection",
    )


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


class ExclusionRuleOut(BaseModel):
    id: str
    party: str
    excludes: list[str]
    note: str | None = None


class CoalitionRulesResponse(BaseModel):
    parliament_id: str
    rules: list[ExclusionRuleOut]


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


class ThresholdWatchPartyOut(BaseModel):
    party_id: str
    party_name: str
    average_share: float
    threshold_percent: float
    probability_below_threshold: float


class ThresholdWatchResponse(BaseModel):
    parliament_id: str
    threshold_percent: float
    band_points: float
    n_simulations: int
    parties: list[ThresholdWatchPartyOut]


class ThresholdWatchOverviewItem(ThresholdWatchPartyOut):
    parliament_id: str
    parliament_name: str | None = None
    toss_up: float


class ThresholdWatchOverviewResponse(BaseModel):
    band_points: float
    items: list[ThresholdWatchOverviewItem]


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


class InstituteLeaderboardRow(BaseModel):
    rank: int
    institute_id: str
    institute_name: str | None = None
    n_comparisons: int
    mae: float
    rmse: float
    score: float
    by_parliament: list[InstituteAccuracyOut] = Field(default_factory=list)


class InstituteLeaderboardResponse(BaseModel):
    institutes: list[InstituteLeaderboardRow]


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
    disabled_rule_ids: list[str] = Field(default_factory=list)
    max_coalition_parties: int = 4


class ScenarioResponse(BaseModel):
    parliament_id: str
    party_shares: dict[str, float]
    seats: dict[str, int]
    total_seats: int
    majority_threshold: int
    coalitions: list[CoalitionOut]


class BundesratCoalitionOption(BaseModel):
    key: str
    parties: list[str]
    seats: int
    is_minimal_winning: bool = False


class BundesratLandOut(BaseModel):
    parliament_id: str
    name: str
    votes: int
    default_government: list[str]
    default_government_label: str
    coalition_options: list[BundesratCoalitionOption] = Field(default_factory=list)


class BundesratLandVoteOut(BaseModel):
    parliament_id: str
    name: str
    votes: int
    stance: str
    government: list[str]
    government_label: str
    source: str


class BundesratSimulationOut(BaseModel):
    yes_votes: int
    no_votes: int
    abstain_votes: int
    has_majority: bool
    has_two_thirds: bool
    by_land: list[BundesratLandVoteOut]


class BundesratStatusResponse(BaseModel):
    as_of: str
    disclaimer: str
    sources: list[str] = Field(default_factory=list)
    total_votes: int
    majority_threshold: int
    two_thirds_threshold: int
    laender: list[BundesratLandOut]
    simulation: BundesratSimulationOut


class BundesratSimulateRequest(BaseModel):
    choices: dict[str, str] = Field(
        default_factory=dict,
        description="parliament_id → default | abstain | reject | de:a+de:b",
    )


class BundesratSimulateResponse(BaseModel):
    as_of: str
    disclaimer: str
    total_votes: int
    majority_threshold: int
    two_thirds_threshold: int
    yes_votes: int
    no_votes: int
    abstain_votes: int
    has_majority: bool
    has_two_thirds: bool
    by_land: list[BundesratLandVoteOut]


class BundesratMajorityCheckItem(BaseModel):
    parties: list[str]
    label: str | None = None
    bundestag_seats: int = 0
    is_minimal_winning: bool = False
    is_incumbent: bool = False
    choices: dict[str, str]
    yes_votes: int
    no_votes: int
    abstain_votes: int
    has_majority: bool
    has_two_thirds: bool


class BundesratCoalitionBalanceSlice(BaseModel):
    key: str
    label: str
    parties_normalized: list[str]
    votes: int
    parliament_ids: list[str]
    matches_federal: bool = False


class BundesratFederalGovernmentOut(BaseModel):
    stand: str
    parties: list[str]
    label: str


class BundesratMajorityCheckResponse(BaseModel):
    as_of: str
    total_votes: int
    majority_threshold: int
    two_thirds_threshold: int
    federal_government: BundesratFederalGovernmentOut | None = None
    coalition_balance: list[BundesratCoalitionBalanceSlice] = Field(default_factory=list)
    coalitions: list[BundesratMajorityCheckItem]
