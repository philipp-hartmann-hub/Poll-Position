# Streamlit Multi-Page Einstieg: streamlit run app/Home.py

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Poll-Position",
    page_icon="📊",
    layout="wide",
)

st.title("Poll-Position")
st.markdown(
    """
Umfragetracker für **Deutschland und Europa**.

Daten aus Dawum und paneuropäischen Quellen werden zusammengeführt;
Sitzverteilung und Koalitionsszenarien kommen aus dem UI-freien Paket `analysis/`.
"""
)

warehouse = Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"
st.info(
    f"Warehouse: `{'vorhanden' if warehouse.exists() else 'fehlt — bitte Pipeline starten'}`  \n"
    f"`python -m data_pipeline.run`"
)

st.caption(
    "Umfragedaten: [dawum.de](https://dawum.de/) "
    "([Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/))"
)
