"""Brücke: Warehouse-Daten → analysis-Funktionen (ohne UI)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Sequence

import pandas as pd
import streamlit as st

from analysis.averages import (
    PollObservationPoint,
    party_averages_for_parliament,
    party_trends_for_parliament,
)
from analysis.coalitions import (
    CoalitionRulesConfig,
    ExclusionRule,
    ExclusionSet,
    MajoritySearchResult,
    load_coalition_rules,
    possible_majorities,
)
from analysis.seat_allocation import allocate_seats, sainte_lague_schepers
from analysis.uncertainty import (
    UncertaintyConfig,
    party_uncertainties_from_means,
    simulate_uncertainty,
)
from app.lib.ui import SHORT_TO_CANONICAL
from data_pipeline.schema import load_parliament_config


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()
    return date.fromisoformat(str(value)[:10])


def series_to_points(df: pd.DataFrame) -> list[PollObservationPoint]:
    points: list[PollObservationPoint] = []
    for row in df.itertuples(index=False):
        raw_as_of = row.as_of if hasattr(row, "as_of") else row.publication_date
        points.append(
            PollObservationPoint(
                parliament_id=row.parliament_id,
                party_id=row.party_id,
                share=float(row.share),
                as_of=_as_date(raw_as_of),
                sample_size=int(row.sample_size)
                if row.sample_size is not None and not pd.isna(row.sample_size)
                else None,
                institute_id=row.institute_id,
                survey_id=row.survey_id,
            )
        )
    return points


@st.cache_data(ttl=300, show_spinner=False)
def compute_current_averages(parliament_id: str, days: int = 120) -> pd.DataFrame:
    from app.lib.db import load_survey_series

    since = date.today() - timedelta(days=days)
    df = load_survey_series(parliament_id, since=since)
    if df.empty:
        return pd.DataFrame()
    points = series_to_points(df)
    avgs = party_averages_for_parliament(
        points, parliament_id=parliament_id, reference_date=date.today()
    )
    parties = __import__("app.lib.db", fromlist=["load_parties"]).load_parties()
    name_map = dict(zip(parties["id"], parties["short_name"])) if not parties.empty else {}
    rows = [
        {
            "parliament_id": a.parliament_id,
            "party_id": a.party_id,
            "party_name": name_map.get(a.party_id, a.party_id),
            "average_share": a.average_share,
            "n_surveys": a.n_surveys,
            "swing": a.swing,
        }
        for a in avgs
    ]
    return pd.DataFrame(rows).sort_values("average_share", ascending=False)


@st.cache_data(ttl=300, show_spinner=False)
def compute_trend_frame(parliament_id: str, days: int = 365) -> pd.DataFrame:
    from app.lib.db import load_survey_series

    since = date.today() - timedelta(days=days)
    df = load_survey_series(parliament_id, since=since)
    if df.empty:
        return pd.DataFrame()
    points = series_to_points(df)
    trends = party_trends_for_parliament(points, parliament_id=parliament_id)
    parties = __import__("app.lib.db", fromlist=["load_parties"]).load_parties()
    name_map = dict(zip(parties["id"], parties["short_name"])) if not parties.empty else {}
    # Rohpunkte mit rollierenden Unsicherheitsbändern (Min/Max-Fenster)
    raw = df[["as_of", "party_name", "party_id", "share"]].copy()
    raw["as_of"] = pd.to_datetime(raw["as_of"]).dt.normalize()
    raw = raw.sort_values("as_of")

    band_rows = []
    for _, sub in raw.groupby("party_name"):
        sub = sub.copy()
        sub["lo"] = sub["share"].rolling(5, min_periods=1).min()
        sub["hi"] = sub["share"].rolling(5, min_periods=1).max()
        band_rows.append(sub)
    bands = pd.concat(band_rows, ignore_index=True) if band_rows else raw

    if trends:
        trend_df = pd.DataFrame(
            [
                {
                    "as_of": pd.Timestamp(t.as_of),
                    "party_id": t.party_id,
                    "party_name": name_map.get(t.party_id, t.party_id),
                    "share": t.trend_share,
                }
                for t in trends
            ]
        )
        trend_df["as_of"] = pd.to_datetime(trend_df["as_of"]).dt.normalize()
        merged = trend_df.merge(
            bands[["as_of", "party_name", "lo", "hi"]],
            on=["as_of", "party_name"],
            how="left",
        )
        # Fehlende Bänder: ±1 pp um Trend
        merged["lo"] = merged["lo"].fillna(merged["share"] - 1.0)
        merged["hi"] = merged["hi"].fillna(merged["share"] + 1.0)
        return merged
    return bands


def averages_to_vote_dict(avg_df: pd.DataFrame) -> dict[str, float]:
    return {row.party_id: float(row.average_share) for row in avg_df.itertuples()}


def name_seats(seats: dict[str, int], avg_df: pd.DataFrame) -> dict[str, int]:
    id_to_name = dict(zip(avg_df["party_id"], avg_df["party_name"])) if not avg_df.empty else {}
    return {id_to_name.get(k, k): v for k, v in seats.items()}


@st.cache_data(ttl=300, show_spinner=False)
def project_seats(parliament_id: str, days: int = 120) -> tuple[pd.DataFrame, dict[str, int], dict[str, int]]:
    avg_df = compute_current_averages(parliament_id, days=days)
    if avg_df.empty:
        return avg_df, {}, {}
    votes = averages_to_vote_dict(avg_df)
    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    system = None
    if parliament:
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )
        seats = allocate_seats(parliament, votes, election_system=system)
    else:
        seats = sainte_lague_schepers(votes, 100, 0.05)
    named = name_seats(seats, avg_df)
    return avg_df, seats, named


def build_exclusion_config(
    enabled_rules: Sequence[tuple[str, str]],
    *,
    parliament_id: str,
) -> CoalitionRulesConfig:
    """enabled_rules: (party_canonical, excluded_canonical)."""
    base = load_coalition_rules()
    rules = [
        ExclusionRule(party=a, excludes=[b], note="UI-Toggle")
        for a, b in enabled_rules
    ]
    return CoalitionRulesConfig(
        version=base.version,
        party_positions=base.party_positions,
        exclusions=[
            ExclusionSet(
                id="ui_live",
                parliament_id=parliament_id,
                rules=rules,
                description="Live aus Streamlit-Toggles",
            )
        ],
    )


def seats_for_coalitions(seats: dict[str, int], avg_df: pd.DataFrame) -> dict[str, int]:
    """Mappt Warehouse-IDs auf kanonische IDs, falls bekannt."""
    id_to_name = dict(zip(avg_df["party_id"], avg_df["party_name"])) if not avg_df.empty else {}
    out: dict[str, int] = {}
    for pid, n in seats.items():
        name = id_to_name.get(pid, pid)
        canon = SHORT_TO_CANONICAL.get(str(name), pid)
        out[canon] = out.get(canon, 0) + n
    return out


def compute_majorities(
    seats: dict[str, int],
    avg_df: pd.DataFrame,
    *,
    parliament_id: str,
    enabled_rules: Sequence[tuple[str, str]],
    apply_exclusions: bool,
) -> MajoritySearchResult:
    mapped = seats_for_coalitions(seats, avg_df)
    total = sum(mapped.values()) or 1
    cfg = build_exclusion_config(enabled_rules, parliament_id=parliament_id)
    return possible_majorities(
        mapped,
        total,
        max_parties=4,
        parliament_id=parliament_id,
        apply_exclusions=apply_exclusions,
        rules_config=cfg,
    )


@st.cache_data(ttl=300, show_spinner=False)
def coalition_probabilities(
    parliament_id: str,
    coalition_tuples: tuple[tuple[str, ...], ...],
    days: int = 120,
    n_sim: int = 300,
) -> pd.DataFrame:
    avg_df = compute_current_averages(parliament_id, days=days)
    if avg_df.empty or not coalition_tuples:
        return pd.DataFrame()
    means = {row.party_id: float(row.average_share) for row in avg_df.itertuples()}
    parties = party_uncertainties_from_means(means, sample_size=1000, house_variance=1.0)
    _, seats_id, _ = project_seats(parliament_id, days=days)
    total = sum(seats_id.values()) or 630
    thr = 0.05
    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    if parliament:
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )
        thr = system.threshold_percent / 100.0
        total = system.seats_total

    def alloc(votes: dict[str, float]) -> dict[str, int]:
        if parliament:
            return allocate_seats(parliament, votes, election_system=system)
        return sainte_lague_schepers(votes, total, thr)

    # Koalitionen sind kanonische IDs — Simulation nutzt warehouse IDs.
    # Mappe Koalition zurück auf warehouse party_ids über Namen.
    name_to_id = dict(zip(avg_df["party_name"], avg_df["party_id"]))
    canon_to_id = {}
    for name, pid in name_to_id.items():
        canon = SHORT_TO_CANONICAL.get(str(name))
        if canon:
            canon_to_id[canon] = pid

    mapped_coalitions = []
    for coal in coalition_tuples:
        ids = tuple(sorted(canon_to_id[c] for c in coal if c in canon_to_id))
        if len(ids) == len(coal):
            mapped_coalitions.append(ids)

    result = simulate_uncertainty(
        parties,
        mapped_coalitions,
        allocate=alloc,
        total_seats=total,
        config=UncertaintyConfig(n_simulations=n_sim, seed=42),
    )
    rows = [
        {
            "coalition": " + ".join(c.parties),
            "probability": c.majority_probability,
            "n_majority": c.n_majority,
        }
        for c in result.coalition_probabilities
    ]
    return pd.DataFrame(rows)


def default_exclusion_toggles(parliament_id: str) -> list[tuple[str, str, str]]:
    """Liste (label, party, excluded) aus YAML."""
    cfg = load_coalition_rules()
    out: list[tuple[str, str, str]] = []
    for excl in cfg.exclusions:
        if excl.parliament_id and excl.parliament_id != parliament_id:
            continue
        for rule in excl.rules:
            for other in rule.excludes:
                label = f"{rule.party} schließt {other} aus"
                out.append((label, rule.party, other))
    return out
