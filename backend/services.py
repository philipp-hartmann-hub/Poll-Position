"""Orchestrierung: Warehouse lesen + analysis/-Funktionen aufrufen (ohne UI)."""

from __future__ import annotations

import copy
import time
from datetime import date, datetime, timedelta
from typing import Any

from analysis.averages import (
    PollObservationPoint,
    load_poll_points_from_warehouse,
    party_averages_for_parliament,
    party_trends_for_parliament,
)
from analysis.bundesrat import (
    choices_for_coalition,
    coalition_key,
    group_votes_by_coalition,
    load_bundesrat_config,
    parse_coalition_key,
    simulate_bundesrat,
)
from analysis.coalitions import list_active_exclusion_rules, possible_majorities
from analysis.house_effects import (
    aggregate_institute_leaderboard,
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
from analysis.seat_allocation import (
    allocate_seats,
    is_residual_party_id,
    sainte_lague_schepers,
)
from analysis.uncertainty import (
    UncertaintyConfig,
    party_uncertainties_from_means,
    simulate_threshold_watch,
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

# Stabile Dawum-Party-IDs → Shortcut (Fallback, wenn Warehouse-Join fehlt)
DAWUM_PARTY_SHORTCUTS: dict[str, str] = {
    "dawum:party:1": "CDU/CSU",
    "dawum:party:2": "SPD",
    "dawum:party:3": "FDP",
    "dawum:party:4": "Grüne",
    "dawum:party:5": "Linke",
    "dawum:party:7": "AfD",
    "dawum:party:8": "Freie Wähler",
    "dawum:party:23": "BSW",
    "de:sonstige": "Sonstige",
}

# Prozess-lokaler TTL-Cache (warme Serverless-Instanzen; Daily-Pipeline ~1×/Tag).
_PAYLOAD_TTL_SECONDS = 300.0
_averages_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_coalitions_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}


def clear_payload_caches() -> None:
    """Leert Averages-/Coalitions-Caches (Tests / nach Pipeline-Write)."""
    _averages_cache.clear()
    _coalitions_cache.clear()


def _ttl_get(
    cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]],
    key: tuple[Any, ...],
) -> dict[str, Any] | None:
    entry = cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        del cache[key]
        return None
    return copy.deepcopy(value)


def _ttl_set(
    cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]],
    key: tuple[Any, ...],
    value: dict[str, Any],
    *,
    ttl: float = _PAYLOAD_TTL_SECONDS,
) -> dict[str, Any]:
    cache[key] = (time.monotonic() + ttl, copy.deepcopy(value))
    return copy.deepcopy(value)


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()
    return date.fromisoformat(str(value)[:10])


def _party_name_map(con) -> dict[str, str]:
    rows = con.execute(
        """
        SELECT id,
               COALESCE(
                   NULLIF(TRIM(short_name), ''),
                   NULLIF(TRIM(full_name), ''),
                   id
               )
        FROM parties
        """
    ).fetchall()
    return {str(r[0]): str(r[1]) for r in rows}


def resolve_party_display_name(
    party_id: str,
    names: dict[str, str] | None = None,
) -> str:
    """Lesbarer Parteiname; nie rohe ``dawum:party:N`` wenn Shortcut bekannt."""
    pid = str(party_id)
    if names:
        hit = names.get(pid)
        if hit is not None:
            label = str(hit).strip()
            if label and label != pid and not label.startswith("dawum:party:"):
                return label
    if pid in DAWUM_PARTY_SHORTCUTS:
        return DAWUM_PARTY_SHORTCUTS[pid]
    for short, canon in SHORT_TO_CANONICAL.items():
        if canon == pid:
            return short
    return pid


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
    cache_key = (parliament_id, days)
    cached = _ttl_get(_averages_cache, cache_key)
    if cached is not None:
        return cached

    points = _load_points(parliament_id)
    if not points:
        return _ttl_set(
            _averages_cache,
            cache_key,
            {"parliament_id": parliament_id, "as_of": date.today(), "parties": []},
        )

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
            "party_name": resolve_party_display_name(a.party_id, names),
            "average_share": a.average_share,
            "n_surveys": a.n_surveys,
            "swing": a.swing,
            "trend_share": latest_trend.get(a.party_id),
        }
        for a in avgs
    ]
    parties.sort(
        key=lambda x: (
            x["party_name"] == "Sonstige" or x["party_id"] == "de:sonstige",
            -x["average_share"],
        )
    )
    return _ttl_set(
        _averages_cache,
        cache_key,
        {"parliament_id": parliament_id, "as_of": date.today(), "parties": parties},
    )


