"""Landesspezifische Parser für Wikipedia-Umfrage-Tabellen."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from bs4 import BeautifulSoup, Tag

META_HEADERS = {
    "polling firm",
    "polling firm/commissioner",
    "polling aggregator",
    "fieldwork date",
    "date",
    "date updated",
    "sample size",
    "samplesize",
    "method",
    "turnout",
    "lead",
    "ref.",
    "ref",
    "source",
}

SKIP_PARTY_HEADERS = {
    "lead",
    "turnout",
    "ref.",
    "ref",
    "others",
    "oth.",
    "oth",
    "other",
}


@dataclass
class IntermediatePoll:
    """Gemeinsames Zwischenformat vor dem Mapping auf Survey."""

    institute: str
    field_date_from: date | None
    field_date_to: date | None
    sample_size: int | None
    results: dict[str, float] = field(default_factory=dict)
    method: str | None = None
    tasker: str | None = None


def _cell_text(cell: Tag) -> str:
    return cell.get_text(" ", strip=True)


def _party_label(cell: Tag) -> str | None:
    text = _cell_text(cell)
    if text:
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned
    link = cell.find("a", title=True)
    if link and link.get("title"):
        return str(link["title"]).strip()
    img = cell.find("img", alt=True)
    if img and img.get("alt"):
        return str(img["alt"]).strip()
    return None


def _is_meta(label: str) -> bool:
    return label.lower().strip() in META_HEADERS


def _parse_percent(raw: str) -> float | None:
    if not raw or raw in {"–", "-", "—", "?", "N/A", "n/a"}:
        return None
    # "32.0 131" / "32,0" / "32%" → erste Zahl
    match = re.search(r"(\d+[.,]?\d*)\s*%?", raw.replace("\xa0", " "))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _parse_sample_size(raw: str) -> int | None:
    if not raw or raw in {"–", "-", "—", "?"}:
        return None
    digits = re.sub(r"[^\d]", "", raw.split()[0] if raw else "")
    return int(digits) if digits else None


_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def parse_fieldwork_dates(raw: str, *, default_year: int | None = None) -> tuple[date | None, date | None]:
    """Parst typische Wikipedia-Datumsangaben wie '15–17 Jul 2026' oder '22–29 Dec'."""
    if not raw or raw.lower() in {"n/a", "tba"}:
        return None, None
    text = raw.replace("–", "-").replace("—", "-").replace("/", "-")
    # 15-17 Jul 2026
    m = re.search(
        r"(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        text,
    )
    if m:
        d1, d2, mon, year = int(m.group(1)), int(m.group(2)), m.group(3).lower(), int(m.group(4))
        month = _MONTHS.get(mon[:3]) or _MONTHS.get(mon)
        if month:
            return date(year, month, d1), date(year, month, d2)
    # 15 Jul 2026
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if m:
        d1, mon, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = _MONTHS.get(mon[:3]) or _MONTHS.get(mon)
        if month:
            day = date(year, month, d1)
            return day, day
    # 22-29 Dec (ohne Jahr)
    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)", text)
    if m and default_year:
        d1, d2, mon = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        month = _MONTHS.get(mon[:3]) or _MONTHS.get(mon)
        if month:
            return date(default_year, month, d1), date(default_year, month, d2)
    # ISO
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        day = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return day, day
    return None, None


def _split_institute_tasker(raw: str) -> tuple[str, str | None]:
    cleaned = re.sub(r"\[\s*\d+\s*\]", "", raw).strip()
    if "/" in cleaned:
        left, right = cleaned.split("/", 1)
        return left.strip(), right.strip() or None
    return cleaned, None


def _header_party_names(header_row: Tag) -> list[str | None]:
    labels: list[str | None] = []
    for cell in header_row.find_all(["th", "td"]):
        labels.append(_party_label(cell))
    return labels


def _find_header_row(table: Tag) -> Tag | None:
    for row in table.find_all("tr"):
        texts = [_cell_text(c).lower() for c in row.find_all(["th", "td"])]
        if any("polling firm" in t or "polling aggregator" in t for t in texts):
            return row
    return None


def parse_generic_wikitable(
    table: Tag,
    *,
    party_aliases: dict[str, str] | None = None,
    default_year: int | None = None,
    max_rows: int | None = 40,
) -> list[IntermediatePoll]:
    """
    Generischer Parser für wikitable-Umfragen.

    Erwartet Header mit Polling firm / Fieldwork date / Sample size und
    anschließenden Parteispalten (Text, Link-Title oder Bild-Alt).
    """
    header = _find_header_row(table)
    if header is None:
        return []

    labels = _header_party_names(header)
    aliases = {k.lower(): v for k, v in (party_aliases or {}).items()}

    firm_idx = next((i for i, l in enumerate(labels) if l and "polling firm" in l.lower()), None)
    if firm_idx is None:
        firm_idx = next(
            (i for i, l in enumerate(labels) if l and "polling aggregator" in l.lower()),
            0,
        )
    date_idx = next(
        (i for i, l in enumerate(labels) if l and ("fieldwork" in l.lower() or l.lower() == "date" or "date updated" in l.lower())),
        None,
    )
    sample_idx = next(
        (i for i, l in enumerate(labels) if l and "sample" in l.lower()),
        None,
    )
    method_idx = next(
        (i for i, l in enumerate(labels) if l and l.lower() == "method"),
        None,
    )

    party_cols: list[tuple[int, str]] = []
    for i, label in enumerate(labels):
        if label is None:
            continue
        low = label.lower()
        if i in {firm_idx, date_idx, sample_idx, method_idx}:
            continue
        if low in SKIP_PARTY_HEADERS or _is_meta(label):
            if low in {"others", "oth.", "oth", "other"}:
                party_cols.append((i, "Others"))
            continue
        short = aliases.get(low, label)
        party_cols.append((i, short))

    polls: list[IntermediatePoll] = []
    data_rows = 0
    for row in header.find_next_siblings("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        firm_raw = _cell_text(cells[firm_idx]) if firm_idx is not None and firm_idx < len(cells) else ""
        if not firm_raw or firm_raw.lower() in {"polling firm", "average", "election result"}:
            continue
        # Logo-/Zwischenheader-Zeilen überspringen
        if sum(1 for c in cells if _cell_text(c)) < 3:
            continue

        institute, tasker = _split_institute_tasker(firm_raw)
        date_raw = (
            _cell_text(cells[date_idx]) if date_idx is not None and date_idx < len(cells) else ""
        )
        start, end = parse_fieldwork_dates(date_raw, default_year=default_year)
        sample = (
            _parse_sample_size(_cell_text(cells[sample_idx]))
            if sample_idx is not None and sample_idx < len(cells)
            else None
        )
        method = (
            _cell_text(cells[method_idx])
            if method_idx is not None and method_idx < len(cells)
            else None
        )

        results: dict[str, float] = {}
        for col_i, party in party_cols:
            if col_i >= len(cells):
                continue
            value = _parse_percent(_cell_text(cells[col_i]))
            if value is not None:
                results[party] = value

        if len(results) < 2:
            continue

        polls.append(
            IntermediatePoll(
                institute=institute,
                field_date_from=start,
                field_date_to=end,
                sample_size=sample,
                results=results,
                method=method or None,
                tasker=tasker,
            )
        )
        data_rows += 1
        if max_rows is not None and data_rows >= max_rows:
            break

    return polls


def parse_html_tables(
    html: str,
    *,
    party_aliases: dict[str, str] | None = None,
    default_year: int | None = None,
    max_tables: int = 3,
    max_rows_per_table: int = 30,
) -> list[IntermediatePoll]:
    soup = BeautifulSoup(html, "lxml")
    polls: list[IntermediatePoll] = []
    for table in soup.select("table.wikitable")[:max_tables]:
        polls.extend(
            parse_generic_wikitable(
                table,
                party_aliases=party_aliases,
                default_year=default_year,
                max_rows=max_rows_per_table,
            )
        )
    return polls


# --- Landesspezifische Einstiege (Aliases + Defaults) ---

AUSTRIA_ALIASES = {
    "freedom party of austria": "FPÖ",
    "austrian people's party": "ÖVP",
    "social democratic party of austria": "SPÖ",
    "neos (austria)": "NEOS",
    "the greens (austria)": "GRÜNE",
    "communist party of austria": "KPÖ",
}

FRANCE_ALIASES = {
    "national rally": "RN",
    "renaissance (french political party)": "RE",
    "la france insoumise": "LFI",
    "the republicans (france)": "LR",
    "socialist party (france)": "PS",
    "the ecologists (france)": "ÉCO",
}

NETHERLANDS_ALIASES = {
    "party for freedom": "PVV",
    "groenlinks–pvdA": "GL-PvdA",
    "people's party for freedom and democracy": "VVD",
    "new social contract": "NSC",
    "democrats 66": "D66",
    "farmer–citizen movement": "BBB",
    "christian democratic appeal": "CDA",
    "socialist party (netherlands)": "SP",
}

ITALY_ALIASES = {
    "brothers of italy": "FdI",
    "democratic party (italy)": "PD",
    "five star movement": "M5S",
    "lega (political party)": "Lega",
    "forza italia (2013)": "FI",
    "action (italian political party)": "A",
    "italia viva": "IV",
    "greens and left alliance": "AVS",
}

SPAIN_ALIASES = {
    "people's party (spain)": "PP",
    "spanish socialist workers' party": "PSOE",
    "vox (political party)": "Vox",
    "sumar (electoral platform)": "Sumar",
    "podemos (spanish political party)": "Podemos",
}

POLAND_ALIASES = {
    "law and justice": "PiS",
    "civic coalition": "KO",
    "confederation liberty and independence": "Konf",
    "the left (poland)": "Lewica",
    "third way (poland)": "TD",
}

SWEDEN_ALIASES = {
    "social democratic party (sweden)": "S",
    "sweden democrats": "SD",
    "moderate party": "M",
    "left party (sweden)": "V",
    "centre party (sweden)": "C",
    "christian democrats (sweden)": "KD",
    "greens (sweden)": "MP",
    "liberals (sweden)": "L",
}

PORTUGAL_ALIASES = {
    "social democratic party (portugal)": "PSD",
    "socialist party (portugal)": "PS",
    "chega": "Chega",
    "unitary democratic coalition": "CDU",
    "liberal initiative": "IL",
    "livre": "L",
}


def parse_austria(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=AUSTRIA_ALIASES, default_year=2026)


def parse_france(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=FRANCE_ALIASES, default_year=2026)


def parse_netherlands(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=NETHERLANDS_ALIASES, default_year=2026)


def parse_italy(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=ITALY_ALIASES, default_year=2026)


def parse_spain(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=SPAIN_ALIASES, default_year=2026)


def parse_poland(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=POLAND_ALIASES, default_year=2026)


def parse_sweden(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=SWEDEN_ALIASES, default_year=2026)


def parse_portugal(html: str) -> list[IntermediatePoll]:
    return parse_html_tables(html, party_aliases=PORTUGAL_ALIASES, default_year=2026)


PARSERS: dict[str, Callable[[str], list[IntermediatePoll]]] = {
    "austria": parse_austria,
    "france": parse_france,
    "netherlands": parse_netherlands,
    "italy": parse_italy,
    "spain": parse_spain,
    "poland": parse_poland,
    "sweden": parse_sweden,
    "portugal": parse_portugal,
}
