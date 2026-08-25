"""Koalitions- und Mehrheitslogik (UI-frei)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Iterable, Sequence

from pydantic import BaseModel, Field

from analysis.seat_allocation import is_residual_party_id

CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "data_pipeline" / "config" / "coalition_rules.yaml"
)


class ExclusionRule(BaseModel):
    """Einzelne Ausschlussregel; `id` wird beim Laden gesetzt, falls im YAML fehlt."""

    id: str | None = None
    party: str
    excludes: list[str] = Field(default_factory=list)
    note: str | None = None


class ExclusionSet(BaseModel):
    id: str
    parliament_id: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    description: str | None = None
    rules: list[ExclusionRule] = Field(default_factory=list)


class PartyPosition(BaseModel):
    left_right: float = Field(..., ge=0.0, le=10.0)
    european_party_family: str | None = None


class CoalitionRulesConfig(BaseModel):
    version: int = 1
    party_positions: dict[str, PartyPosition] = Field(default_factory=dict)
    exclusions: list[ExclusionSet] = Field(default_factory=list)


def assign_exclusion_rule_ids(config: CoalitionRulesConfig) -> CoalitionRulesConfig:
    """
    Vergibt stabile IDs `"{set_id}:{index}"` an Regeln ohne explizite id.

    Mutiert die übergebene Config und gibt sie zurück (für Chaining).
    """
    for excl in config.exclusions:
        for i, rule in enumerate(excl.rules):
            if not rule.id:
                rule.id = f"{excl.id}:{i}"
    return config


def load_coalition_rules(path: Path | None = None) -> CoalitionRulesConfig:
    import yaml

    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return assign_exclusion_rule_ids(CoalitionRulesConfig.model_validate(raw))


@dataclass(frozen=True)
class Coalition:
    """Mehrheitsfähige Koalition mit Kennzahlen."""

    parties: tuple[str, ...]
    seats: int
    total_seats: int
    seat_majority: int
    """Sitze über der absoluten Mehrheitsschwelle (majority_threshold)."""

    majority_share_percent: float
    """Anteil der Kammersitze in Prozent."""

    margin_over_half_pp: float
    """Prozentpunkte über 50 % der Kammer."""

    compatibility_span: float | None
    """
    Heuristische ideologische Spannweite (max−min auf Links-Rechts-Skala 0–10).
    None, wenn Positionen fehlen. Kein Fakt — nur grobe Schätzung.
    """

    compatibility_heuristic: str | None
    """Kurzlabel der Heuristik, z. B. 'eng' / 'mittel' / 'weit'."""

    is_minimal_winning: bool
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MajoritySearchResult:
    coalitions: list[Coalition]
    """Inklusionsminimale Mehrheitskoalitionen (keine Obermenge einer kleineren Mehrheit)."""

    minimal_winning: list[Coalition]
    """Mindest-Mehrheitskoalitionen: keine Partei entfernbar ohne Mehrheitsverlust."""

    majority_threshold: int
    total_seats: int
    excluded_by_rules: int
    """Anzahl rechnerischer Mehrheiten, die an Ausschlusslisten scheiterten."""


def majority_threshold(total_seats: int) -> int:
    """Kleinste Sitzzahl mit strikter Mehrheit (> 50 %)."""
    if total_seats <= 0:
        raise ValueError("total_seats muss > 0 sein")
    return total_seats // 2 + 1


def has_majority(
    seats: dict[str, int],
    coalition: list[str] | Sequence[str],
    *,
    total_seats: int | None = None,
) -> bool:
    """True, wenn die Koalition strikt mehr als die Hälfte der Sitze hält."""
    chamber = total_seats if total_seats is not None else sum(seats.values())
    if chamber <= 0:
        return False
    coalition_seats = sum(seats.get(p, 0) for p in coalition)
    return coalition_seats > chamber / 2


def coalition_seat_sum(seats: dict[str, int], parties: Sequence[str]) -> int:
    return sum(seats.get(p, 0) for p in parties)


def is_minimal_winning(
    seats: dict[str, int],
    parties: Sequence[str],
    *,
    total_seats: int,
) -> bool:
    """True, wenn Mehrheit besteht und Entfernen einer beliebigen Partei sie zerstört."""
    if not has_majority(seats, parties, total_seats=total_seats):
        return False
    if len(parties) == 1:
        return True
    for i in range(len(parties)):
        reduced = [p for j, p in enumerate(parties) if j != i]
        if has_majority(seats, reduced, total_seats=total_seats):
            return False
    return True


def _exclusion_active(excl: ExclusionSet, *, parliament_id: str | None, as_of: date | None) -> bool:
    if parliament_id is not None and excl.parliament_id and excl.parliament_id != parliament_id:
        return False
    if as_of is not None:
        if excl.valid_from and as_of < excl.valid_from:
            return False
        if excl.valid_to and as_of > excl.valid_to:
            return False
    return True


def coalition_violates_exclusions(
    parties: Sequence[str],
    rules: Sequence[ExclusionRule],
) -> bool:
    """True, wenn ein Koalitionsmitglied ein anderes laut Regel ausschließt."""
    members = set(parties)
    for rule in rules:
        if rule.party not in members:
            continue
        if members.intersection(rule.excludes):
            return True
    return False


def collect_exclusion_rules(
    config: CoalitionRulesConfig,
    *,
    parliament_id: str | None = None,
    as_of: date | None = None,
    exclusion_set_ids: Sequence[str] | None = None,
    disabled_rule_ids: Sequence[str] | None = None,
) -> list[ExclusionRule]:
    """Sammelt aktive Einzelregeln; `disabled_rule_ids` filtert trotz apply_exclusions."""
    disabled = set(disabled_rule_ids or ())
    rules: list[ExclusionRule] = []
    for excl in config.exclusions:
        if exclusion_set_ids is not None and excl.id not in exclusion_set_ids:
            continue
        if not _exclusion_active(excl, parliament_id=parliament_id, as_of=as_of):
            continue
        for rule in excl.rules:
            rid = rule.id
            if rid and rid in disabled:
                continue
            rules.append(rule)
    return rules


def list_active_exclusion_rules(
    parliament_id: str,
    *,
    as_of: date | None = None,
    rules_config: CoalitionRulesConfig | None = None,
) -> list[ExclusionRule]:
    """
    Öffentliche Loader-API: für ein Parlament gültige Ausschlussregeln
    (mit stabilen IDs nach `assign_exclusion_rule_ids`).
    """
    config = rules_config if rules_config is not None else load_coalition_rules()
    return collect_exclusion_rules(config, parliament_id=parliament_id, as_of=as_of)


def ideological_span(
    parties: Sequence[str],
    positions: dict[str, PartyPosition],
) -> tuple[float | None, str | None]:
    """
    Heuristische Spannweite auf der Links-Rechts-Skala.

    Klar als Schätzung gekennzeichnet — fehlende Positionen → (None, None).
    """
    vals = []
    for p in parties:
        pos = positions.get(p)
        if pos is None:
            return None, None
        vals.append(pos.left_right)
    if not vals:
        return None, None
    span = max(vals) - min(vals)
    if span <= 2.0:
        label = "eng (Heuristik)"
    elif span <= 4.5:
        label = "mittel (Heuristik)"
    else:
        label = "weit (Heuristik)"
    return span, label


def _contains_as_subset(smaller: Sequence[str], larger: Sequence[str]) -> bool:
    return set(smaller).issubset(set(larger))


def _is_superset_of_any(candidate: Sequence[str], known: Iterable[Sequence[str]]) -> bool:
    return any(_contains_as_subset(k, candidate) for k in known)


def _build_coalition(
    parties: tuple[str, ...],
    seats: dict[str, int],
    *,
    total_seats: int,
    positions: dict[str, PartyPosition],
) -> Coalition:
    seat_sum = coalition_seat_sum(seats, parties)
    thr = majority_threshold(total_seats)
    span, label = ideological_span(parties, positions)
    notes: list[str] = []
    if span is not None:
        notes.append(
            "compatibility_span ist eine heuristische Schätzung anhand grober "
            "Links-Rechts-Positionen / Parteienfamilien, kein empirischer Fakt."
        )
    return Coalition(
        parties=parties,
        seats=seat_sum,
        total_seats=total_seats,
        seat_majority=seat_sum - thr,
        majority_share_percent=100.0 * seat_sum / total_seats,
        margin_over_half_pp=100.0 * seat_sum / total_seats - 50.0,
        compatibility_span=span,
        compatibility_heuristic=label,
        is_minimal_winning=is_minimal_winning(seats, parties, total_seats=total_seats),
        notes=tuple(notes),
    )


def possible_majorities(
    seats: dict[str, int],
    total_seats: int,
    *,
    max_parties: int = 4,
    parliament_id: str | None = None,
    as_of: date | None = None,
    exclusion_set_ids: Sequence[str] | None = None,
    disabled_rule_ids: Sequence[str] | None = None,
    rules_config: CoalitionRulesConfig | None = None,
    apply_exclusions: bool = True,
) -> MajoritySearchResult:
    """
    Alle inklusionsminimalen Mehrheitskoalitionen (Combinatorial Search mit Pruning).

    Obermengen einer bereits mehrheitsfähigen Koalition werden nicht ausgegeben.
    Typischerweise reichen 2–4 Parteien (`max_parties`).
    """
    if total_seats <= 0:
        raise ValueError("total_seats muss > 0 sein")
    if max_parties < 1:
        raise ValueError("max_parties muss >= 1 sein")

    config = rules_config if rules_config is not None else load_coalition_rules()
    exclusion_rules = (
        collect_exclusion_rules(
            config,
            parliament_id=parliament_id,
            as_of=as_of,
            exclusion_set_ids=exclusion_set_ids,
            disabled_rule_ids=disabled_rule_ids,
        )
        if apply_exclusions
        else []
    )
    positions = config.party_positions

    parties = sorted(
        p for p, s in seats.items() if s > 0 and not is_residual_party_id(p)
    )
    thr = majority_threshold(total_seats)
    known_minimal: list[tuple[str, ...]] = []
    excluded_count = 0

    for k in range(1, min(max_parties, len(parties)) + 1):
        for combo in combinations(parties, k):
            if _is_superset_of_any(combo, known_minimal):
                continue
            if not has_majority(seats, combo, total_seats=total_seats):
                continue
            if apply_exclusions and coalition_violates_exclusions(combo, exclusion_rules):
                excluded_count += 1
                continue
            known_minimal.append(combo)

    coalitions = [
        _build_coalition(c, seats, total_seats=total_seats, positions=positions)
        for c in known_minimal
    ]

    coalitions.sort(
        key=lambda c: (
            c.compatibility_span if c.compatibility_span is not None else 99.0,
            -c.seats,
            len(c.parties),
            c.parties,
        )
    )
    minimal_winning = [c for c in coalitions if c.is_minimal_winning]

    return MajoritySearchResult(
        coalitions=coalitions,
        minimal_winning=minimal_winning,
        majority_threshold=thr,
        total_seats=total_seats,
        excluded_by_rules=excluded_count,
    )


def majority_coalitions(
    seats: dict[str, int],
    *,
    max_parties: int = 3,
    total_seats: int | None = None,
) -> list[tuple[str, ...]]:
    """Kompatibilität: Tupel-Liste inklusionsminimaler Mehrheiten."""
    chamber = total_seats if total_seats is not None else sum(seats.values())
    result = possible_majorities(
        seats,
        chamber,
        max_parties=max_parties,
        apply_exclusions=False,
    )
    return [c.parties for c in result.coalitions]
