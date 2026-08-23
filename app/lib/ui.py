"""UI-Hilfen: Farben, Footer, Partei-Mapping."""

from __future__ import annotations

import streamlit as st

PARTY_COLORS: dict[str, str] = {
    "AfD": "#009EE0",
    "CDU/CSU": "#000000",
    "CDU": "#000000",
    "CSU": "#0080C8",
    "SPD": "#E3000F",
    "Grüne": "#64A12D",
    "FDP": "#FFED00",
    "Linke": "#BE3075",
    "BSW": "#7B2D8E",
    "Freie Wähler": "#F7A800",
    "Sonstige": "#A0A0A0",
    "SSW": "#A0C8E0",
}

# Warehouse-Kurzname → kanonische ID (für Ausschlussregeln / Familien)
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


def party_color(name: str) -> str:
    return PARTY_COLORS.get(name, "#888888")


def render_footer() -> None:
    st.divider()
    st.caption(
        "Datenquellen: [dawum.de](https://dawum.de/) "
        "([ODbL](https://opendatacommons.org/licenses/odbl/1-0/)) · "
        "Wikipedia-Mitwirkende ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)) · "
        "Wahlrechtsparameter: [Bundeswahlleiterin](https://www.bundeswahlleiterin.de/), "
        "Landeswahlleitungen / [wahlrecht.de](https://www.wahlrecht.de/landtage/)"
    )


def page_setup(title: str, *, wide: bool = True) -> None:
    st.set_page_config(page_title=f"{title} · Poll-Position", layout="wide" if wide else "centered")
