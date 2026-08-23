"""Bundestags-Umfragen, Sitzprojektion, Koalitionen."""

from __future__ import annotations

import streamlit as st

from app.lib.components import render_parliament_analysis
from app.lib.ui import render_footer

st.set_page_config(page_title="Deutschland Bund · Poll-Position", layout="wide")
st.title("Deutschland — Bundestag")
st.caption("Gewichteter Umfragemittelwert, Sitzprojektion und Koalitionsoptionen.")

render_parliament_analysis("de_bundestag")
render_footer()
