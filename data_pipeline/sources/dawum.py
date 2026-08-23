"""Dawum-API Adapter: Bronze (Roh-JSON) → Silver (DuckDB)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import requests

from data_pipeline.schema import (
    SONSTIGE_PARTY_ID,
    LevelKind,
    Party,
    Pollster,
    Survey,
    load_parliament_config,
)
from data_pipeline.sources.base import PollSourceAdapter
from data_pipeline.warehouse import (
    insert_surveys_incremental,
    upsert_institutes,
    upsert_parliaments,
    upsert_parties,
)

log = logging.getLogger(__name__)

API_URL = "https://api.dawum.de/"
LAST_UPDATE_URL = "https://api.dawum.de/last_update.txt"
SOURCE = "dawum"
COUNTRY = "DE"

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "dawum"
LAST_UPDATE_FILE = RAW_DIR / "last_update.txt"

# Dawum Parliament_ID → internes Parlament (de_parliaments.yaml)
DAWUM_TO_PARLIAMENT: dict[str, str] = {
    "0": "de_bundestag",
    "1": "de_bw_landtag",
    "2": "de_by_landtag",
    "3": "de_be_abgeordnetenhaus",
    "4": "de_bb_landtag",
    "5": "de_hb_buergerschaft",
    "6": "de_hh_buergerschaft",
    "7": "de_he_landtag",
    "8": "de_mv_landtag",
    "9": "de_ni_landtag",
    "10": "de_nw_landtag",
    "11": "de_rp_landtag",
    "12": "de_sl_landtag",
    "13": "de_sn_landtag",
    "14": "de_st_landtag",
    "15": "de_sh_landtag",
    "16": "de_th_landtag",
}

# Dawum Parliament_ID → ISO 3166-2 (nur Landtage)
DAWUM_STATE_CODES: dict[str, str] = {
    "1": "DE-BW",
    "2": "DE-BY",
    "3": "DE-BE",
    "4": "DE-BB",
    "5": "DE-HB",
    "6": "DE-HH",
    "7": "DE-HE",
    "8": "DE-MV",
    "9": "DE-NI",
    "10": "DE-NW",
    "11": "DE-RP",
    "12": "DE-SL",
    "13": "DE-SN",
    "14": "DE-ST",
    "15": "DE-SH",
    "16": "DE-TH",
}

ODBL_ATTRIBUTION = (
    "Umfragedaten: [dawum.de](https://dawum.de/) "
    "([Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/))"
)


@dataclass
class DawumLoadResult:
    fetched: bool
    last_update: str | None
    bronze_path: Path | None
    parliaments: int
    parties: int
    institutes: int
    surveys_new: int
    results_new: int
    notes: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _http_get(url: str, *, session: requests.Session | None = None) -> str:
    client = session or requests
    response = client.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def fetch_last_update(session: requests.Session | None = None) -> str:
    return _http_get(LAST_UPDATE_URL, session=session).strip()


def fetch_payload(session: requests.Session | None = None) -> dict[str, Any]:
    text = _http_get(API_URL, session=session)
    return json.loads(text)


def read_local_last_update() -> str | None:
    if LAST_UPDATE_FILE.exists():
        return LAST_UPDATE_FILE.read_text(encoding="utf-8").strip()
    return None


def write_local_last_update(value: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LAST_UPDATE_FILE.write_text(value, encoding="utf-8")


def write_bronze_raw(payload: dict[str, Any], *, as_of: date | None = None) -> Path:
    """Speichert die Roh-JSON-Antwort unverändert als Parquet (Bronze)."""
    as_of = as_of or date.today()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    last_update = payload.get("Database", {}).get("Last_Update")
    frame = pl.DataFrame(
        {
            "fetched_at": [_utc_now()],
            "fetch_date": [as_of],
            "last_update": [last_update],
            "source": [SOURCE],
            "raw_json": [json.dumps(payload, ensure_ascii=False)],
        }
    )
    path = RAW_DIR / f"{as_of.isoformat()}.parquet"
    frame.write_parquet(path)
    return path


def _parliament_level(parliament_id: str) -> tuple[LevelKind, str | None]:
    if parliament_id == "0":
        return LevelKind.NATIONAL, None
    if parliament_id == "17":
        return LevelKind.EU_PARLIAMENT, None
    return LevelKind.STATE, DAWUM_STATE_CODES.get(parliament_id)


def _canonical_party_id(dawum_party_id: str) -> str:
    if dawum_party_id == "0":
        return SONSTIGE_PARTY_ID
    return f"dawum:party:{dawum_party_id}"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _parse_int(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _load_parliament_meta() -> dict[str, dict[str, Any]]:
    try:
        bundle = load_parliament_config()
        return {p.id: p.model_dump() for p in bundle.parliaments}
    except Exception as exc:  # noqa: BLE001 — Konfig optional beim Parsen
        log.warning("Parlamentskonfiguration nicht geladen: %s", exc)
        return {}


def parse_dawum_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Parst Dawum-JSON in interne Entitätslisten."""
    parliament_meta = _load_parliament_meta()
    now = _utc_now()

    parliament_rows: list[dict[str, Any]] = []
    for pid, entry in payload.get("Parliaments", {}).items():
        level_kind, state_code = _parliament_level(pid)
        mapped_id = DAWUM_TO_PARLIAMENT.get(pid)
        meta = parliament_meta.get(mapped_id, {}) if mapped_id else {}
        level = meta.get("level", {})
        parliament_rows.append(
            {
                "id": mapped_id or f"dawum:parliament:{pid}",
                "source": SOURCE,
                "source_id": pid,
                "country": COUNTRY,
                "level_kind": level.get("kind", level_kind.value),
                "state_code": level.get("state_code", state_code),
                "name": entry["Name"],
                "shortcut": entry.get("Shortcut"),
                "election_label": entry.get("Election"),
                "seats_total": meta.get("seats_total"),
                "election_system_key": meta.get("election_system_key"),
                "updated_at": now,
            }
        )

    party_rows: list[dict[str, Any]] = []
    parties_parsed: list[Party] = []
    for pid, entry in payload.get("Parties", {}).items():
        canonical_id = _canonical_party_id(pid)
        party_rows.append(
            {
                "id": canonical_id,
                "source": SOURCE,
                "source_id": pid,
                "country": COUNTRY,
                "short_name": entry["Shortcut"],
                "full_name": entry["Name"],
                "european_party_family": None,
                "updated_at": now,
            }
        )
        parties_parsed.append(
            Party(
                id=canonical_id,
                country=COUNTRY,
                short_name=entry["Shortcut"],
                full_name=entry["Name"],
            )
        )

    institute_rows: list[dict[str, Any]] = []
    institutes_parsed: list[Pollster] = []
    for iid, entry in payload.get("Institutes", {}).items():
        canonical_id = f"dawum:institute:{iid}"
        institute_rows.append(
            {
                "id": canonical_id,
                "source": SOURCE,
                "source_id": iid,
                "name": entry["Name"],
                "country": COUNTRY,
                "house_effect_score": None,
                "updated_at": now,
            }
        )
        institutes_parsed.append(
            Pollster(id=canonical_id, name=entry["Name"], country=COUNTRY)
        )

    taskers = payload.get("Taskers", {})
    methods = payload.get("Methods", {})

    survey_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    surveys_parsed: list[Survey] = []

    for sid, entry in payload.get("Surveys", {}).items():
        parliament_id_raw = entry["Parliament_ID"]
        mapped_parliament = DAWUM_TO_PARLIAMENT.get(
            parliament_id_raw, f"dawum:parliament:{parliament_id_raw}"
        )
        institute_id = f"dawum:institute:{entry['Institute_ID']}"
        tasker = taskers.get(entry.get("Tasker_ID"), {}).get("Name")
        method = methods.get(entry.get("Method_ID"), {}).get("Name")
        period = entry.get("Survey_Period") or {}

        results: dict[str, float] = {}
        for party_id, share in entry.get("Results", {}).items():
            results[_canonical_party_id(str(party_id))] = float(share)

        canonical_survey_id = f"dawum:survey:{sid}"
        survey_rows.append(
            {
                "id": canonical_survey_id,
                "source": SOURCE,
                "source_id": sid,
                "parliament_id": mapped_parliament,
                "institute_id": institute_id,
                "tasker": tasker,
                "method": method,
                "field_date_from": _parse_date(period.get("Date_Start")),
                "field_date_to": _parse_date(period.get("Date_End")),
                "publication_date": _parse_date(entry["Date"]),
                "sample_size": _parse_int(entry.get("Surveyed_Persons")),
                "source_url": "https://dawum.de/",
                "updated_at": now,
            }
        )
        for party_id, share in results.items():
            result_rows.append(
                {"survey_id": canonical_survey_id, "party_id": party_id, "share": share}
            )
        surveys_parsed.append(
            Survey(
                id=canonical_survey_id,
                parliament_id=mapped_parliament,
                institute_id=institute_id,
                tasker=tasker,
                method=method,
                field_date_from=_parse_date(period.get("Date_Start")),
                field_date_to=_parse_date(period.get("Date_End")),
                publication_date=_parse_date(entry["Date"]),  # type: ignore[arg-type]
                sample_size=_parse_int(entry.get("Surveyed_Persons")),
                source=SOURCE,
                source_url="https://dawum.de/",
                results=results,
            )
        )

    return {
        "parliament_rows": parliament_rows,
        "party_rows": party_rows,
        "institute_rows": institute_rows,
        "survey_rows": survey_rows,
        "result_rows": result_rows,
        "parties": parties_parsed,
        "institutes": institutes_parsed,
        "surveys": surveys_parsed,
        "last_update": payload.get("Database", {}).get("Last_Update"),
    }


