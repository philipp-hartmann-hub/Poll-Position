"""Erkennt fällige Wahlen und schreibt Wikipedia-Ergebnis-Entwürfe nach Staging.

Überschreibt nie ``election_results.yaml`` — Übernahme bleibt manuell.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import requests
import yaml
from pydantic import BaseModel, Field

from data_pipeline.reference.election_results import (
    load_election_results,
)
from data_pipeline.schema import Parliament, load_parliament_config
from data_pipeline.sources.wikipedia_parsers import parse_election_result_table

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
STAGING_DIR = ROOT / "data" / "staging" / "election_results"
DE_WIKI_API = "https://de.wikipedia.org/w/api.php"

# Wikipedia-Lemma-Templates — Titel recherchiert (de.wikipedia.org), Jahr aus election_date.
# Berlin: „Wahl zum Abgeordnetenhaus von Berlin {year}“
# Saarland: „Landtagswahl im Saarland {year}“
WIKIPEDIA_LEMMA_TEMPLATES: dict[str, str] = {
    "de_bundestag": "Bundestagswahl {year}",
    "de_bw_landtag": "Landtagswahl in Baden-Württemberg {year}",
    "de_by_landtag": "Landtagswahl in Bayern {year}",
    "de_be_abgeordnetenhaus": "Wahl zum Abgeordnetenhaus von Berlin {year}",
    "de_bb_landtag": "Landtagswahl in Brandenburg {year}",
    "de_hb_buergerschaft": "Bürgerschaftswahl in Bremen {year}",
    "de_hh_buergerschaft": "Bürgerschaftswahl in Hamburg {year}",
    "de_he_landtag": "Landtagswahl in Hessen {year}",
    "de_mv_landtag": "Landtagswahl in Mecklenburg-Vorpommern {year}",
    "de_ni_landtag": "Landtagswahl in Niedersachsen {year}",
    "de_nw_landtag": "Landtagswahl in Nordrhein-Westfalen {year}",
    "de_rp_landtag": "Landtagswahl in Rheinland-Pfalz {year}",
    "de_sl_landtag": "Landtagswahl im Saarland {year}",
    "de_sn_landtag": "Landtagswahl in Sachsen {year}",
    "de_st_landtag": "Landtagswahl in Sachsen-Anhalt {year}",
    "de_sh_landtag": "Landtagswahl in Schleswig-Holstein {year}",
    "de_th_landtag": "Landtagswahl in Thüringen {year}",
}

# Anzeige-Labels → kanonische Party-IDs (DE)
_PARTY_LABEL_TO_ID: dict[str, str] = {
    "cdu": "de:cdu",
    "csu": "de:csu",
    "cdu/csu": "de:cdu_csu",
    "union": "de:cdu_csu",
    "spd": "de:spd",
    "afd": "de:afd",
    "grüne": "de:gruene",
    "gruene": "de:gruene",
    "grün": "de:gruene",
    "bündnis 90/die grünen": "de:gruene",
    "buendnis 90/die gruenen": "de:gruene",
    "die grünen": "de:gruene",
    "fdp": "de:fdp",
    "linke": "de:linke",
    "die linke": "de:linke",
    "bsw": "de:bsw",
    "freie wähler": "de:fw",
    "fw": "de:fw",
    "ssw": "de:ssw",
    "volt": "de:volt",
    "sonst.": "de:sonstige",
    "sonstige": "de:sonstige",
    "others": "de:sonstige",
    "oth.": "de:sonstige",
    "freie sachsen": "de:freie_sachsen",
}


class ElectionResultDraft(BaseModel):
    parliament_id: str
    election_date: date
    label: str
    source_url: str
    results: dict[str, float] = Field(..., min_length=1)
    grundmandat_candidates: list[str] = Field(
        default_factory=list,
        description="Parteien mit Verdacht auf Grundmandat (manuell prüfen → grundmandat_party_ids)",
    )


def wikipedia_lemma_for(parliament_id: str, election_date: date) -> str | None:
    template = WIKIPEDIA_LEMMA_TEMPLATES.get(parliament_id)
    if not template:
        return None
    return template.format(year=election_date.year)


def pending_elections(*, as_of: date | None = None) -> list[Parliament]:
    """
    Parlamente mit ``next_election_date <= as_of`` ohne ElectionResult gleichen Datums.
    """
    as_of = as_of or date.today()
    bundle = load_parliament_config()
    results = load_election_results()
    known: set[tuple[str, date]] = {
        (e.parliament_id, e.election_date) for e in results.elections
    }
    pending: list[Parliament] = []
    for parl in bundle.parliaments:
        if parl.country != "DE":
            continue
        ned = parl.next_election_date
        if ned is None or ned > as_of:
            continue
        if (parl.id, ned) in known:
            continue
        pending.append(parl)
    pending.sort(key=lambda p: (p.next_election_date or date.max, p.id))
    return pending


def _normalize_party_label(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label).strip().lower()
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    # Fußnoten / Klammern abschneiden
    cleaned = re.sub(r"\s*\[\d+\]\s*", "", cleaned)
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()
    return cleaned


def map_party_label_to_id(label: str) -> str | None:
    key = _normalize_party_label(label)
    if key in _PARTY_LABEL_TO_ID:
        return _PARTY_LABEL_TO_ID[key]
    # Präfix-Match für lange Wikipedia-Titel
    for alias, pid in _PARTY_LABEL_TO_ID.items():
        if key.startswith(alias) or alias in key:
            return pid
    return None


def canonicalize_results(raw: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for label, pct in raw.items():
        pid = map_party_label_to_id(label)
        if pid is None:
            continue
        out[pid] = float(pct)
    return out


def fetch_de_wikipedia_html(title: str, *, session: requests.Session | None = None) -> tuple[str, str]:
    """Holt Parse-HTML von de.wikipedia.org. Returns (html, resolved_title)."""
    client = session or requests.Session()
    # MediaWiki verlangt einen beschreibenden User-Agent (403 sonst).
    if "User-Agent" not in client.headers:
        client.headers["User-Agent"] = (
            "PollPositionBot/0.1 "
            "(https://github.com/philipp-hartmann-hub/Poll-Position; "
            "election-result-watch; python-requests)"
        )
    response = client.get(
        DE_WIKI_API,
        params={
            "action": "parse",
            "page": title,
            "prop": "text|displaytitle",
            "format": "json",
            "formatversion": "2",
            "redirects": 1,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"de.wikipedia API error for {title!r}: {payload['error']}")
    parse = payload["parse"]
    return parse["text"], (parse.get("title") or title)


def fetch_wikipedia_election_result(
    parliament_id: str,
    election_date: date,
    *,
    session: requests.Session | None = None,
    html: str | None = None,
) -> ElectionResultDraft | None:
    """
    Holt Wikipedia-Seite und parst die Ergebnistabelle.

    ``None``, wenn Lemma fehlt oder noch keine auswertbare Tabelle vorliegt
    (normal an Wahlabenden) — kein Fehler.
    """
    lemma = wikipedia_lemma_for(parliament_id, election_date)
    if lemma is None:
        log.info("Kein Wikipedia-Lemma für %s", parliament_id)
        return None

    source_url = f"https://de.wikipedia.org/wiki/{lemma.replace(' ', '_')}"
    if html is None:
        try:
            html, resolved = fetch_de_wikipedia_html(lemma, session=session)
            source_url = f"https://de.wikipedia.org/wiki/{resolved.replace(' ', '_')}"
        except Exception as exc:
            log.warning("Wikipedia-Fetch fehlgeschlagen (%s): %s", lemma, exc)
            return None

    raw = parse_election_result_table(html)
    if not raw:
        return None
    results = canonicalize_results(raw)
    if len(results) < 3:
        return None

    label = lemma
    return ElectionResultDraft(
        parliament_id=parliament_id,
        election_date=election_date,
        label=label,
        source_url=source_url,
        results=results,
        grundmandat_candidates=[],
    )


def draft_path(parliament_id: str, election_date: date) -> Path:
    return STAGING_DIR / f"{parliament_id}_{election_date.isoformat()}.yaml"


def write_draft(draft: ElectionResultDraft, path: Path | None = None) -> Path:
    """Schreibt Entwurf nach ``data/staging/election_results/`` — nie in die Referenz-YAML."""
    out = path or draft_path(draft.parliament_id, draft.election_date)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = draft.model_dump(mode="json")
    out.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return out


def list_staging_drafts(staging_dir: Path | None = None) -> list[dict[str, Any]]:
    """Liest vorhandene Staging-YAML-Dateien (für API / Banner)."""
    base = staging_dir or STAGING_DIR
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "parliament_id": raw.get("parliament_id"),
                    "election_date": raw.get("election_date"),
                    "label": raw.get("label"),
                    "source_url": raw.get("source_url"),
                    "grundmandat_candidates": raw.get("grundmandat_candidates") or [],
                }
            )
        except Exception as exc:
            log.warning("Staging-Datei unlesbar (%s): %s", path, exc)
    return rows


def maybe_open_review_issue(draft: ElectionResultDraft, path: Path) -> None:
    """
    Legt bei vorhandenem GH_TOKEN/GITHUB_TOKEN ein GitHub-Issue an (Dedup über Titel).
    Sonst nur Log.
    """
    title = f"Wahlergebnis verfügbar: {draft.label}"
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    repo = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    body = (
        f"Automatischer Entwurf aus der Daily-Pipeline.\n\n"
        f"- Parlament: `{draft.parliament_id}`\n"
        f"- Datum: {draft.election_date.isoformat()}\n"
        f"- Staging: `{path}`\n"
        f"- Quelle: {draft.source_url}\n\n"
        f"Bitte `election_results.yaml` manuell prüfen und ggf. übernehmen "
        f"(inkl. `grundmandat_party_ids`).\n"
        f"Parteien: {', '.join(f'{k}={v}' for k, v in sorted(draft.results.items()))}\n"
    )
    if not token or not repo:
        log.info("Review-Issue nur geloggt (kein Token/Repo): %s", title)
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{repo}"
    try:
        search = requests.get(
            f"{api}/issues",
            params={"state": "open", "per_page": 50},
            headers=headers,
            timeout=30,
        )
        search.raise_for_status()
        for issue in search.json():
            if issue.get("title") == title:
                log.info("Issue bereits offen (#%s): %s", issue.get("number"), title)
                return
        create = requests.post(
            f"{api}/issues",
            headers=headers,
            json={"title": title, "body": body},
            timeout=30,
        )
        create.raise_for_status()
        log.info("GitHub-Issue angelegt: %s → #%s", title, create.json().get("number"))
    except Exception as exc:
        log.warning("GitHub-Issue fehlgeschlagen (%s): %s", title, exc)


def run_election_watch(*, as_of: date | None = None) -> list[Path]:
    """
    Fehlertoleranter Pipeline-Schritt: pending → fetch → draft + Issue.

    Exceptions pro Parlament werden geloggt; Rückgabe: geschriebene Pfade.
    """
    as_of = as_of or date.today()
    written: list[Path] = []
    pending = pending_elections(as_of=as_of)
    if not pending:
        log.info("Election-Watch: keine ausstehenden Wahlen.")
        return written

    log.info("Election-Watch: %d ausstehende Parlament(e)", len(pending))
    for parl in pending:
        assert parl.next_election_date is not None
        try:
            draft = fetch_wikipedia_election_result(parl.id, parl.next_election_date)
            if draft is None:
                log.info(
                    "Election-Watch: noch keine auswertbare Tabelle für %s (%s)",
                    parl.id,
                    parl.next_election_date,
                )
                continue
            path = write_draft(draft)
            written.append(path)
            log.info("Election-Watch: Draft geschrieben %s", path)
            maybe_open_review_issue(draft, path)
            if parl.id == "de_bundestag":
                log.warning(
                    "Bundesregierung sollte nach dieser Wahl neu geprüft werden."
                )
            else:
                log.warning(
                    "Regierung von %s sollte nach dieser Wahl neu geprüft werden.",
                    parl.name,
                )
        except Exception:
            log.exception("Election-Watch: Fehler bei %s — weiter", parl.id)
    return written


def maybe_scrape_ministerpraesidenten_diff() -> list[str]:
    """
    Best-Effort: Wikipedia „Liste der Ministerpräsidenten…“ vs. bundesrat.yaml.

    Fragil — nur Hinweistexte, nie blockierend. Schreibt optional Staging-Notiz.
    """
    from analysis.bundesrat import load_bundesrat_config

    notes: list[str] = []
    try:
        html, _title = fetch_de_wikipedia_html(
            "Liste der Ministerpräsidenten der deutschen Länder"
        )
    except Exception as exc:
        log.info("Ministerpräsidenten-Liste nicht erreichbar: %s", exc)
        return notes

    # Nur grober Existenz-Check: Seite hat Inhalt und Config hat 16 Länder
    if len(html) < 1000:
        return notes
    try:
        cfg = load_bundesrat_config()
        if len(cfg.states) != 16:
            notes.append(
                f"Bundesrat-Config hat {len(cfg.states)} Länder (erwartet 16) — prüfen."
            )
        # Staging-Hinweisdatei (kein automatischer Diff der Parteien — zu fragil)
        hint_dir = ROOT / "data" / "staging" / "government"
        hint_dir.mkdir(parents=True, exist_ok=True)
        hint = hint_dir / "ministerpraesidenten_check.yaml"
        hint.write_text(
            yaml.safe_dump(
                {
                    "checked_page": "Liste der Ministerpräsidenten der deutschen Länder",
                    "bundesrat_stand": cfg.stand,
                    "note": (
                        "Automatischer Best-Effort-Check: Wikipedia-Seite erreichbar. "
                        "government_parties manuell gegen die Liste abgleichen."
                    ),
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        notes.append(
            "Ministerpräsidenten-Wikipedia erreichbar — government_parties manuell prüfen "
            f"(Hinweis: {hint.relative_to(ROOT)})."
        )
    except Exception as exc:
        log.info("Ministerpräsidenten-Diff übersprungen: %s", exc)
    return notes
