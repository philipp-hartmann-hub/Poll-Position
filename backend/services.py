"""Orchestrierung: Warehouse lesen + analysis/-Funktionen aufrufen (ohne UI)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from analysis.averages import (
    PollObservationPoint,
    load_poll_points_from_warehouse,
    party_averages_for_parliament,
    party_trends_for_parliament,
)
from analysis.coalitions import possible_majorities
from analysis.house_effects import (
    backtest_institutes,
    compute_house_effects,
    institute_accuracy_scores,
)
from analysis.party_families import (
    EuropeanPartyFamily,
    aggregate_by_family,
    load_party_families,
    map_party_to_family,
)
from analysis.scenario import ScenarioInput, run_scenario
from analysis.seat_allocation import allocate_seats, sainte_lague_schepers
from analysis.uncertainty import (
    UncertaintyConfig,
    party_uncertainties_from_means,
    simulate_uncertainty,
)
from data_pipeline.reference.election_results import load_election_results
from data_pipeline.schema import load_parliament_config
from data_pipeline.warehouse import connect_warehouse, ensure_warehouse, uses_motherduck

# Kurzname → kanonische ID (Koalitionsregeln / Familien)
SHORT_TO_CANONICAL: dict[str, str] = {
    "AfD": "de:afd",
    "CDU/CSU": "de:cdu_csu",
    "CDU": "de:cdu",
    "CSU": "de:csu",
    "SPD": "de:spd",
    "Grüne": "de:gruene",
    "FDP": "de:fdp",
    "Linke": "de:linke",
    "BSW": "de:bsw",
    "SSW": "de:ssw",
    "Sonstige": "de:sonstige",
    "Freie Wähler": "de:fw",
}


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()
    return date.fromisoformat(str(value)[:10])


def _party_name_map(con) -> dict[str, str]:
    rows = con.execute("SELECT id, short_name FROM parties").fetchall()
    return {r[0]: r[1] for r in rows}


def _institute_name_map(con) -> dict[str, str]:
    rows = con.execute("SELECT id, name FROM institutes").fetchall()
    return {r[0]: r[1] for r in rows}


def list_parliaments() -> list[dict[str, Any]]:
    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        rows = con.execute(
            """
            SELECT id, name, country, level_kind, state_code, seats_total,
                   election_system_key, shortcut
            FROM parliaments
            ORDER BY country, level_kind, name
            """
        ).fetchall()
        cols = [
            "id",
            "name",
            "country",
            "level_kind",
            "state_code",
            "seats_total",
            "election_system_key",
            "shortcut",
        ]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        con.close()


def _load_points(parliament_id: str | None = None) -> list[PollObservationPoint]:
    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        points = load_poll_points_from_warehouse(con)
    finally:
        con.close()
    if parliament_id:
        points = [p for p in points if p.parliament_id == parliament_id]
    return points


def party_averages_payload(parliament_id: str, *, days: int = 365) -> dict[str, Any]:
    points = _load_points(parliament_id)
    if not points:
        return {"parliament_id": parliament_id, "as_of": date.today(), "parties": []}

    since = date.today() - timedelta(days=days)
    points = [p for p in points if p.as_of >= since]
    avgs = party_averages_for_parliament(
        points, parliament_id=parliament_id, reference_date=date.today()
    )
    trends = party_trends_for_parliament(points, parliament_id=parliament_id)
    latest_trend: dict[str, float] = {}
    for t in trends:
        latest_trend[t.party_id] = t.trend_share  # chronologisch → letzter gewinnt

    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        names = _party_name_map(con)
    finally:
        con.close()

    parties = [
        {
            "parliament_id": a.parliament_id,
            "party_id": a.party_id,
            "party_name": names.get(a.party_id, a.party_id),
            "average_share": a.average_share,
            "n_surveys": a.n_surveys,
            "swing": a.swing,
            "trend_share": latest_trend.get(a.party_id),
        }
        for a in sorted(avgs, key=lambda x: -x.average_share)
    ]
    return {"parliament_id": parliament_id, "as_of": date.today(), "parties": parties}


def _votes_from_averages(parliament_id: str) -> tuple[dict[str, float], dict[str, str]]:
    payload = party_averages_payload(parliament_id)
    votes = {p["party_id"]: float(p["average_share"]) for p in payload["parties"]}
    names = {p["party_id"]: p["party_name"] for p in payload["parties"]}
    return votes, names


def _allocate_for_parliament(parliament_id: str, votes: dict[str, float]) -> tuple[dict[str, int], int]:
    if not votes:
        return {}, 0
    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    if parliament:
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )
        seats = allocate_seats(parliament, votes, election_system=system)
        return seats, system.seats_total
    seats = sainte_lague_schepers(votes, 100, 0.05)
    return seats, sum(seats.values())


def seats_payload(parliament_id: str) -> dict[str, Any]:
    votes, names = _votes_from_averages(parliament_id)
    seats, total = _allocate_for_parliament(parliament_id, votes)
    by_name = {names.get(k, k): v for k, v in seats.items()}
    return {
        "parliament_id": parliament_id,
        "total_seats": total,
        "seats": seats,
        "seats_by_name": by_name,
    }


def _seats_to_canonical(seats: dict[str, int], names: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for pid, n in seats.items():
        if n <= 0:
            continue
        name = names.get(pid, pid)
        canon = SHORT_TO_CANONICAL.get(name, pid)
        out[canon] = out.get(canon, 0) + n
    return out


def coalitions_payload(
    parliament_id: str,
    *,
    apply_exclusions: bool = True,
    max_parties: int = 4,
) -> dict[str, Any]:
    seats_data = seats_payload(parliament_id)
    seats = seats_data["seats"]
    _, names = _votes_from_averages(parliament_id)
    canon = _seats_to_canonical(seats, names)
    total = seats_data["total_seats"] or sum(canon.values())
    result = possible_majorities(
        canon,
        total,
        max_parties=max_parties,
        parliament_id=parliament_id,
        apply_exclusions=apply_exclusions,
    )
    return {
        "parliament_id": parliament_id,
        "total_seats": result.total_seats,
        "majority_threshold": result.majority_threshold,
        "excluded_by_rules": result.excluded_by_rules,
        "coalitions": [
            {
                "parties": list(c.parties),
                "seats": c.seats,
                "is_minimal_winning": c.is_minimal_winning,
                "compatibility_span": c.compatibility_span,
            }
            for c in result.coalitions
        ],
    }


def uncertainty_payload(
    parliament_id: str,
    *,
    n_simulations: int = 400,
) -> dict[str, Any]:
    votes, _names = _votes_from_averages(parliament_id)
    if not votes:
        return {
            "parliament_id": parliament_id,
            "n_simulations": 0,
            "mean_seats": {},
            "coalition_probabilities": [],
        }
    parties = party_uncertainties_from_means(votes, sample_size=1000, house_variance=1.0)
    seats, total = _allocate_for_parliament(parliament_id, votes)
    coal = coalitions_payload(parliament_id)
    # Koalitionen sind kanonisch — Simulation nutzt warehouse IDs
    names = _names
    canon_to_id = {
        SHORT_TO_CANONICAL[name]: pid
        for pid, name in names.items()
        if name in SHORT_TO_CANONICAL
    }
    mapped: list[tuple[str, ...]] = []
    for c in coal["coalitions"][:8]:
        ids = tuple(sorted(canon_to_id[p] for p in c["parties"] if p in canon_to_id))
        if len(ids) == len(c["parties"]):
            mapped.append(ids)

    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    system = None
    if parliament:
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )

    def alloc(v: dict[str, float]) -> dict[str, int]:
        if parliament and system:
            return allocate_seats(parliament, v, election_system=system)
        return sainte_lague_schepers(v, total or 630, 0.05)

    result = simulate_uncertainty(
        parties,
        mapped,
        allocate=alloc,
        total_seats=total or 630,
        config=UncertaintyConfig(n_simulations=n_simulations, seed=42),
    )
    return {
        "parliament_id": parliament_id,
        "n_simulations": result.n_simulations,
        "mean_seats": result.mean_seats,
        "coalition_probabilities": [
            {
                "parties": list(c.parties),
                "majority_probability": c.majority_probability,
                "n_majority": c.n_majority,
                "n_simulations": c.n_simulations,
            }
            for c in result.coalition_probabilities
        ],
    }


def house_effects_payload(
    parliament_id: str | None = None,
    *,
    window_days: int = 14,
) -> dict[str, Any]:
    points = _load_points(parliament_id)
    if not points:
        return {"parliament_id": parliament_id, "effects": [], "accuracy": []}

    ref_dates = sorted({p.as_of for p in points})
    step = max(1, len(ref_dates) // 24)
    sample = ref_dates[::step][-24:]
    effects = compute_house_effects(points, window_days=window_days, reference_dates=sample)

    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        inames = _institute_name_map(con)
        pnames = _party_name_map(con)
    finally:
        con.close()

    effect_rows = [
        {
            "institute_id": e.institute_id,
            "institute_name": inames.get(e.institute_id),
            "party_id": e.party_id,
            "party_name": pnames.get(e.party_id),
            "as_of": e.as_of,
            "house_effect": e.house_effect,
            "institute_share": e.institute_share,
            "peer_average": e.peer_average,
        }
        for e in effects
    ]

    accuracy_rows: list[dict[str, Any]] = []
    try:
        elections = load_election_results()
        relevant = [
            e
            for e in elections.elections
            if parliament_id is None or e.parliament_id == parliament_id
        ]
        canon_to_name = {v: k for k, v in SHORT_TO_CANONICAL.items()}
        name_to_wh = {v: k for k, v in pnames.items()}
        tuples = []
        for el in relevant:
            mapped: dict[str, float] = {}
            for pid, share in el.results.items():
                pname = canon_to_name.get(pid)
                wh = name_to_wh.get(pname) if pname else None
                if wh:
                    mapped[wh] = float(share)
            if mapped:
                tuples.append((el.parliament_id, el.election_date, mapped))
        if tuples:
            records = backtest_institutes(points, tuples)
            for s in institute_accuracy_scores(records):
                accuracy_rows.append(
                    {
                        "institute_id": s.institute_id,
                        "institute_name": inames.get(s.institute_id),
                        "parliament_id": s.parliament_id,
                        "n_comparisons": s.n_comparisons,
                        "mae": s.mae,
                        "rmse": s.rmse,
                        "score": s.score,
                    }
                )
    except Exception:  # noqa: BLE001 — Backtest optional
        pass

    return {
        "parliament_id": parliament_id,
        "effects": effect_rows,
        "accuracy": accuracy_rows,
    }


def europe_overview_payload() -> dict[str, Any]:
    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        rows = con.execute(
            """
            WITH latest AS (
                SELECT parliament_id, MAX(publication_date) AS max_date
                FROM surveys
                GROUP BY parliament_id
            )
            SELECT
                par.country,
                par.level_kind,
                r.party_id,
                COALESCE(p.short_name, r.party_id) AS party_name,
                AVG(r.share) AS share
            FROM surveys s
            JOIN latest l ON l.parliament_id = s.parliament_id
                AND l.max_date = s.publication_date
            JOIN survey_results r ON r.survey_id = s.id
            LEFT JOIN parties p ON p.id = r.party_id
            LEFT JOIN parliaments par ON par.id = s.parliament_id
            GROUP BY 1, 2, 3, 4
            """
        ).fetchall()
    finally:
        con.close()

    cfg = load_party_families()
    name_to_canon = dict(SHORT_TO_CANONICAL)
    for entry in cfg.parties:
        name_to_canon.setdefault(entry.short_name, entry.party_id)

    by_country: dict[str, list[tuple[str, str, float]]] = {}
    for country, level_kind, party_id, party_name, share in rows:
        if country is None:
            continue
        if level_kind not in ("national", "eu_parliament", None):
            # National bevorzugen; wenn leer, alles nehmen
            pass
        by_country.setdefault(str(country), []).append(
            (str(party_id), str(party_name), float(share))
        )

    # Filter: nur national wenn vorhanden
    countries_out = []
    for country, parties in sorted(by_country.items()):
        parties_sorted = sorted(parties, key=lambda x: -x[2])
        top_id, top_name, top_share = parties_sorted[0]
        shares: dict[str, float] = {}
        for _pid, pname, share in parties_sorted:
            canon = name_to_canon.get(pname, _pid)
            shares[canon] = shares.get(canon, 0.0) + share
        fam = aggregate_by_family(shares, config=cfg)
        if fam:
            top_fam = max(fam, key=fam.get)  # type: ignore[arg-type]
            fam_share = fam[top_fam]
            fam_label = top_fam.value if hasattr(top_fam, "value") else str(top_fam)
        else:
            mapped = map_party_to_family(
                name_to_canon.get(top_name, top_id), config=cfg
            ) or EuropeanPartyFamily.NI
            fam_label = mapped.value
            fam_share = top_share
        countries_out.append(
            {
                "country": country,
                "top_party_name": top_name,
                "top_party_share": top_share,
                "top_family": fam_label,
                "family_share": float(fam_share),
            }
        )

    return {"as_of": date.today(), "countries": countries_out}


def scenario_payload(
    parliament_id: str,
    party_shares: dict[str, float],
    *,
    apply_exclusions: bool = True,
    max_coalition_parties: int = 4,
) -> dict[str, Any]:
    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    system = None
    if parliament:
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )
    result = run_scenario(
        ScenarioInput(party_shares=party_shares, parliament_id=parliament_id),
        parliament=parliament,
        election_system=system,
        apply_exclusions=apply_exclusions,
        max_coalition_parties=max_coalition_parties,
    )
    return {
        "parliament_id": parliament_id,
        "party_shares": result.party_shares,
        "seats": result.seats,
        "total_seats": result.total_seats,
        "majority_threshold": result.majorities.majority_threshold,
        "coalitions": [
            {
                "parties": list(c.parties),
                "seats": c.seats,
                "is_minimal_winning": c.is_minimal_winning,
                "compatibility_span": c.compatibility_span,
            }
            for c in result.majorities.coalitions
        ],
    }
