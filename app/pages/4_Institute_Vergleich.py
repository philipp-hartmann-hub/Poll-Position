"""House Effects und Backtesting je Institut."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analysis.house_effects import (
    backtest_institutes,
    compute_house_effects,
    institute_accuracy_scores,
)
from app.lib.analysis_bridge import series_to_points
from app.lib.db import load_institutes, load_parties, load_survey_series, warehouse_exists
from app.lib.ui import render_footer
from data_pipeline.reference.election_results import load_election_results

st.set_page_config(page_title="Institute · Poll-Position", layout="wide")
st.title("Institute — Vergleich")
st.caption("House Effects (Abweichung vom Peer-Durchschnitt) und Backtesting gegen Wahlergebnisse.")

if not warehouse_exists():
    st.warning("Warehouse fehlt.")
    render_footer()
    st.stop()

parliament_id = st.selectbox(
    "Parlament",
    ["de_bundestag", "de_by_landtag", "de_th_landtag", "de_nw_landtag"],
    format_func=lambda x: {
        "de_bundestag": "Bundestag",
        "de_by_landtag": "Bayern",
        "de_th_landtag": "Thüringen",
        "de_nw_landtag": "NRW",
    }.get(x, x),
)
window = st.slider("House-Effect-Fenster (Tage)", 7, 60, 14)
days = st.slider("Datenhorizont", 90, 730, 365)

since = date.today() - timedelta(days=days)
raw = load_survey_series(parliament_id, since=since)
if raw.empty:
    st.info("Keine Umfragen.")
    render_footer()
    st.stop()

points = series_to_points(raw)
# House effects nur an wenigen Stützstellen (Performance)
ref_dates = sorted({p.as_of for p in points})
# Monatsraster
ref_sample = [d for i, d in enumerate(ref_dates) if i % max(1, len(ref_dates) // 24) == 0][-24:]

with st.spinner("Berechne House Effects…"):
    effects = compute_house_effects(points, window_days=window, reference_dates=ref_sample)

institutes = load_institutes()
parties = load_parties()
inst_name = dict(zip(institutes["id"], institutes["name"])) if not institutes.empty else {}
party_name = dict(zip(parties["id"], parties["short_name"])) if not parties.empty else {}

if effects:
    eff_df = pd.DataFrame(
        [
            {
                "Institut": inst_name.get(e.institute_id, e.institute_id),
                "Partei": party_name.get(e.party_id, e.party_id),
                "as_of": e.as_of,
                "House Effect (pp)": round(e.house_effect, 2),
                "Institut %": round(e.institute_share, 2),
                "Peers %": round(e.peer_average, 2),
            }
            for e in effects
        ]
    )
    latest = (
        eff_df.sort_values("as_of")
        .groupby(["Institut", "Partei"], as_index=False)
        .tail(1)
    )
    st.subheader("Aktuelle House Effects")
    pivot = latest.pivot_table(
        index="Institut", columns="Partei", values="House Effect (pp)", aggfunc="mean"
    )
    st.dataframe(pivot.round(1), use_container_width=True)
else:
    st.info("Keine House Effects berechenbar (zu wenige Peer-Institute).")

st.subheader("Backtesting")
try:
    elections = load_election_results()
except Exception:
    elections = None

if elections is None or not elections.elections:
    st.caption("Keine Referenz-Wahlergebnisse geladen.")
else:
    relevant = [e for e in elections.elections if e.parliament_id == parliament_id]
    if not relevant:
        st.caption(f"Kein Wahlergebnis für `{parliament_id}` in der Referenzdatei.")
    else:
        # Wahlergebnis-IDs (de:spd …) → Warehouse-IDs über Kurznamen
        from app.lib.ui import SHORT_TO_CANONICAL

        name_to_wh = (
            dict(zip(parties["short_name"], parties["id"])) if not parties.empty else {}
        )
        # SHORT_TO_CANONICAL: name -> canon; invert via party short names
        canon_to_name = {v: k for k, v in SHORT_TO_CANONICAL.items()}

        election_tuples = []
        for el in relevant:
            mapped: dict[str, float] = {}
            for pid, share in el.results.items():
                pname = canon_to_name.get(pid)
                wh = name_to_wh.get(pname) if pname else None
                if wh:
                    mapped[wh] = float(share)
            if mapped:
                election_tuples.append((el.parliament_id, el.election_date, mapped))

        records = backtest_institutes(points, election_tuples) if election_tuples else []
        if records:
            scores = institute_accuracy_scores(records)
            score_df = pd.DataFrame(
                [
                    {
                        "Institut": inst_name.get(s.institute_id, s.institute_id),
                        "n": s.n_comparisons,
                        "MAE": round(s.mae, 2),
                        "RMSE": round(s.rmse, 2),
                        "Score": round(s.score, 3),
                    }
                    for s in scores
                ]
            ).sort_values("MAE")
            st.dataframe(score_df, use_container_width=True, hide_index=True)
        else:
            st.caption(
                "Backtest ohne Treffer — Partei-IDs in Wahlergebnissen und Umfragen "
                "stimmen möglicherweise nicht überein."
            )

render_footer()
