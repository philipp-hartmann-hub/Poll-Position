"""Wikipedia Opinion-Polling Adapter (paneuropäisch, CC BY-SA).

Politico Poll of Polls bietet keine offene API; Europe Elects ist kostenpflichtig /
nicht-kommerziell lizenziert. Wikipedia-Tabellen sind die freie Alternative.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import requests
import yaml

from data_pipeline.schema import Survey
from data_pipeline.sources.base import PollSourceAdapter
from data_pipeline.sources.wikipedia_parsers import IntermediatePoll, PARSERS
from data_pipeline.warehouse import (
    insert_surveys_incremental,
    upsert_institutes,
    upsert_parties,
)

log = logging.getLogger(__name__)

SOURCE = "wikipedia"
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data_pipeline" / "config" / "wikipedia_pages.yaml"
RAW_DIR = ROOT / "data" / "raw" / "wikipedia_polls"
API_ENDPOINT = "https://en.wikipedia.org/w/api.php"

CC_BY_SA_ATTRIBUTION = (
    "Quelle: [Wikipedia-Mitwirkende](https://www.wikipedia.org/), "
    "[CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/)"
)


@dataclass
class WikiPageConfig:
    id: str
    country: str
    parliament_id: str
    level: str
    title: str
    url: str
    parser: str
    enabled: bool = True


@dataclass
class WikipediaFetchMeta:
    page_id: str
    title: str
    revision_id: int
    permalink: str
    fetched_at: datetime
    html: str


@dataclass
class WikipediaLoadResult:
    surveys: list[Survey]
    bronze_paths: list[Path]
    surveys_new: int
    results_new: int
    notes: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_page_configs(path: Path | None = None) -> list[WikiPageConfig]:
    raw = yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8"))
    pages = []
    for entry in raw.get("pages", []):
        pages.append(WikiPageConfig(**entry))
    return [p for p in pages if p.enabled]


def _session_with_ua(user_agent: str, session: requests.Session | None = None) -> requests.Session:
    client = session or requests.Session()
    client.headers.update({"User-Agent": user_agent})
    return client


def load_user_agent(path: Path | None = None) -> str:
    raw = yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8"))
    return raw.get(
        "user_agent",
        "PollPosition/0.1 (https://github.com/philipp-hartmann-hub/Poll-Position)",
    )


def fetch_wikipedia_revision(
    title: str,
    *,
    session: requests.Session | None = None,
    user_agent: str | None = None,
) -> WikipediaFetchMeta:
    """Holt HTML + Revision-ID über die MediaWiki-API (reproduzierbarer Permalink)."""
    client = _session_with_ua(user_agent or load_user_agent(), session)
    response = client.get(
        API_ENDPOINT,
        params={
            "action": "parse",
            "page": title,
            "prop": "text|revid|displaytitle",
            "format": "json",
            "formatversion": "2",
            "redirects": 1,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"Wikipedia API error for {title!r}: {payload['error']}")
    parse = payload["parse"]
    revid = int(parse["revid"])
    resolved_title = parse.get("title") or title
    permalink = f"https://en.wikipedia.org/w/index.php?title={resolved_title.replace(' ', '_')}&oldid={revid}"
    return WikipediaFetchMeta(
        page_id=str(parse.get("pageid", "")),
        title=resolved_title,
        revision_id=revid,
        permalink=permalink,
        fetched_at=_utc_now(),
        html=parse["text"],
    )


def write_bronze_wikipedia(meta: WikipediaFetchMeta, page: WikiPageConfig, *, as_of: date | None = None) -> Path:
    as_of = as_of or date.today()
    out_dir = RAW_DIR / page.id
    out_dir.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(
        {
            "fetched_at": [meta.fetched_at],
            "fetch_date": [as_of],
            "page_id": [page.id],
            "title": [meta.title],
            "revision_id": [meta.revision_id],
            "permalink": [meta.permalink],
            "url": [page.url],
            "source": [SOURCE],
            "attribution": [CC_BY_SA_ATTRIBUTION],
            "raw_html": [meta.html],
        }
    )
    path = out_dir / f"{as_of.isoformat()}_r{meta.revision_id}.parquet"
    frame.write_parquet(path)
    return path


def _slug(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    ascii_ish = "".join(c for c in normalized if not unicodedata.combining(c))
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_ish.strip().lower()).strip("_")
    return slug or "unknown"


def _party_id(country: str, party_label: str) -> str:
    if party_label.lower() in {"others", "other", "oth.", "oth"}:
        return f"{country.lower()}:others"
    return f"{country.lower()}:{_slug(party_label)}"


def _survey_id(page_id: str, poll: IntermediatePoll, revision_id: int) -> str:
    key = "|".join(
        [
            page_id,
            poll.institute,
            str(poll.field_date_from),
            str(poll.field_date_to),
            str(sorted(poll.results.items())),
            str(revision_id),
        ]
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"wikipedia:survey:{page_id}:{digest}"


def intermediate_to_surveys(
    polls: list[IntermediatePoll],
    *,
    page: WikiPageConfig,
    revision_id: int,
    permalink: str,
) -> list[Survey]:
    surveys: list[Survey] = []
    for poll in polls:
        results = {
            _party_id(page.country, label): share for label, share in poll.results.items()
        }
        if not results:
            continue
        pub = poll.field_date_to or poll.field_date_from or date.today()
        surveys.append(
            Survey(
                id=_survey_id(page.id, poll, revision_id),
                parliament_id=page.parliament_id,
                institute_id=f"wikipedia:institute:{_slug(poll.institute)}",
                tasker=poll.tasker,
                method=poll.method,
                field_date_from=poll.field_date_from,
                field_date_to=poll.field_date_to,
                publication_date=pub,
                sample_size=poll.sample_size,
                source=SOURCE,
                source_url=permalink,
                results=results,
            )
        )
    return surveys


def parse_page_html(html: str, page: WikiPageConfig) -> list[IntermediatePoll]:
    parser = PARSERS.get(page.parser)
    if parser is None:
        raise KeyError(f"Kein Parser für Key {page.parser!r} (Seite {page.id})")
    return parser(html)


def surveys_to_silver_rows(
    surveys: list[Survey],
    *,
    country: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    now = _utc_now()
    institutes: dict[str, dict[str, Any]] = {}
    parties: dict[str, dict[str, Any]] = {}
    survey_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    for survey in surveys:
        institutes[survey.institute_id] = {
            "id": survey.institute_id,
            "source": SOURCE,
            "source_id": survey.institute_id.split(":")[-1],
            "name": survey.institute_id.split(":")[-1].replace("_", " "),
            "country": country,
            "house_effect_score": None,
            "updated_at": now,
        }
        for party_id, share in survey.results.items():
            short = party_id.split(":")[-1]
            parties[party_id] = {
                "id": party_id,
                "source": SOURCE,
                "source_id": short,
                "country": country,
                "short_name": short,
                "full_name": short,
                "european_party_family": None,
                "updated_at": now,
            }
            result_rows.append(
                {"survey_id": survey.id, "party_id": party_id, "share": share}
            )
        survey_rows.append(
            {
                "id": survey.id,
                "source": SOURCE,
                "source_id": survey.id,
                "parliament_id": survey.parliament_id,
                "institute_id": survey.institute_id,
                "tasker": survey.tasker,
                "method": survey.method,
                "field_date_from": survey.field_date_from,
                "field_date_to": survey.field_date_to,
                "publication_date": survey.publication_date,
                "sample_size": survey.sample_size,
                "source_url": survey.source_url,
                "updated_at": now,
            }
        )
    return list(institutes.values()), list(parties.values()), survey_rows, result_rows


class WikipediaPollsAdapter(PollSourceAdapter):
    source_id = SOURCE

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        config_path: Path | None = None,
        pages: list[WikiPageConfig] | None = None,
    ) -> None:
        self._session = session
        self._config_path = config_path
        self._pages = pages
        self._user_agent = load_user_agent(config_path)

    def _page_list(self) -> list[WikiPageConfig]:
        if self._pages is not None:
            return self._pages
        return load_page_configs(self._config_path)

    def fetch(self) -> list[Survey]:
        surveys: list[Survey] = []
        for page in self._page_list():
            try:
                meta = fetch_wikipedia_revision(
                    page.title,
                    session=self._session,
                    user_agent=self._user_agent,
                )
                polls = parse_page_html(meta.html, page)
                page_surveys = intermediate_to_surveys(
                    polls,
                    page=page,
                    revision_id=meta.revision_id,
                    permalink=meta.permalink,
                )
                log.info(
                    "Wikipedia %s: revid=%s polls=%d surveys=%d",
                    page.id,
                    meta.revision_id,
                    len(polls),
                    len(page_surveys),
                )
                surveys.extend(page_surveys)
            except Exception as exc:  # noqa: BLE001 — eine Seite darf den Rest nicht stoppen
                log.warning("Wikipedia %s fehlgeschlagen: %s", page.id, exc)
        return surveys

    def run(self, *, as_of: date | None = None) -> WikipediaLoadResult:
        """Bronze speichern, Survey-Liste erzeugen, Silver incremental aktualisieren."""
        as_of = as_of or date.today()
        all_surveys: list[Survey] = []
        bronze_paths: list[Path] = []
        total_new_s = 0
        total_new_r = 0

        for page in self._page_list():
            try:
                meta = fetch_wikipedia_revision(
                    page.title,
                    session=self._session,
                    user_agent=self._user_agent,
                )
                bronze_paths.append(write_bronze_wikipedia(meta, page, as_of=as_of))
                polls = parse_page_html(meta.html, page)
                surveys = intermediate_to_surveys(
                    polls,
                    page=page,
                    revision_id=meta.revision_id,
                    permalink=meta.permalink,
                )
                institutes, parties, survey_rows, result_rows = surveys_to_silver_rows(
                    surveys, country=page.country
                )
                upsert_institutes(institutes)
                upsert_parties(parties)
                n_s, n_r = insert_surveys_incremental(
                    survey_rows, result_rows, source=SOURCE
                )
                total_new_s += n_s
                total_new_r += n_r
                all_surveys.extend(surveys)
                log.info(
                    "Wikipedia %s: bronze=%s surveys=%d new=%d permalink=%s",
                    page.id,
                    bronze_paths[-1].name,
                    len(surveys),
                    n_s,
                    meta.permalink,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Wikipedia %s fehlgeschlagen: %s", page.id, exc)

        return WikipediaLoadResult(
            surveys=all_surveys,
            bronze_paths=bronze_paths,
            surveys_new=total_new_s,
            results_new=total_new_r,
            notes=json.dumps({"attribution": CC_BY_SA_ATTRIBUTION}, ensure_ascii=False),
        )
