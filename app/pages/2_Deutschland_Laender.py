"""Landtags-Umfragen je Bundesland."""

from __future__ import annotations

import streamlit as st

from app.lib.components import render_parliament_analysis
from app.lib.db import load_parliaments, warehouse_exists
from app.lib.ui import render_footer

st.set_page_config(page_title="Deutschland Länder · Poll-Position", layout="wide")
st.title("Deutschland — Länder")

if not warehouse_exists():
    st.warning("Warehouse fehlt — bitte Pipeline starten.")
    render_footer()
    st.stop()

pars = load_parliaments()
states = pars[pars["level_kind"] == "state"].sort_values("name")
if states.empty:
    st.info("Keine Landtage im Warehouse.")
    render_footer()
    st.stop()

labels = {row.id: row.name for row in states.itertuples()}
choice = st.selectbox(
    "Bundesland / Landtag",
    options=list(labels.keys()),
    format_func=lambda i: labels[i],
)

render_parliament_analysis(choice, title=labels[choice])
render_footer()
