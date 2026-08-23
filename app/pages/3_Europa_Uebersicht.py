"""Europa-Übersicht: Karte nach stärkster Parteienfamilie, Drilldown."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from analysis.party_families import (
    EuropeanPartyFamily,
    aggregate_by_family,
    load_party_families,
    map_party_to_family,
)
from app.lib.charts import COUNTRY_CENTROIDS, europe_family_deck
from app.lib.db import load_all_latest_shares_by_country, warehouse_exists
from app.lib.ui import SHORT_TO_CANONICAL, render_footer

st.set_page_config(page_title="Europa · Poll-Position", layout="wide")
st.title("Europa — Übersicht")
st.caption("Einfärbung nach stärkster europäischer Parteienfamilie je Land (neueste Umfragen).")

if not warehouse_exists():
    st.warning("Warehouse fehlt.")
    render_footer()
    st.stop()

df = load_all_latest_shares_by_country()
cfg = load_party_families()
# Kurzname → kanonische ID für Familien-YAML
name_to_canon = dict(SHORT_TO_CANONICAL)
for entry in cfg.parties:
    name_to_canon.setdefault(entry.short_name, entry.party_id)

if df.empty:
    st.info("Keine Survey-Daten für die Europakarte.")
    render_footer()
    st.stop()

# National/EU-Ebene bevorzugen
national = df[df["level_kind"].isin(["national", "eu_parliament"])]
if national.empty:
    national = df

rows_map: list[dict] = []
detail_by_country: dict[str, pd.DataFrame] = {}

for country, g in national.groupby("country"):
    # stärkste Partei je Land (Mittel über Parlamente falls mehrere)
    by_party = g.groupby(["party_id", "party_name"], as_index=False)["share"].mean()
    detail_by_country[str(country)] = by_party.sort_values("share", ascending=False)

    shares: dict[str, float] = {}
    for row in by_party.itertuples():
        canon = name_to_canon.get(str(row.party_name), row.party_id)
        shares[canon] = shares.get(canon, 0.0) + float(row.share)

    fam_shares = aggregate_by_family(shares, config=cfg)
    if not fam_shares:
        top_fam = EuropeanPartyFamily.NI
        top_share = 0.0
    else:
        top_fam = max(fam_shares, key=fam_shares.get)  # type: ignore[arg-type]
        top_share = fam_shares[top_fam]

    top_party = by_party.iloc[0]
    latlon = COUNTRY_CENTROIDS.get(str(country), (50.0, 10.0))
    rows_map.append(
        {
            "country": str(country),
            "lat": latlon[0],
            "lon": latlon[1],
            "family": top_fam.value if hasattr(top_fam, "value") else str(top_fam),
            "label": f"{top_party.party_name} ({top_party.share:.1f}%)",
            "share": round(float(top_share), 1),
        }
    )

st.pydeck_chart(europe_family_deck(rows_map), use_container_width=True)

countries = sorted(detail_by_country.keys())
selected = st.selectbox("Drilldown Land", countries, index=countries.index("DE") if "DE" in countries else 0)
detail = detail_by_country[selected].copy()
detail["family"] = detail.apply(
    lambda r: (
        (map_party_to_family(name_to_canon.get(str(r.party_name), r.party_id), config=cfg) or EuropeanPartyFamily.NI).value
    ),
    axis=1,
)
st.subheader(f"Detail: {selected}")
st.dataframe(
    detail.rename(columns={"party_name": "Partei", "share": "%", "family": "Familie"})[
        ["Partei", "%", "family"]
    ],
    use_container_width=True,
    hide_index=True,
)

st.caption(f"Stand der Aggregation: {date.today().isoformat()} (letzte Survey-Publikation je Parlament).")
render_footer()
