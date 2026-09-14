"""Orchestrierung: Warehouse lesen + analysis/-Funktionen aufrufen (ohne UI)."""

from __future__ import annotations

import copy
import time
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from analysis.averages import (
    PollObservationPoint,
    load_poll_points_from_warehouse,
    party_averages_for_parliament,
    party_dispersion_for_parliament,
    party_trends_for_parliament,
)
from analysis.bundesrat import (
    check_government_config_age,
    choices_for_coalition,
    coalition_key,
    group_votes_by_coalition,
    informal_coalition_label,
    known_government_party_ids,
    load_bundesrat_config,
    parse_coalition_key,
    party_display_label,
    simulate_bundesrat,
)
from analysis.coalitions import (
    CoalitionRulesConfig,
    list_active_exclusion_rules,
    majority_threshold,
    possible_majorities,
)
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
    simulate_party_forecast,
    simulate_threshold_watch,
    simulate_uncertainty,
)
from data_pipeline.reference.election_results import (
    latest_election_for,
    load_election_results,
)
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
    "BIW": "de:biw",
    "BVB/FW": "de:bvb_freie_waehler",
    "Freie Sachsen": "de:freie_sachsen",
    "Volt": "de:volt",
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
_TTL_MISS = object()
_averages_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_coalitions_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_seats_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_last_election_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_uncertainty_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_trend_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_forecast_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_house_effects_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_leaderboard_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_europe_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}


def clear_payload_caches() -> None:
    """Leert Payload-TTL-Caches (Tests / nach Pipeline-Write)."""
    for cache in (
        _averages_cache,
        _coalitions_cache,
        _seats_cache,
        _last_election_cache,
        _uncertainty_cache,
        _trend_cache,
        _forecast_cache,
        _house_effects_cache,
        _leaderboard_cache,
        _europe_cache,
    ):
        cache.clear()


def _ttl_get(
    cache: dict[tuple[Any, ...], tuple[float, Any]],
    key: tuple[Any, ...],
) -> Any:
    """Cache-Treffer oder ``_TTL_MISS`` (auch gecachtes ``None`` ist ein Treffer)."""
    entry = cache.get(key)
    if entry is None:
        return _TTL_MISS
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        del cache[key]
        return _TTL_MISS
    return copy.deepcopy(value)


