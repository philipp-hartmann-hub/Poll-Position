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


class BundesratStateConfig(BaseModel):
    parliament_id: str
    name: str
    votes: int = Field(..., ge=3, le=6)
    government_parties: list[str] = Field(default_factory=list)
    government_label: str


class BundesratConfig(BaseModel):
    stand: str
    votes_total: int = 69
    majority_simple: int = 35
    majority_two_thirds: int = 46
    sources: list[str] = Field(default_factory=list)
    states: list[BundesratStateConfig]


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
    """Union (de:cdu_csu) deckt Landes-CDU/CSU ab."""
    out = set(parties)
    if "de:cdu_csu" in out:
        out.update({"de:cdu", "de:csu"})
    return out


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