def load_silver(parsed: dict[str, Any]) -> tuple[int, int, int, int, int]:
    """Schreibt/aktualisiert Silver-Tabellen; Surveys incremental."""
    p = upsert_parliaments(parsed["parliament_rows"])
    pt = upsert_parties(parsed["party_rows"])
    i = upsert_institutes(parsed["institute_rows"])
    s, r = insert_surveys_incremental(
        parsed["survey_rows"], parsed["result_rows"], source=SOURCE
    )
    return p, pt, i, s, r


class DawumAdapter(PollSourceAdapter):
    source_id = SOURCE

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session

    def needs_fetch(self, remote_last_update: str | None = None) -> bool:
        remote = remote_last_update or fetch_last_update(session=self._session)
        local = read_local_last_update()
        return remote != local

    def run(self, *, force: bool = False, as_of: date | None = None) -> DawumLoadResult:
        as_of = as_of or date.today()
        remote_last_update = fetch_last_update(session=self._session)
        local_last_update = read_local_last_update()
        fetched = False
        bronze_path: Path | None = None
        payload: dict[str, Any]

        if force or remote_last_update != local_last_update:
            log.info("Dawum: neue Daten (%s → %s)", local_last_update, remote_last_update)
            payload = fetch_payload(session=self._session)
            bronze_path = write_bronze_raw(payload, as_of=as_of)
            write_local_last_update(remote_last_update)
            fetched = True
        else:
            log.info("Dawum: last_update unverändert (%s)", remote_last_update)
            latest = sorted(RAW_DIR.glob("*.parquet"), reverse=True)
            latest = [p for p in latest if p.name != "last_update.txt"]
            if latest:
                row = pl.read_parquet(latest[0]).row(0, named=True)
                payload = json.loads(row["raw_json"])
            else:
                payload = fetch_payload(session=self._session)
                bronze_path = write_bronze_raw(payload, as_of=as_of)
                write_local_last_update(remote_last_update)
                fetched = True

        parsed = parse_dawum_payload(payload)
        p, pt, i, s, r = load_silver(parsed)
        self._last_parsed = parsed

        return DawumLoadResult(
            fetched=fetched,
            last_update=remote_last_update,
            bronze_path=bronze_path,
            parliaments=p,
            parties=pt,
            institutes=i,
            surveys_new=s,
            results_new=r,
            notes=None if s else "Keine neuen Surveys",
        )

    def fetch(self) -> list[Survey]:
        """Lädt bei Bedarf und gibt kanonische Survey-Objekte zurück."""
        if not hasattr(self, "_last_parsed"):
            self.run()
        return list(self._last_parsed["surveys"])