def party_trend_series_payload(parliament_id: str, *, days: int = 365) -> dict[str, Any]:
    """Chronologische Trendpunkte je Partei aus Gold-Tabelle `party_trends`."""
    since = date.today() - timedelta(days=days)
    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        names = _party_name_map(con)
        rows = con.execute(
            """
            SELECT party_id, as_of, trend_share
            FROM party_trends
            WHERE parliament_id = ?
              AND as_of >= ?
            ORDER BY party_id, as_of
            """,
            [parliament_id, since],
        ).fetchall()
    finally:
        con.close()

    by_party: dict[str, list[dict[str, Any]]] = {}
    for party_id, as_of, trend_share in rows:
        by_party.setdefault(str(party_id), []).append(
            {"as_of": _as_date(as_of), "trend_share": float(trend_share)}
        )

    parties = [
        {
            "party_id": pid,
            "party_name": resolve_party_display_name(pid, names),
            "points": points,
        }
        for pid, points in by_party.items()
    ]
    parties.sort(key=lambda p: (-(p["points"][-1]["trend_share"] if p["points"] else 0.0), p["party_id"]))
    return {"parliament_id": parliament_id, "days": days, "parties": parties}


def raw_surveys_payload(
    parliament_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Einzelne Umfragen (nicht aggregiert), neueste zuerst, paginiert."""
    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        total = int(
            con.execute(
                "SELECT COUNT(*) FROM surveys WHERE parliament_id = ?",
                [parliament_id],
            ).fetchone()[0]
        )
        survey_rows = con.execute(
            """
            SELECT
                s.id,
                s.institute_id,
                i.name,
                s.field_date_from,
                s.field_date_to,
                s.publication_date,
                s.sample_size,
                s.source_url
            FROM surveys s
            LEFT JOIN institutes i ON i.id = s.institute_id
            WHERE s.parliament_id = ?
            ORDER BY s.publication_date DESC, s.id DESC
            LIMIT ? OFFSET ?
            """,
            [parliament_id, limit, offset],
        ).fetchall()
        party_names = _party_name_map(con)
        ids = [r[0] for r in survey_rows]
        results_by_survey: dict[str, list[dict[str, Any]]] = {sid: [] for sid in ids}
        if ids:
            placeholders = ", ".join(["?"] * len(ids))
            result_rows = con.execute(
                f"""
                SELECT survey_id, party_id, share
                FROM survey_results
                WHERE survey_id IN ({placeholders})
                ORDER BY share DESC
                """,
                ids,
            ).fetchall()
            for survey_id, party_id, share in result_rows:
                results_by_survey[str(survey_id)].append(
                    {
                        "party_id": str(party_id),
                        "party_name": resolve_party_display_name(
                            str(party_id), party_names
                        ),
                        "share": float(share),
                    }
                )
    finally:
        con.close()

    surveys = [
        {
            "id": row[0],
            "institute_id": row[1],
            "institute_name": row[2],
            "field_date_from": _as_date(row[3]) if row[3] is not None else None,
            "field_date_to": _as_date(row[4]) if row[4] is not None else None,
            "publication_date": _as_date(row[5]),
            "sample_size": int(row[6]) if row[6] is not None else None,
            "source_url": row[7],
            "results": results_by_survey.get(row[0], []),
        }
        for row in survey_rows
    ]
    return {
        "parliament_id": parliament_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "surveys": surveys,
    }


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
        if not system.seat_projection:
            return {}, system.seats_total
        seats = allocate_seats(parliament, votes, election_system=system)
        return seats, system.seats_total
    seats = sainte_lague_schepers(votes, 100, 0.05)
    return seats, sum(seats.values())


def _seat_projection_enabled(parliament_id: str) -> bool | None:
    """True/False wenn Parlament bekannt, sonst None (Fallback-Allokation)."""
    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    if not parliament:
        return None
    system = next(
        s for s in bundle.election_systems if s.key == parliament.election_system_key
    )
    return bool(system.seat_projection)


def seats_payload(parliament_id: str) -> dict[str, Any]:
    """
    Sitzprojektion. Bei leerem ``seats`` steht ``reason``:
    ``no_averages`` | ``all_below_threshold`` | ``no_seat_projection``.
    """
    votes, names = _votes_from_averages(parliament_id)
    try:
        ensure_warehouse()
        con = connect_warehouse(read_only=not uses_motherduck())
        try:
            names = {**names, **_party_name_map(con)}
        finally:
            con.close()
    except Exception:
        pass
    if not votes:
        return {
            "parliament_id": parliament_id,
            "total_seats": 0,
            "seats": {},
            "seats_by_name": {},
            "reason": "no_averages",
        }

    projection = _seat_projection_enabled(parliament_id)
    if projection is False:
        bundle = load_parliament_config()
        parliament = next(p for p in bundle.parliaments if p.id == parliament_id)
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )
        return {
            "parliament_id": parliament_id,
            "total_seats": system.seats_total,
            "seats": {},
            "seats_by_name": {},
            "reason": "no_seat_projection",
        }

    seats, total = _allocate_for_parliament(parliament_id, votes)
    # Restkategorie nie in der Sitz-/Koalitions-UI
    seats = {
        pid: n
        for pid, n in seats.items()
        if n > 0 and not _is_residual_party(pid, names.get(pid))
    }
    by_name = {
        resolve_party_display_name(k, names): v for k, v in seats.items()
    }
    if not seats:
        return {
            "parliament_id": parliament_id,
            "total_seats": total,
            "seats": {},
            "seats_by_name": {},
            "reason": "all_below_threshold",
        }
    return {
        "parliament_id": parliament_id,
        "total_seats": total,
        "seats": seats,
        "seats_by_name": by_name,
        "reason": None,
    }


def _is_residual_party(party_id: str, name: str | None = None) -> bool:
    if is_residual_party_id(party_id):
        return True
    if name:
        low = name.strip().lower()
        if low in {"sonstige", "others", "other", "oth", "oth."}:
            return True
        if "sonstige" in low:
            return True
    canon = SHORT_TO_CANONICAL.get(name or "", "")
    return is_residual_party_id(canon)


def _seats_to_canonical(seats: dict[str, int], names: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for pid, n in seats.items():
        if n <= 0:
            continue
        name = names.get(pid, pid)
        if _is_residual_party(pid, name):
            continue
        canon = SHORT_TO_CANONICAL.get(name, pid)
        if is_residual_party_id(canon):
            continue
        out[canon] = out.get(canon, 0) + n
    return out


def coalitions_payload(
    parliament_id: str,
    *,
    apply_exclusions: bool = True,
    max_parties: int = 4,
    disabled_rule_ids: list[str] | None = None,
) -> dict[str, Any]:
    disabled = tuple(sorted(disabled_rule_ids or []))
    cache_key = (parliament_id, apply_exclusions, max_parties, disabled)
    cached = _ttl_get(_coalitions_cache, cache_key)
    if cached is not None:
        return cached

    seats_data = seats_payload(parliament_id)
    seats = seats_data["seats"]
    total = int(seats_data["total_seats"] or 0)
    if not seats or total <= 0:
        # Leeres Warehouse / keine Umfragen — Endpoint liefert 404, kein 500.
        return _ttl_set(
            _coalitions_cache,
            cache_key,
            {
                "parliament_id": parliament_id,
                "total_seats": 0,
                "majority_threshold": 0,
                "excluded_by_rules": 0,
                "coalitions": [],
            },
        )
    _, names = _votes_from_averages(parliament_id)
    canon = _seats_to_canonical(seats, names)
    if not canon:
        return _ttl_set(
            _coalitions_cache,
            cache_key,
            {
                "parliament_id": parliament_id,
                "total_seats": total,
                "majority_threshold": 0,
                "excluded_by_rules": 0,
                "coalitions": [],
            },
        )
    total = total or sum(canon.values())
    result = possible_majorities(
        canon,
        total,
        max_parties=max_parties,
        parliament_id=parliament_id,
        apply_exclusions=apply_exclusions,
        disabled_rule_ids=list(disabled) if disabled else None,
    )
    coalitions_out = []
    for c in result.coalitions:
        parties = [p for p in c.parties if not is_residual_party_id(p)]
        if len(parties) != len(c.parties):
            continue
        coalitions_out.append(
            {
                "parties": parties,
                "seats": c.seats,
                "is_minimal_winning": c.is_minimal_winning,
                "compatibility_span": c.compatibility_span,
            }
        )
    return _ttl_set(
        _coalitions_cache,
        cache_key,
        {
            "parliament_id": parliament_id,
            "total_seats": result.total_seats,
            "majority_threshold": result.majority_threshold,
            "excluded_by_rules": result.excluded_by_rules,
            "coalitions": coalitions_out,
        },
    )


def coalition_rules_payload(parliament_id: str) -> dict[str, Any]:
    """Aktive Ausschlussregeln für ein Parlament (UI-Checkboxen)."""
    rules = list_active_exclusion_rules(parliament_id)
    return {
        "parliament_id": parliament_id,
        "rules": [
            {
                "id": r.id or "",
                "party": r.party,
                "excludes": list(r.excludes),
                "note": r.note,
            }
            for r in rules
            if r.id
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
    id_to_canon = {v: k for k, v in canon_to_id.items()}
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
                "parties": [id_to_canon.get(p, p) for p in c.parties],
                "majority_probability": c.majority_probability,
                "n_majority": c.n_majority,
                "n_simulations": c.n_simulations,
            }
            for c in result.coalition_probabilities
        ],
    }


def _election_system_for(parliament_id: str):
    bundle = load_parliament_config()
    parliament = next((p for p in bundle.parliaments if p.id == parliament_id), None)
    if not parliament:
        return None, None
    system = next(
        s for s in bundle.election_systems if s.key == parliament.election_system_key
    )
    return parliament, system


def _threshold_exempt_ids(
    names: dict[str, str],
    *,
    minority_exempt_party_ids: list[str],
) -> set[str]:
    """Warehouse-IDs, die nicht vor die Sperrklausel gestellt werden (Minderheit)."""
    exempt_canon = set(minority_exempt_party_ids)
    out: set[str] = set()
    for pid, name in names.items():
        canon = SHORT_TO_CANONICAL.get(name, pid)
        if pid in exempt_canon or canon in exempt_canon or name in exempt_canon:
            out.add(pid)
        if name == "Sonstige" or canon == "de:sonstige":
            out.add(pid)
    return out


def threshold_watch_payload(
    parliament_id: str,
    *,
    band_points: float = 3.0,
    n_simulations: int = 400,
) -> dict[str, Any]:
    votes, names = _votes_from_averages(parliament_id)
    # Averages-TTL-Cache kann veraltete/fehlende Namen tragen — Warehouse nochmal mergen.
    try:
        ensure_warehouse()
        con = connect_warehouse(read_only=not uses_motherduck())
        try:
            names = {**names, **_party_name_map(con)}
        finally:
            con.close()
    except Exception:
        # Read-only / Cold-Start: Dawum-Shortcuts in resolve_party_display_name
        pass

    _parliament, system = _election_system_for(parliament_id)
    threshold = float(system.threshold_percent) if system else 5.0
    minority = list(system.minority_exempt_party_ids) if system else []
    empty = {
        "parliament_id": parliament_id,
        "threshold_percent": threshold,
        "band_points": band_points,
        "n_simulations": 0,
        "parties": [],
    }
    if not votes:
        return empty

    exempt = _threshold_exempt_ids(names, minority_exempt_party_ids=minority)
    parties = party_uncertainties_from_means(votes, sample_size=1000, house_variance=1.0)
    rows = simulate_threshold_watch(
        parties,
        threshold_percent=threshold,
        band_points=band_points,
        exempt_party_ids=sorted(exempt),
        config=UncertaintyConfig(n_simulations=n_simulations, seed=42),
    )
    return {
        "parliament_id": parliament_id,
        "threshold_percent": threshold,
        "band_points": band_points,
        "n_simulations": n_simulations if rows else 0,
        "parties": [
            {
                "party_id": r.party_id,
                "party_name": resolve_party_display_name(r.party_id, names),
                "average_share": r.mean_share,
                "threshold_percent": r.threshold_percent,
                "probability_below_threshold": r.probability_below_threshold,
            }
            for r in rows
        ],
    }


def threshold_watch_overview_payload(
    *,
    band_points: float = 3.0,
    limit: int = 8,
) -> dict[str, Any]:
    """Kritischste Sperrklausel-Fälle über DE-Parlamente (für die Startseite)."""
    items: list[dict[str, Any]] = []
    for parl in list_parliaments():
        if parl.get("country") != "DE":
            continue
        watch = threshold_watch_payload(parl["id"], band_points=band_points, n_simulations=250)
        for p in watch["parties"]:
            prob = float(p["probability_below_threshold"])
            items.append(
                {
                    **p,
                    "parliament_id": parl["id"],
                    "parliament_name": parl.get("name"),
                    "toss_up": min(prob, 1.0 - prob),
                }
            )
    items.sort(key=lambda r: (-r["toss_up"], -abs(r["average_share"] - r["threshold_percent"])))
    return {"band_points": band_points, "items": items[:limit]}


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
        tuples = _election_tuples_for_backtest(pnames, parliament_id=parliament_id)
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


def _election_tuples_for_backtest(
    pnames: dict[str, str],
    *,
    parliament_id: str | None = None,
) -> list[tuple[str, date, dict[str, float]]]:
    elections = load_election_results()
    relevant = [
        e
        for e in elections.elections
        if parliament_id is None or e.parliament_id == parliament_id
    ]
    canon_to_name = {v: k for k, v in SHORT_TO_CANONICAL.items()}
    name_to_wh = {v: k for k, v in pnames.items()}
    tuples: list[tuple[str, date, dict[str, float]]] = []
    for el in relevant:
        mapped: dict[str, float] = {}
        for pid, share in el.results.items():
            pname = canon_to_name.get(pid)
            wh = name_to_wh.get(pname) if pname else None
            if wh:
                mapped[wh] = float(share)
        if mapped:
            tuples.append((el.parliament_id, el.election_date, mapped))
    return tuples


def institute_leaderboard_payload() -> dict[str, Any]:
    """Gesamt-Rangliste der Institute über alle Parlamente mit Backtest-Daten."""
    points = _load_points(None)
    if not points:
        return {"institutes": []}

    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        inames = _institute_name_map(con)
        pnames = _party_name_map(con)
    finally:
        con.close()

    tuples = _election_tuples_for_backtest(pnames)
    if not tuples:
        return {"institutes": []}

    records = backtest_institutes(points, tuples)
    per_parliament = institute_accuracy_scores(records, by_parliament=True)
    ranked = aggregate_institute_leaderboard(per_parliament)

    institutes = []
    for rank, entry in enumerate(ranked, start=1):
        institutes.append(
            {
                "rank": rank,
                "institute_id": entry.institute_id,
                "institute_name": inames.get(entry.institute_id),
                "n_comparisons": entry.n_comparisons,
                "mae": entry.mae,
                "rmse": entry.rmse,
                "score": entry.score,
                "by_parliament": [
                    {
                        "institute_id": d.institute_id,
                        "institute_name": inames.get(d.institute_id),
                        "parliament_id": d.parliament_id,
                        "n_comparisons": d.n_comparisons,
                        "mae": d.mae,
                        "rmse": d.rmse,
                        "score": d.score,
                    }
                    for d in entry.details
                ],
            }
        )
    return {"institutes": institutes}


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


BUNDESRAT_DISCLAIMER = (
    "Basierend auf den aktuell amtierenden Landesregierungen (Stand siehe Datum), "
    "nicht auf Umfragen-Projektionen der Landtage — die kannst du über die "
    "Dropdowns selbst durchspielen."
)

_ALLOWED_STANCES = frozenset({"default", "abstain", "enthaltung", "nein", "reject", "no"})


def _bundesrat_coalition_options(parliament_id: str) -> list[dict[str, Any]]:
    """Mehrheitsfähige Umfrage-Koalitionen für ein Land (Sandbox-Dropdown)."""
    try:
        data = coalitions_payload(
            parliament_id,
            apply_exclusions=True,
            max_parties=4,
        )
    except Exception:
        return []
    options: list[dict[str, Any]] = []
    for c in data.get("coalitions") or []:
        parties = list(c.get("parties") or [])
        if len(parties) < 2:
            continue
        options.append(
            {
                "key": coalition_key(parties),
                "parties": parties,
                "seats": int(c.get("seats") or 0),
                "is_minimal_winning": bool(c.get("is_minimal_winning")),
            }
        )
    return options


def _tally_to_dict(sim: Any) -> dict[str, Any]:
    return {
        "yes_votes": sim.yes,
        "no_votes": sim.no,
        "abstain_votes": sim.abstain,
        "has_majority": sim.has_simple_majority,
        "has_two_thirds": sim.has_two_thirds_majority,
        "by_land": [
            {
                "parliament_id": r.parliament_id,
                "name": r.name,
                "votes": r.votes,
                "stance": r.stance,
                "government": list(r.parties),
                "government_label": r.government_label,
                "source": r.source,
            }
            for r in sim.states
        ],
    }


def bundesrat_status_payload() -> dict[str, Any]:
    cfg = load_bundesrat_config()
    land_rows: list[dict[str, Any]] = []
    for land in cfg.states:
        land_rows.append(
            {
                "parliament_id": land.parliament_id,
                "name": land.name,
                "votes": land.votes,
                "default_government": list(land.government_parties),
                "default_government_label": land.government_label,
                "coalition_options": _bundesrat_coalition_options(land.parliament_id),
            }
        )
    sim = simulate_bundesrat(cfg, choices={})
    return {
        "as_of": cfg.stand,
        "disclaimer": BUNDESRAT_DISCLAIMER,
        "sources": list(cfg.sources),
        "total_votes": cfg.votes_total,
        "majority_threshold": cfg.majority_simple,
        "two_thirds_threshold": cfg.majority_two_thirds,
        "laender": land_rows,
        "simulation": _tally_to_dict(sim),
    }


def bundesrat_simulate_payload(choices: dict[str, str]) -> dict[str, Any]:
    cfg = load_bundesrat_config()
    cleaned: dict[str, str] = {}
    known = {land.parliament_id for land in cfg.states}
    labels: dict[str, str] = {}
    for pid, choice in choices.items():
        if pid not in known:
            raise ValueError(f"Unbekanntes Land: {pid}")
        value = (choice or "default").strip()
        lower = value.lower()
        if lower in _ALLOWED_STANCES:
            cleaned[pid] = "reject" if lower in {"nein", "no", "reject"} else (
                "abstain" if lower in {"abstain", "enthaltung"} else "default"
            )
        elif "+" in value:
            parties = parse_coalition_key(value)
            cleaned[pid] = coalition_key(parties)
            labels[cleaned[pid]] = " + ".join(parties)
        else:
            raise ValueError(
                f"Ungültige Wahl für {pid}: {choice!r} "
                f"(erwartet: default | abstain | reject | de:a+de:b)"
            )
    sim = simulate_bundesrat(cfg, choices=cleaned, coalition_labels=labels)
    return {
        "as_of": cfg.stand,
        "disclaimer": BUNDESRAT_DISCLAIMER,
        "total_votes": cfg.votes_total,
        "majority_threshold": cfg.majority_simple,
        "two_thirds_threshold": cfg.majority_two_thirds,
        **_tally_to_dict(sim),
    }


def bundesrat_majority_check_payload(*, limit: int = 8) -> dict[str, Any]:
    """Amtierende Bundesregierung + Top-Bundestags-Koalitionen × Art. 51 Abs. 3."""
    cfg = load_bundesrat_config()
    rows: list[dict[str, Any]] = []

    if cfg.bundesregierung and cfg.bundesregierung.parties:
        fed_parties = list(cfg.bundesregierung.parties)
        choices = choices_for_coalition(cfg, fed_parties)
        sim = simulate_bundesrat(cfg, choices=choices)
        rows.append(
            {
                "parties": fed_parties,
                "label": cfg.bundesregierung.label,
                "bundestag_seats": 0,
                "is_minimal_winning": False,
                "is_incumbent": True,
                "choices": choices,
                "yes_votes": sim.yes,
                "no_votes": sim.no,
                "abstain_votes": sim.abstain,
                "has_majority": sim.has_simple_majority,
                "has_two_thirds": sim.has_two_thirds_majority,
            }
        )

    coal = coalitions_payload("de_bundestag", apply_exclusions=True, max_parties=4)
    for c in (coal.get("coalitions") or [])[:limit]:
        parties = [p for p in (c.get("parties") or []) if not is_residual_party_id(p)]
        if not parties:
            continue
        choices = choices_for_coalition(cfg, parties)
        sim = simulate_bundesrat(cfg, choices=choices)
        rows.append(
            {
                "parties": parties,
                "label": None,
                "bundestag_seats": int(c.get("seats") or 0),
                "is_minimal_winning": bool(c.get("is_minimal_winning")),
                "is_incumbent": False,
                "choices": choices,
                "yes_votes": sim.yes,
                "no_votes": sim.no,
                "abstain_votes": sim.abstain,
                "has_majority": sim.has_simple_majority,
                "has_two_thirds": sim.has_two_thirds_majority,
            }
        )

    balance = [
        {
            "key": g.key,
            "label": g.label,
            "parties_normalized": list(g.parties_normalized),
            "votes": g.votes,
            "parliament_ids": list(g.parliament_ids),
            "matches_federal": g.matches_federal,
        }
        for g in group_votes_by_coalition(cfg)
    ]

    fed = cfg.bundesregierung
    return {
        "as_of": cfg.stand,
        "total_votes": cfg.votes_total,
        "majority_threshold": cfg.majority_simple,
        "two_thirds_threshold": cfg.majority_two_thirds,
        "federal_government": (
            {
                "stand": fed.stand,
                "parties": list(fed.parties),
                "label": fed.label,
            }
            if fed
            else None
        ),
        "coalition_balance": balance,
        "coalitions": rows,
    }


def scenario_payload(
    parliament_id: str,
    party_shares: dict[str, float],
    *,
    apply_exclusions: bool = True,
    max_coalition_parties: int = 4,
    disabled_rule_ids: list[str] | None = None,
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
        disabled_rule_ids=disabled_rule_ids,
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