def _ttl_set(
    cache: dict[tuple[Any, ...], tuple[float, Any]],
    key: tuple[Any, ...],
    value: Any,
    *,
    ttl: float = _PAYLOAD_TTL_SECONDS,
) -> Any:
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
        out = [dict(zip(cols, r)) for r in rows]
    finally:
        con.close()

    cfg_by_id = {p.id: p for p in load_parliament_config().parliaments}
    for row in out:
        cfg = cfg_by_id.get(str(row["id"]))
        row["next_election_date"] = cfg.next_election_date if cfg else None
        row["next_election_note"] = cfg.next_election_note if cfg else None
    return out


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
    if cached is not _TTL_MISS:
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
    cache_key = (parliament_id, days)
    cached = _ttl_get(_trend_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

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
    return _ttl_set(
        _trend_cache,
        cache_key,
        {"parliament_id": parliament_id, "days": days, "parties": parties},
    )


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


def _party_house_variance(parliament_id: str) -> dict[str, float]:
    points = _load_points(parliament_id)
    return party_dispersion_for_parliament(points, parliament_id=parliament_id)


def _allocate_for_parliament(
    parliament_id: str,
    votes: dict[str, float],
    *,
    constituency_wins: Mapping[str, int] | None = None,
) -> tuple[dict[str, int], int]:
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
        seats = allocate_seats(
            parliament,
            votes,
            election_system=system,
            constituency_wins=constituency_wins,
        )
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
    cache_key = (parliament_id,)
    cached = _ttl_get(_seats_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

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
        return _ttl_set(
            _seats_cache,
            cache_key,
            {
                "parliament_id": parliament_id,
                "total_seats": 0,
                "seats": {},
                "seats_by_name": {},
                "reason": "no_averages",
            },
        )

    projection = _seat_projection_enabled(parliament_id)
    if projection is False:
        bundle = load_parliament_config()
        parliament = next(p for p in bundle.parliaments if p.id == parliament_id)
        system = next(
            s for s in bundle.election_systems if s.key == parliament.election_system_key
        )
        return _ttl_set(
            _seats_cache,
            cache_key,
            {
                "parliament_id": parliament_id,
                "total_seats": system.seats_total,
                "seats": {},
                "seats_by_name": {},
                "reason": "no_seat_projection",
            },
        )

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
    if parliament_id == "de_bundestag":
        _aggregate_cdu_csu_bundestag_display(seats, by_name)
    if not seats:
        return _ttl_set(
            _seats_cache,
            cache_key,
            {
                "parliament_id": parliament_id,
                "total_seats": total,
                "seats": {},
                "seats_by_name": {},
                "reason": "all_below_threshold",
            },
        )
    return _ttl_set(
        _seats_cache,
        cache_key,
        {
            "parliament_id": parliament_id,
            "total_seats": total,
            "seats": seats,
            "seats_by_name": by_name,
            "reason": None,
        },
    )


def _aggregate_cdu_csu_bundestag_display(
    seats: dict[str, int],
    seats_by_name: dict[str, int],
    vote_share_by_name: dict[str, float] | None = None,
) -> None:
    """
    Bundestag-Anzeige: CDU und CSU immer als CDU/CSU zusammenführen (in-place).

    Die Sitzzuteilung darf weiter getrennt rechnen; nur die Response-Maps
    werden aggregiert, damit nirgendwo getrennte CDU/CSU-Balken oder -Sitze
    erscheinen.
    """
    cdu = int(seats.pop("de:cdu", 0) or 0)
    csu = int(seats.pop("de:csu", 0) or 0)
    if cdu or csu:
        seats["de:cdu_csu"] = int(seats.get("de:cdu_csu", 0) or 0) + cdu + csu

    name_cdu = int(seats_by_name.pop("CDU", 0) or 0)
    name_csu = int(seats_by_name.pop("CSU", 0) or 0)
    if name_cdu or name_csu:
        seats_by_name["CDU/CSU"] = (
            int(seats_by_name.get("CDU/CSU", 0) or 0) + name_cdu + name_csu
        )

    if vote_share_by_name is not None:
        share_cdu = vote_share_by_name.pop("CDU", None)
        share_csu = vote_share_by_name.pop("CSU", None)
        if share_cdu is not None or share_csu is not None:
            if "CDU/CSU" not in vote_share_by_name:
                vote_share_by_name["CDU/CSU"] = float(share_cdu or 0.0) + float(
                    share_csu or 0.0
                )


def last_election_payload(parliament_id: str) -> dict[str, Any] | None:
    """
    Sitzzuteilung aus dem letzten amtlichen Wahlergebnis (election_results.yaml).

    Nutzt dieselbe Allokationspipeline wie ``seats_payload`` (inkl. Sonstige-Ausschluss).
    ``None``, wenn für das Parlament kein Wahlergebnis hinterlegt ist.
    """
    cache_key = (parliament_id,)
    cached = _ttl_get(_last_election_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

    election = latest_election_for(parliament_id)
    if election is None:
        return _ttl_set(_last_election_cache, cache_key, None)

    votes = dict(election.results)
    # Aggregat Union nur nutzen, wenn keine getrennten CDU/CSU-Anteile vorliegen
    if "de:cdu_csu" in votes and ("de:cdu" in votes or "de:csu" in votes):
        votes.pop("de:cdu_csu")

    names: dict[str, str] = {canon: short for short, canon in SHORT_TO_CANONICAL.items()}
    try:
        ensure_warehouse()
        con = connect_warehouse(read_only=not uses_motherduck())
        try:
            names = {**names, **_party_name_map(con)}
        finally:
            con.close()
    except Exception:
        pass

    _parliament, system = _election_system_for(parliament_id)
    constituency_wins: dict[str, int] | None = None
    if election.grundmandat_party_ids:
        gm = (system.grundmandat_seats if system else None) or 1
        constituency_wins = {pid: gm for pid in election.grundmandat_party_ids}

    seats, total = _allocate_for_parliament(
        parliament_id,
        votes,
        constituency_wins=constituency_wins,
    )
    seats = {
        pid: n
        for pid, n in seats.items()
        if n > 0 and not _is_residual_party(pid, names.get(pid))
    }
    by_name = {
        resolve_party_display_name(k, names): v for k, v in seats.items()
    }
    vote_share_by_name = {
        resolve_party_display_name(pid, names): float(share)
        for pid, share in votes.items()
        if not _is_residual_party(pid, names.get(pid))
    }
    # Umfragen melden oft „CDU/CSU“, Wahlergebnisse CDU und CSU getrennt.
    cdu_share = vote_share_by_name.get("CDU")
    csu_share = vote_share_by_name.get("CSU")
    if cdu_share is not None and csu_share is not None:
        raw_union = election.results.get("de:cdu_csu")
        vote_share_by_name["CDU/CSU"] = (
            float(raw_union) if raw_union is not None else float(cdu_share) + float(csu_share)
        )

    if parliament_id == "de_bundestag":
        _aggregate_cdu_csu_bundestag_display(seats, by_name, vote_share_by_name)

    return _ttl_set(
        _last_election_cache,
        cache_key,
        {
            "parliament_id": parliament_id,
            "election_date": election.election_date,
            "label": election.label,
            "source": election.source,
            "seats": seats,
            "seats_by_name": by_name,
            "vote_share_by_name": vote_share_by_name,
            "total_seats": sum(seats.values()) if seats else total,
        },
    )


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


def party_indispensability_from_seat_distributions(
    seat_distributions: Sequence[Mapping[str, int]],
    names: Mapping[str, str],
    *,
    total_seats: int,
    parliament_id: str | None = None,
    apply_exclusions: bool = True,
    disabled_rule_ids: Sequence[str] | None = None,
    max_parties: int = 4,
    rules_config: CoalitionRulesConfig | None = None,
) -> dict[str, Any]:
    """
    P(Partei ist in jeder möglichen Mehrheitskoalition dieser Ziehung).

    Ziehungen ohne jede mögliche Mehrheit (Deadlock) zählen nicht zum Nenner.
    """
    if total_seats <= 0 or not seat_distributions:
        return {
            "n_deadlock": 0,
            "n_simulations_considered": 0,
            "party_indispensability": [],
        }

    hits: dict[str, int] = {}
    n_deadlock = 0
    n_considered = 0
    disabled = list(disabled_rule_ids) if disabled_rule_ids else None

    for raw_seats in seat_distributions:
        canon = _seats_to_canonical(dict(raw_seats), dict(names))
        chamber = total_seats or sum(canon.values())
        if not canon or chamber <= 0:
            n_deadlock += 1
            continue
        result = possible_majorities(
            canon,
            chamber,
            max_parties=max_parties,
            parliament_id=parliament_id,
            apply_exclusions=apply_exclusions,
            disabled_rule_ids=disabled,
            rules_config=rules_config,
        )
        coalitions = result.coalitions
        if not coalitions:
            n_deadlock += 1
            continue
        n_considered += 1
        for pid, seats_n in canon.items():
            if seats_n <= 0:
                continue
            hits.setdefault(pid, 0)
            if all(pid in c.parties for c in coalitions):
                hits[pid] += 1

    rows = [
        {
            "party_id": pid,
            "probability": (hits.get(pid, 0) / n_considered) if n_considered else 0.0,
            "n_simulations_considered": n_considered,
        }
        for pid in sorted(hits.keys(), key=lambda p: (-hits.get(p, 0), p))
    ]
    return {
        "n_deadlock": n_deadlock,
        "n_simulations_considered": n_considered,
        "party_indispensability": rows,
    }


def _coalitions_from_seats(
    parliament_id: str,
    seats: dict[str, int],
    names: Mapping[str, str],
    *,
    total_seats: int,
    apply_exclusions: bool = True,
    max_parties: int = 4,
    disabled_rule_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Gemeinsamer Kern: kanonisierte Sitze → possible_majorities → Response-Dict."""
    empty = {
        "parliament_id": parliament_id,
        "total_seats": int(total_seats or 0),
        "majority_threshold": 0,
        "excluded_by_rules": 0,
        "coalitions": [],
    }
    if not seats or total_seats <= 0:
        return empty
    canon = _seats_to_canonical(dict(seats), dict(names))
    if not canon:
        return empty
    chamber = total_seats or sum(canon.values())
    result = possible_majorities(
        canon,
        chamber,
        max_parties=max_parties,
        parliament_id=parliament_id,
        apply_exclusions=apply_exclusions,
        disabled_rule_ids=list(disabled_rule_ids) if disabled_rule_ids else None,
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
    return {
        "parliament_id": parliament_id,
        "total_seats": result.total_seats,
        "majority_threshold": result.majority_threshold,
        "excluded_by_rules": result.excluded_by_rules,
        "coalitions": coalitions_out,
    }


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
    if cached is not _TTL_MISS:
        return cached

    seats_data = seats_payload(parliament_id)
    seats = seats_data["seats"]
    total = int(seats_data["total_seats"] or 0)
    if not seats or total <= 0:
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
    return _ttl_set(
        _coalitions_cache,
        cache_key,
        _coalitions_from_seats(
            parliament_id,
            seats,
            names,
            total_seats=total,
            apply_exclusions=apply_exclusions,
            max_parties=max_parties,
            disabled_rule_ids=disabled_rule_ids,
        ),
    )


def last_election_coalitions_payload(
    parliament_id: str,
    *,
    apply_exclusions: bool = True,
    max_parties: int = 4,
    disabled_rule_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    """
    Mögliche Mehrheiten auf Basis der Sitze des letzten amtlichen Wahlergebnisses.

    ``None``, wenn kein Wahlergebnis hinterlegt ist (analog ``last_election_payload``).
    """
    disabled = tuple(sorted(disabled_rule_ids or []))
    cache_key = ("last_election", parliament_id, apply_exclusions, max_parties, disabled)
    cached = _ttl_get(_coalitions_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

    election = last_election_payload(parliament_id)
    if election is None:
        return _ttl_set(_coalitions_cache, cache_key, None)

    seats = dict(election["seats"])
    total = int(election["total_seats"] or 0)
    names: dict[str, str] = {
        canon: short for short, canon in SHORT_TO_CANONICAL.items()
    }
    for pid in seats:
        names.setdefault(pid, resolve_party_display_name(pid, names))
    # Anzeigenamen aus seats_by_name rückwärts mergen
    for display, _n in (election.get("seats_by_name") or {}).items():
        canon = SHORT_TO_CANONICAL.get(display)
        if canon:
            names.setdefault(canon, display)

    payload = _coalitions_from_seats(
        parliament_id,
        seats,
        names,
        total_seats=total,
        apply_exclusions=apply_exclusions,
        max_parties=max_parties,
        disabled_rule_ids=disabled_rule_ids,
    )
    return _ttl_set(_coalitions_cache, cache_key, payload)


def coalition_rules_payload(parliament_id: str) -> dict[str, Any]:
    """Aktive Ausschlussregeln für ein Parlament (UI-Checkboxen, Paar-Gruppierung)."""
    rules = list_active_exclusion_rules(parliament_id)
    present = _present_parties_for_exclusion_ui(parliament_id)
    filtered: list[dict[str, Any]] = []
    for r in rules:
        if not r.id:
            continue
        parties = list(r.parties) if r.parties and len(r.parties) >= 2 else [r.party, *r.excludes]
        if len(parties) < 2:
            continue
        a, b = parties[0], parties[1]
        # party und mindestens eine excludes-Partei müssen in Sitzen/Umfragen sein
        if a not in present:
            continue
        if b not in present:
            continue
        filtered.append(
            {
                "id": r.id,
                "party": a,
                "excludes": [b],
                "parties": [a, b],
                "note": r.note,
            }
        )
    return {"parliament_id": parliament_id, "rules": filtered}


def _present_parties_for_exclusion_ui(parliament_id: str) -> set[str]:
    """Warehouse-IDs + kanonische IDs aus Sitzen und Umfrage-Mittelwerten."""
    present: set[str] = set()
    votes, names = _votes_from_averages(parliament_id)
    seats_data = seats_payload(parliament_id)
    seats = seats_data.get("seats") or {}

    def _add(pid: str) -> None:
        if not pid:
            return
        present.add(pid)
        label = resolve_party_display_name(pid, names)
        present.add(SHORT_TO_CANONICAL.get(label, pid))
        raw_name = names.get(pid)
        if raw_name:
            present.add(SHORT_TO_CANONICAL.get(raw_name, raw_name))

    for pid, share in votes.items():
        if float(share) > 0:
            _add(str(pid))
    for pid, n in seats.items():
        if int(n) > 0:
            _add(str(pid))
    return present


def _expanded_coalition_candidates(
    parliament_id: str,
    votes: dict[str, float],
    names: dict[str, str],
    *,
    total_seats: int,
    max_parties: int = 4,
    majority_band_points: float = 10.0,
    apply_exclusions: bool = True,
    disabled_rule_ids: list[str] | None = None,
) -> list[tuple[str, ...]]:
    """
    Zusätzliche Koalitions-Kandidaten (kanonische Partei-IDs) für die
    Unsicherheits-Simulation, über die deterministischen Top-8 aus
    coalitions_payload() hinaus.

    1. Nahe der Sperrklausel: eine NOMINALE Sitzverteilung ohne Hürde
       (threshold_percent=0, sonst identisches Zuteilungsverfahren) macht
       Parteien sichtbar, die im Punkt-Schätzwert 0 Sitze haben und daher
       nie in possible_majorities() auftauchen. Koalitionen, die eine
       solche Partei enthalten, werden hier zusätzlich ermittelt.
    2. Alleinregierung "falls sinnvoll": eine einzelne Partei, deren
       NOMINALE Sitzzahl mindestens (50 − majority_band_points) % der
       Kammer erreicht, wird zusätzlich als 1-Partei-Kandidat aufgenommen
       — auch wenn sie im Punkt-Schätzwert noch keine Mehrheit hat.
       Kleinere Parteien werden bewusst nicht einbezogen.

    Rein additiv zu den deterministischen Top-8; ob ein Kandidat am Ende
    in der Antwort auftaucht, entscheidet uncertainty_payload() über
    n_majority > 0.
    """
    if not votes or total_seats <= 0:
        return []

    parliament, system = _election_system_for(parliament_id)
    if parliament and system:
        nominal_system = system.model_copy(update={"threshold_percent": 0.0})
        nominal_seats = allocate_seats(
            parliament, votes, election_system=nominal_system
        )
    else:
        nominal_seats = sainte_lague_schepers(votes, total_seats, 0.0)

    canon_nominal = _seats_to_canonical(nominal_seats, names)
    if not canon_nominal:
        return []

    result = possible_majorities(
        canon_nominal,
        total_seats,
        max_parties=max_parties,
        parliament_id=parliament_id,
        apply_exclusions=apply_exclusions,
        disabled_rule_ids=disabled_rule_ids,
    )
    candidates: list[tuple[str, ...]] = [c.parties for c in result.coalitions]

    thr = majority_threshold(total_seats)
    seat_margin = max(0, round(majority_band_points / 100 * total_seats))
    have_singleton = {c[0] for c in candidates if len(c) == 1}
    for pid, seats_n in canon_nominal.items():
        if pid in have_singleton:
            continue
        if seats_n >= thr - seat_margin:
            candidates.append((pid,))

    candidates.sort(key=lambda c: -sum(canon_nominal.get(p, 0) for p in c))
    return candidates


def _incumbent_government_for_parliament(
    parliament_id: str,
) -> tuple[list[str], str] | None:
    """Amtierende Regierung aus bundesrat.yaml (Länder) bzw. bundesregierung (Bund)."""
    cfg = load_bundesrat_config()
    if parliament_id == "de_bundestag":
        fed = cfg.bundesregierung
        if fed is None or not fed.parties:
            return None
        return list(fed.parties), fed.label
    for state in cfg.states:
        if state.parliament_id == parliament_id:
            if not state.government_parties:
                return None
            return list(state.government_parties), state.government_label
    return None


def _normalize_gov_parties_for_simulation(
    parties: Sequence[str],
    canon_to_id: Mapping[str, str],
) -> list[str]:
    """CDU+CSU → de:cdu_csu, wenn die Simulation nur das Aggregat kennt."""
    ordered = [p for p in parties if p]
    use_union = (
        "de:cdu" in ordered
        and "de:csu" in ordered
        and "de:cdu_csu" in canon_to_id
        and "de:cdu" not in canon_to_id
        and "de:csu" not in canon_to_id
    )
    out: list[str] = []
    seen: set[str] = set()
    for p in ordered:
        repl = "de:cdu_csu" if use_union and p in {"de:cdu", "de:csu"} else p
        if repl in seen:
            continue
        seen.add(repl)
        out.append(repl)
    return out


def uncertainty_payload(
    parliament_id: str,
    *,
    n_simulations: int = 400,
    apply_exclusions: bool = True,
    disabled_rule_ids: list[str] | None = None,
) -> dict[str, Any]:
    disabled = tuple(sorted(disabled_rule_ids or []))
    cache_key = (parliament_id, n_simulations, apply_exclusions, disabled)
    cached = _ttl_get(_uncertainty_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

    empty_gov = {
        "current_government_parties": None,
        "current_government_label": None,
        "current_government_majority_probability": None,
    }

    votes, _names = _votes_from_averages(parliament_id)
    if not votes:
        return _ttl_set(
            _uncertainty_cache,
            cache_key,
            {
                "parliament_id": parliament_id,
                "n_simulations": 0,
                "n_deadlock": 0,
                "mean_seats": {},
                "coalition_probabilities": [],
                "party_indispensability": [],
                **empty_gov,
            },
        )
    parties = party_uncertainties_from_means(
        votes,
        sample_size=1000,
        house_variance=_party_house_variance(parliament_id),
    )
    seats, total = _allocate_for_parliament(parliament_id, votes)
    coal = coalitions_payload(
        parliament_id,
        apply_exclusions=apply_exclusions,
        disabled_rule_ids=disabled_rule_ids,
    )
    # Koalitionen sind kanonisch — Simulation nutzt warehouse IDs
    names = _names
    canon_to_id = {
        SHORT_TO_CANONICAL[name]: pid
        for pid, name in names.items()
        if name in SHORT_TO_CANONICAL
    }
    id_to_canon = {v: k for k, v in canon_to_id.items()}

    mapped: list[tuple[str, ...]] = []
    mapped_set: set[tuple[str, ...]] = set()
    deterministic_ids: set[tuple[str, ...]] = set()

    def _add_candidate(canon_parties: Sequence[str]) -> None:
        ids = tuple(sorted(canon_to_id[p] for p in canon_parties if p in canon_to_id))
        if not ids or len(ids) != len(canon_parties) or ids in mapped_set:
            return
        mapped_set.add(ids)
        mapped.append(ids)

    for c in coal["coalitions"][:8]:
        before = len(mapped)
        _add_candidate(c["parties"])
        if len(mapped) > before:
            deterministic_ids.add(mapped[-1])

    if total and total > 0:
        expanded = _expanded_coalition_candidates(
            parliament_id,
            votes,
            names,
            total_seats=total,
            apply_exclusions=apply_exclusions,
            disabled_rule_ids=disabled_rule_ids,
        )
        for combo in expanded:
            _add_candidate(combo)
        mapped = mapped[:20]

    # Amtierende Regierung immer als Kandidat (auch nach Truncation).
    gov_cfg = _incumbent_government_for_parliament(parliament_id)
    gov_canon: list[str] | None = None
    gov_label: str | None = None
    gov_wh_ids: tuple[str, ...] | None = None
    if gov_cfg is not None:
        raw_parties, gov_label = gov_cfg
        gov_canon = _normalize_gov_parties_for_simulation(raw_parties, canon_to_id)
        ids = tuple(sorted(canon_to_id[p] for p in gov_canon if p in canon_to_id))
        if ids and len(ids) == len(gov_canon):
            gov_wh_ids = ids
            if ids not in mapped_set:
                mapped_set.add(ids)
                mapped.append(ids)
            elif ids not in mapped:
                mapped.append(ids)
            deterministic_ids.add(ids)

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
    indis = party_indispensability_from_seat_distributions(
        result.seat_distributions,
        names,
        total_seats=total or 630,
        parliament_id=parliament_id,
        apply_exclusions=apply_exclusions,
        disabled_rule_ids=disabled_rule_ids,
        max_parties=4,
    )

    gov_prob: float | None = None
    if gov_wh_ids is not None:
        gov_prob = 0.0
        for c in result.coalition_probabilities:
            if c.parties == gov_wh_ids:
                gov_prob = float(c.majority_probability)
                break

    return _ttl_set(
        _uncertainty_cache,
        cache_key,
        {
            "parliament_id": parliament_id,
            "n_simulations": result.n_simulations,
            "n_deadlock": indis["n_deadlock"],
            "mean_seats": result.mean_seats,
            "coalition_probabilities": [
                {
                    "parties": [id_to_canon.get(p, p) for p in c.parties],
                    "majority_probability": c.majority_probability,
                    "n_majority": c.n_majority,
                    "n_simulations": c.n_simulations,
                }
                for c in result.coalition_probabilities
                if c.parties in deterministic_ids or c.n_majority > 0
            ],
            "party_indispensability": indis["party_indispensability"],
            "current_government_parties": gov_canon,
            "current_government_label": gov_label,
            "current_government_majority_probability": gov_prob,
        },
    )


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
    parties = party_uncertainties_from_means(
        votes,
        sample_size=1000,
        house_variance=_party_house_variance(parliament_id),
    )
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


def party_forecast_payload(
    parliament_id: str,
    *,
    n_simulations: int = 400,
) -> dict[str, Any]:
    """Monte-Carlo: P(stärkste Kraft) und P(über Sperrklausel) für alle Parteien."""
    cache_key = (parliament_id, n_simulations)
    cached = _ttl_get(_forecast_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

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

    _parliament, system = _election_system_for(parliament_id)
    threshold = float(system.threshold_percent) if system else 5.0
    minority = list(system.minority_exempt_party_ids) if system else []
    empty = {
        "parliament_id": parliament_id,
        "threshold_percent": threshold,
        "n_simulations": 0,
        "n_deadlock": 0,
        "parties": [],
    }
    if not votes:
        return _ttl_set(_forecast_cache, cache_key, empty)

    residual_ids = [
        pid
        for pid in votes
        if is_residual_party_id(pid) or _is_residual_party(pid, names.get(pid))
    ]
    filtered = {pid: share for pid, share in votes.items() if pid not in residual_ids}
    if not filtered:
        return _ttl_set(_forecast_cache, cache_key, empty)

    exempt = _threshold_exempt_ids(names, minority_exempt_party_ids=minority)
    parties = party_uncertainties_from_means(
        filtered,
        sample_size=1000,
        house_variance=_party_house_variance(parliament_id),
    )
    rows = simulate_party_forecast(
        parties,
        threshold_percent=threshold,
        exempt_party_ids=sorted(exempt),
        residual_party_ids=residual_ids,
        config=UncertaintyConfig(n_simulations=n_simulations, seed=42),
    )
    # Unverzichtbarkeit aus derselben Unsicherheits-Pipeline (Default-Ausschlüsse).
    unc = uncertainty_payload(parliament_id, n_simulations=n_simulations)
    indis_by_canon = {
        e["party_id"]: float(e["probability"])
        for e in unc.get("party_indispensability", [])
    }

    def _canon_for(pid: str) -> str:
        name = names.get(pid, pid)
        return SHORT_TO_CANONICAL.get(name, pid)

    return _ttl_set(
        _forecast_cache,
        cache_key,
        {
            "parliament_id": parliament_id,
            "threshold_percent": threshold,
            "n_simulations": n_simulations,
            "n_deadlock": unc.get("n_deadlock", 0),
            "parties": [
                {
                    "party_id": r.party_id,
                    "party_name": resolve_party_display_name(r.party_id, names),
                    "average_share": r.mean_share,
                    "threshold_percent": r.threshold_percent,
                    "probability_strongest": r.probability_strongest,
                    "probability_above_threshold": r.probability_above_threshold,
                    "probability_indispensable": indis_by_canon.get(
                        _canon_for(r.party_id), 0.0
                    ),
                }
                for r in rows
            ],
        },
    )


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
    cache_key = (parliament_id, window_days)
    cached = _ttl_get(_house_effects_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

    points = _load_points(parliament_id)
    if not points:
        return _ttl_set(
            _house_effects_cache,
            cache_key,
            {"parliament_id": parliament_id, "effects": [], "accuracy": []},
        )

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

    return _ttl_set(
        _house_effects_cache,
        cache_key,
        {
            "parliament_id": parliament_id,
            "effects": effect_rows,
            "accuracy": accuracy_rows,
        },
    )


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
    cache_key: tuple[Any, ...] = ()
    cached = _ttl_get(_leaderboard_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

    points = _load_points(None)
    if not points:
        return _ttl_set(_leaderboard_cache, cache_key, {"institutes": []})

    ensure_warehouse()
    con = connect_warehouse(read_only=not uses_motherduck())
    try:
        inames = _institute_name_map(con)
        pnames = _party_name_map(con)
    finally:
        con.close()

    tuples = _election_tuples_for_backtest(pnames)
    if not tuples:
        return _ttl_set(_leaderboard_cache, cache_key, {"institutes": []})

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
    return _ttl_set(_leaderboard_cache, cache_key, {"institutes": institutes})


def europe_overview_payload() -> dict[str, Any]:
    cache_key: tuple[Any, ...] = ()
    cached = _ttl_get(_europe_cache, cache_key)
    if cached is not _TTL_MISS:
        return cached

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

    return _ttl_set(
        _europe_cache,
        cache_key,
        {"as_of": date.today(), "countries": countries_out},
    )


BUNDESRAT_DISCLAIMER = (
    "Basierend auf den aktuell amtierenden Landesregierungen (Stand siehe Datum), "
    "nicht auf Umfragen-Projektionen der Landtage — die kannst du über die "
    "Dropdowns selbst durchspielen."
)

_ALLOWED_STANCES = frozenset({"default", "abstain", "enthaltung", "nein", "reject", "no"})


def government_payload() -> dict[str, Any]:
    """
    Amtierende Bundesregierung + Umfrage-Koalitions-Presets (Bundestag).

    Presets stammen aus ``uncertainty_payload("de_bundestag")``, gefiltert auf
    ``n_majority > 0`` (inkl. Alleinregierungen).
    """
    cfg = load_bundesrat_config()
    fed = cfg.bundesregierung
    bundesregierung = None
    if fed is not None:
        bundesregierung = {
            "stand": fed.stand,
            "parties": list(fed.parties),
            "label": fed.label,
        }

    known = sorted(
        known_government_party_ids(cfg),
        key=lambda pid: (party_display_label(pid).lower(), pid),
    )
    known_parties = [
        {"id": pid, "label": party_display_label(pid)} for pid in known
    ]

    presets: list[dict[str, Any]] = []
    try:
        unc = uncertainty_payload("de_bundestag")
        for row in unc.get("coalition_probabilities") or []:
            if int(row.get("n_majority") or 0) <= 0:
                continue
            parties = [
                p
                for p in (row.get("parties") or [])
                if p and not is_residual_party_id(str(p))
            ]
            if not parties:
                continue
            presets.append(
                {
                    "parties": parties,
                    "label": informal_coalition_label(parties),
                    "majority_probability": float(
                        row.get("majority_probability") or 0.0
                    ),
                    "n_majority": int(row.get("n_majority") or 0),
                    "n_simulations": int(row.get("n_simulations") or 0),
                }
            )
        presets.sort(key=lambda p: (-p["majority_probability"], p["label"]))
    except Exception:
        presets = []

    return {
        "bundesregierung": bundesregierung,
        "known_parties": known_parties,
        "poll_presets": presets,
    }


def data_freshness_payload() -> dict[str, Any]:
    """Offene Staging-Wahlergebnis-Entwürfe + Regierungs-Stand-Warnungen."""
    staging: list[dict[str, Any]] = []
    try:
        from data_pipeline.sources.election_watch import list_staging_drafts

        staging = list_staging_drafts()
    except Exception:
        staging = []

    gov_warnings: list[str] = []
    try:
        cfg = load_bundesrat_config()
        gov_warnings = check_government_config_age(cfg)
    except Exception:
        gov_warnings = []

    return {
        "staging_election_drafts": staging,
        "government_age_warnings": gov_warnings,
    }


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
