"""Bundesrat-Sandbox: einheitliche Landesstimmen, Default = amtierende Regierung."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from pydantic import BaseModel, Field

CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "data_pipeline" / "config" / "bundesrat.yaml"
)

VoteStance = Literal["yes", "no", "abstain"]

# Normalisierte Tokens für Koalitionsfarben (CDU/CSU → Union)
_UNION_IDS = frozenset({"de:cdu", "de:csu", "de:cdu_csu"})
_PARTY_DISPLAY: dict[str, str] = {
    "union": "Union",
    "de:cdu": "CDU",
    "de:csu": "CSU",
    "de:cdu_csu": "CDU/CSU",
    "de:spd": "SPD",
    "de:gruene": "Grüne",
    "de:fdp": "FDP",
    "de:linke": "Linke",
    "de:afd": "AfD",
    "de:bsw": "BSW",
    "de:fw": "Freie Wähler",
    "de:ssw": "SSW",
}

# Informelle Namen — Key = frozenset normalisierter Tokens (union statt cdu/csu)
_INFORMAL_COALITION_NAMES: dict[frozenset[str], str] = {
    frozenset({"union", "de:spd"}): "Schwarz-Rot",
    frozenset({"union", "de:gruene"}): "Schwarz-Grün",
    frozenset({"union", "de:fdp"}): "Schwarz-Gelb",
    frozenset({"union", "de:spd", "de:gruene"}): "Kenia",
    frozenset({"union", "de:spd", "de:fdp"}): "Deutschland-Koalition",
    frozenset({"de:spd", "de:gruene"}): "Rot-Grün",
    frozenset({"de:spd", "de:gruene", "de:fdp"}): "Ampel",
    frozenset({"de:spd", "de:gruene", "de:linke"}): "Rot-Rot-Grün",
    frozenset({"de:spd", "de:linke"}): "Rot-Rot",
}


class BundesratStateConfig(BaseModel):
    parliament_id: str
    name: str
    votes: int = Field(..., ge=3, le=6)
    government_parties: list[str] = Field(default_factory=list)
    government_label: str


class FederalGovernmentConfig(BaseModel):
    stand: str
    parties: list[str] = Field(default_factory=list)
    label: str


class BundesratConfig(BaseModel):
    stand: str
    votes_total: int = 69
    majority_simple: int = 35
    majority_two_thirds: int = 46
    sources: list[str] = Field(default_factory=list)
    states: list[BundesratStateConfig]
    bundesregierung: FederalGovernmentConfig | None = None


@dataclass(frozen=True)
class StateVote:
    parliament_id: str
    name: str
    votes: int
    parties: tuple[str, ...]
    government_label: str
    stance: VoteStance
    source: Literal["default", "override", "abstain", "reject"]


@dataclass(frozen=True)
class BundesratTally:
    yes: int
    no: int
    abstain: int
    votes_total: int
    majority_simple: int
    majority_two_thirds: int
    has_simple_majority: bool
    has_two_thirds_majority: bool
    states: tuple[StateVote, ...]


@dataclass(frozen=True)
class CoalitionVoteGroup:
    """Stimmen-Slice nach Parteikombination (Reihenfolge egal, Union normalisiert)."""

    key: str
    label: str
    parties_normalized: tuple[str, ...]
    votes: int
    parliament_ids: tuple[str, ...]
    matches_federal: bool


def load_bundesrat_config(path: Path | None = None) -> BundesratConfig:
    import yaml

    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg = BundesratConfig.model_validate(raw)
    total = sum(s.votes for s in cfg.states)
    if total != cfg.votes_total:
        raise ValueError(f"Stimmensumme {total} ≠ votes_total {cfg.votes_total}")
    if len(cfg.states) != 16:
        raise ValueError(f"Erwarte 16 Länder, got {len(cfg.states)}")
    return cfg


def coalition_key(parties: Sequence[str]) -> str:
    return "+".join(sorted(parties))


def parse_coalition_key(key: str) -> tuple[str, ...]:
    parts = [p.strip() for p in key.split("+") if p.strip()]
    return tuple(sorted(parts))


def _expand_party_ids(parties: Sequence[str]) -> set[str]:
    """Union (de:cdu_csu) und explizite CDU+CSU decken Landes-CDU/CSU ab."""
    out = set(parties)
    if "de:cdu_csu" in out or ({"de:cdu", "de:csu"} <= out):
        out.update({"de:cdu", "de:csu", "de:cdu_csu"})
    return out


def normalize_parties_for_color(parties: Sequence[str]) -> frozenset[str]:
    """CDU/CSU → Token ``union``; Reihenfolge egal."""
    out: set[str] = set()
    has_union = False
    for p in parties:
        if p in _UNION_IDS:
            has_union = True
        else:
            out.add(p)
    if has_union:
        out.add("union")
    return frozenset(out)


def informal_coalition_label(parties: Sequence[str]) -> str:
    """Informeller Koalitionsname oder wörtliche Auflistung / Alleinregierung."""
    raw = [p for p in parties if p]
    norm = normalize_parties_for_color(raw)
    if not norm:
        return "—"
    if len(norm) == 1:
        only = next(iter(norm))
        if only == "union" and raw:
            name = _PARTY_DISPLAY.get(raw[0], raw[0])
        else:
            name = _PARTY_DISPLAY.get(only, only)
        return f"Alleinregierung ({name})"
    known = _INFORMAL_COALITION_NAMES.get(norm)
    if known:
        return known
    # Fallback: wörtlich aus Roh-IDs (CDU/CSU getrennt, stabile Parteireihenfolge)
    order = [
        "de:cdu",
        "de:csu",
        "de:cdu_csu",
        "de:bsw",
        "de:spd",
        "de:gruene",
        "de:fdp",
        "de:linke",
        "de:afd",
        "de:fw",
        "de:ssw",
    ]

    def _raw_sort(p: str) -> tuple[int, str]:
        try:
            return (order.index(p), p)
        except ValueError:
            return (len(order), p)

    ordered = sorted(raw, key=_raw_sort)
    return " + ".join(_PARTY_DISPLAY.get(p, p) for p in ordered)


def choices_for_coalition(
    config: BundesratConfig,
    coalition_parties: Sequence[str],
) -> dict[str, str]:
    """
    Pro Land automatische Bundesrats-Stimme für eine Bundes-Koalition.

    - Alle Regierungsparteien ⊆ Koalition → ``default`` (Ja mit amtierender Regierung)
    - Teilüberschneidung → ``abstain`` (Art. 51 Abs. 3 GG)
    - Keine Überschneidung → ``reject``
    """
    coal = _expand_party_ids(coalition_parties)
    choices: dict[str, str] = {}
    for state in config.states:
        gov = set(state.government_parties)
        if not gov:
            choices[state.parliament_id] = "abstain"
            continue
        if gov <= coal:
            choices[state.parliament_id] = "default"
        elif gov & coal:
            choices[state.parliament_id] = "abstain"
        else:
            choices[state.parliament_id] = "reject"
    return choices


def group_votes_by_coalition(
    config: BundesratConfig,
    *,
    parties_by_parliament: Mapping[str, Sequence[str]] | None = None,
) -> list[CoalitionVoteGroup]:
    """
    Gruppiert Länderstimmen nach Regierungs-Parteikombination.

    Ohne ``parties_by_parliament``: Defaults aus der Config.
    """
    federal_norm: frozenset[str] | None = None
    if config.bundesregierung and config.bundesregierung.parties:
        federal_norm = normalize_parties_for_color(config.bundesregierung.parties)

    buckets: dict[frozenset[str], list[BundesratStateConfig]] = {}
    for state in config.states:
        if parties_by_parliament is not None:
            parties = list(parties_by_parliament.get(state.parliament_id) or [])
        else:
            parties = list(state.government_parties)
        key = normalize_parties_for_color(parties)
        buckets.setdefault(key, []).append(state)

    groups: list[CoalitionVoteGroup] = []
    for norm, states in buckets.items():
        # Repräsentative Roh-IDs für Label (erste Landesliste, Union-normalisiert)
        sample = list(states[0].government_parties)
        if parties_by_parliament is not None:
            sample = list(parties_by_parliament.get(states[0].parliament_id) or sample)
        label = informal_coalition_label(sample if sample else sorted(norm))
        votes = sum(s.votes for s in states)
        groups.append(
            CoalitionVoteGroup(
                key="+".join(sorted(norm)),
                label=label,
                parties_normalized=tuple(sorted(norm)),
                votes=votes,
                parliament_ids=tuple(s.parliament_id for s in states),
                matches_federal=bool(federal_norm is not None and norm == federal_norm),
            )
        )
    groups.sort(key=lambda g: (-g.votes, g.label))
    return groups


def simulate_bundesrat(
    config: BundesratConfig,
    *,
    choices: Mapping[str, str] | None = None,
    coalition_labels: Mapping[str, str] | None = None,
) -> BundesratTally:
    """
    Pro Land: fehlend/`default` → Default-Regierung + Ja;
    `abstain` → Enthaltung; `nein`/`reject` → Nein;
    sonst Koalitions-Key (`de:cdu+de:spd`) → diese Parteien + Ja.
    """
    choices = choices or {}
    labels = coalition_labels or {}
    rows: list[StateVote] = []
    yes = no = abstain = 0

    for state in config.states:
        choice = (choices.get(state.parliament_id) or "default").strip()
        if choice in {"abstain", "enthaltung"}:
            vote = StateVote(
                parliament_id=state.parliament_id,
                name=state.name,
                votes=state.votes,
                parties=(),
                government_label="Enthaltung",
                stance="abstain",
                source="abstain",
            )
            abstain += state.votes
        elif choice in {"nein", "reject", "no"}:
            vote = StateVote(
                parliament_id=state.parliament_id,
                name=state.name,
                votes=state.votes,
                parties=tuple(state.government_parties),
                government_label=state.government_label,
                stance="no",
                source="reject",
            )
            no += state.votes
        elif choice in {"default", ""}:
            vote = StateVote(
                parliament_id=state.parliament_id,
                name=state.name,
                votes=state.votes,
                parties=tuple(state.government_parties),
                government_label=state.government_label,
                stance="yes",
                source="default",
            )
            yes += state.votes
        else:
            parties = parse_coalition_key(choice)
            label = labels.get(choice) or " + ".join(parties) or choice
            vote = StateVote(
                parliament_id=state.parliament_id,
                name=state.name,
                votes=state.votes,
                parties=parties,
                government_label=label,
                stance="yes",
                source="override",
            )
            yes += state.votes
        rows.append(vote)

    return BundesratTally(
        yes=yes,
        no=no,
        abstain=abstain,
        votes_total=config.votes_total,
        majority_simple=config.majority_simple,
        majority_two_thirds=config.majority_two_thirds,
        has_simple_majority=yes >= config.majority_simple,
        has_two_thirds_majority=yes >= config.majority_two_thirds,
        states=tuple(rows),
    )
