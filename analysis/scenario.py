"""Was-wäre-wenn-Szenarien: User-Overrides durch Sitzverteilung und Koalitionen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from analysis.coalitions import (
    CoalitionRulesConfig,
    MajoritySearchResult,
    possible_majorities,
)
from analysis.seat_allocation import (
    allocate_seats,
    is_residual_party_id,
    sainte_lague_schepers,
)
from data_pipeline.schema import ElectionSystem, Parliament


@dataclass(frozen=True)
class ScenarioInput:
    """Manuell abgewandelte Umfragewerte (Prozent je Partei)."""

    party_shares: dict[str, float]
    parliament_id: str
    total_seats: int | None = None
    threshold: float | None = None
    """Anteil 0–1; None → aus ElectionSystem oder 0.05."""

    as_of: date | None = None


@dataclass(frozen=True)
class ScenarioResult:
    party_shares: dict[str, float]
    seats: dict[str, int]
    total_seats: int
    majorities: MajoritySearchResult


def run_scenario(
    overrides: Mapping[str, float] | ScenarioInput,
    *,
    parliament: Parliament | None = None,
    election_system: ElectionSystem | None = None,
    total_seats: int = 630,
    threshold: float = 0.05,
    max_coalition_parties: int = 4,
    parliament_id: str | None = None,
    apply_exclusions: bool = True,
    disabled_rule_ids: Sequence[str] | None = None,
    rules_config: CoalitionRulesConfig | None = None,
    as_of: date | None = None,
) -> ScenarioResult:
    """
    Rechnet Overrides durch Sitzzuteilung → Koalitionen, ohne Kernfunktionen zu ändern.

    Für die Streamlit-App: interaktives Was-wäre-wenn.
    """
    if isinstance(overrides, ScenarioInput):
        shares = dict(overrides.party_shares)
        pid = overrides.parliament_id
        seats_n = overrides.total_seats
        thr = overrides.threshold
        as_of = overrides.as_of or as_of
    else:
        shares = dict(overrides)
        pid = parliament_id or (parliament.id if parliament else "scenario")
        seats_n = None
        thr = None

    if any(v < 0 for v in shares.values()):
        raise ValueError("Umfragewerte dürfen nicht negativ sein")
    if not shares:
        raise ValueError("party_shares darf nicht leer sein")

    if parliament is not None or election_system is not None:
        if parliament is None and election_system is None:
            raise ValueError("parliament oder election_system erforderlich")
        target = parliament if parliament is not None else election_system
        assert target is not None
        seats = allocate_seats(
            target,  # type: ignore[arg-type]
            shares,
            election_system=election_system,
        )
        system = election_system
        if system is None and parliament is not None:
            from data_pipeline.schema import load_parliament_config

            bundle = load_parliament_config()
            system = next(
                s for s in bundle.election_systems if s.key == parliament.election_system_key
            )
        chamber = system.seats_total if system else sum(seats.values())
        thr_used = (system.threshold_percent / 100.0) if system else threshold
        pid = parliament.id if parliament else pid
    else:
        chamber = seats_n or total_seats
        thr_used = thr if thr is not None else threshold
        seats = sainte_lague_schepers(shares, chamber, thr_used)

    majorities = possible_majorities(
        seats,
        chamber,
        max_parties=max_coalition_parties,
        parliament_id=pid,
        as_of=as_of,
        apply_exclusions=apply_exclusions,
        disabled_rule_ids=disabled_rule_ids,
        rules_config=rules_config,
    )
    return ScenarioResult(
        party_shares=shares,
        seats=seats,
        total_seats=chamber,
        majorities=majorities,
    )
