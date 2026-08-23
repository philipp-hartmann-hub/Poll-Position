# Streamlit Multi-Page Einstieg: streamlit run app/Home.py

from pathlib import Path

import streamlit as st

from app.lib.db import load_parliaments, warehouse_exists
from app.lib.ui import render_footer

st.set_page_config(
    page_title="Poll-Position",
    page_icon="📊",
    layout="wide",
)

st.title("Poll-Position")
st.markdown(
    "Umfragetracker für **Deutschland und Europa** — "
    "Trends, Sitzprojektionen und Koalitionsszenarien."
)

focus = st.radio(
    "Fokus",
    ["Deutschland", "Europa"],
    horizontal=True,
    help="Steuert die Startnavigation; alle Seiten bleiben über die Seitenleiste erreichbar.",
)

pars = load_parliaments()
n_surveys_hint = ""
if warehouse_exists() and not pars.empty:
    n_de = len(pars[pars["country"] == "DE"])
    n_surveys_hint = f"{n_de} deutsche Parlamente im Warehouse."

if focus == "Deutschland":
    st.subheader("Deutschland")
    st.page_link("pages/1_Deutschland_Bund.py", label="Bundestag — Trends & Koalitionen")
    st.page_link("pages/2_Deutschland_Laender.py", label="Länder — Landtage")
    st.page_link("pages/4_Institute_Vergleich.py", label="Institute — House Effects")
    st.page_link("pages/5_Was_waere_wenn.py", label="Was wäre wenn — Szenarien")
    if n_surveys_hint:
        st.caption(n_surveys_hint)
else:
    st.subheader("Europa")
    st.page_link("pages/3_Europa_Uebersicht.py", label="Europa-Übersicht — Karte & Drilldown")
    st.caption("Länderdetail über die Auswahl auf der Übersichtsseite.")

warehouse = Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"
if warehouse.exists():
    st.success("Warehouse verbunden (`data/warehouse.duckdb`).")
else:
    st.warning("Warehouse fehlt — Pipeline starten: `python -m data_pipeline.run`")

render_footer()
