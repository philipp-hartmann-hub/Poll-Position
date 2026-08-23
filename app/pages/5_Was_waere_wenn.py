"""Was-wäre-wenn: Slider → scenario.run_scenario."""

from __future__ import annotations

import streamlit as st

from analysis.scenario import ScenarioInput, run_scenario
from app.lib.analysis_bridge import compute_current_averages
from app.lib.charts import hemicycle_figure, seats_bar_figure
from app.lib.db import load_parliaments, warehouse_exists
from app.lib.ui import SHORT_TO_CANONICAL, render_footer
from data_pipeline.schema import load_parliament_config

st.set_page_config(page_title="Was wäre wenn · Poll-Position", layout="wide")
st.title("Was wäre wenn")
st.caption("Anteile per Slider anpassen — Sitze und Koalitionen werden live neu berechnet.")

if not warehouse_exists():
    st.warning("Warehouse fehlt.")
    render_footer()
    st.stop()

pars = load_parliaments()
options = pars[pars["country"] == "DE"][["id", "name"]].sort_values("name")
pid = st.selectbox(
    "Parlament",
    options["id"].tolist(),
    format_func=lambda i: options.set_index("id").loc[i, "name"],
    index=int(options["id"].tolist().index("de_bundestag"))
    if "de_bundestag" in options["id"].tolist()
    else 0,
)

avg = compute_current_averages(pid, days=120)
if avg.empty:
    st.info("Keine Basis-Umfragen für Slider.")
    render_footer()
    st.stop()

# Top-Parteien + Rest als Sonstige
show = avg[avg["party_name"] != "Sonstige"].head(10)
baseline = {row.party_id: float(row.average_share) for row in show.itertuples()}
names = {row.party_id: row.party_name for row in show.itertuples()}

st.markdown("### Anteile (%)")
cols = st.columns(2)
overrides: dict[str, float] = {}
for i, (party_id, base) in enumerate(baseline.items()):
    with cols[i % 2]:
        overrides[party_id] = st.slider(
            str(names[party_id]),
            min_value=0.0,
            max_value=40.0,
            value=float(round(base, 1)),
            step=0.1,
            key=f"sc_{pid}_{party_id}",
        )

total_override = sum(overrides.values())
st.caption(f"Summe der Slider: **{total_override:.1f} %** (Rest implizit Sonstige / nicht modelliert).")

apply_ex = st.toggle("Ausschlussregeln anwenden", value=True)

bundle = load_parliament_config()
parliament = next((p for p in bundle.parliaments if p.id == pid), None)
system = None
if parliament:
    system = next(s for s in bundle.election_systems if s.key == parliament.election_system_key)

result = run_scenario(
    ScenarioInput(party_shares=overrides, parliament_id=pid),
    parliament=parliament,
    election_system=system,
    apply_exclusions=apply_ex,
)

# Namen für Charts
named = {names.get(k, k): v for k, v in result.seats.items()}
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(hemicycle_figure(named, title="Szenario-Sitze"), use_container_width=True)
with c2:
    st.plotly_chart(seats_bar_figure(named), use_container_width=True)
    st.metric("Sitze", result.total_seats)

inv = {v: k for k, v in SHORT_TO_CANONICAL.items()}
# Koalitionen ggf. mit Warehouse-IDs — Anzeige über Namen
maj = result.majorities
rows = []
for c in maj.coalitions[:15]:
    label = " + ".join(names.get(p, inv.get(p, p)) for p in c.parties)
    rows.append({"Koalition": label, "Sitze": c.seats, "Span": c.compatibility_span})

st.markdown("### Mehrheiten im Szenario")
st.caption(f"Mehrheit ab {maj.majority_threshold} · ausgeschlossen: {maj.excluded_by_rules}")
if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.warning("Keine Mehrheitskoalition.")

render_footer()
