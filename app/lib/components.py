"""Wiederverwendbare Streamlit-Abschnitte (dünne Orchestrierung)."""

from __future__ import annotations

import streamlit as st

from app.lib.analysis_bridge import (
    compute_majorities,
    compute_trend_frame,
    default_exclusion_toggles,
    project_seats,
)
from app.lib.charts import hemicycle_figure, seats_bar_figure, trend_figure
from app.lib.db import warehouse_exists
from app.lib.ui import SHORT_TO_CANONICAL


def render_parliament_analysis(parliament_id: str, *, title: str | None = None) -> None:
    """Trend, Sitze (Hemicycle), Koalitionsrechner mit Live-Ausschlüssen."""
    if not warehouse_exists():
        st.warning("Warehouse fehlt — bitte `python -m data_pipeline.run` ausführen.")
        return

    if title:
        st.subheader(title)

    days = st.slider("Zeitfenster (Tage)", 30, 730, 180, key=f"days_{parliament_id}")

    with st.spinner("Berechne Durchschnitt und Sitze…"):
        avg_df, seats_id, seats_named = project_seats(parliament_id, days=days)
        trend_df = compute_trend_frame(parliament_id, days=max(days, 180))

    if avg_df.empty:
        st.info("Keine Umfragedaten für dieses Parlament.")
        return

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.plotly_chart(
            trend_figure(trend_df, title="Umfragetrend (mit Unsicherheitsbändern)"),
            use_container_width=True,
        )
    with c2:
        st.dataframe(
            avg_df[["party_name", "average_share", "n_surveys", "swing"]].rename(
                columns={
                    "party_name": "Partei",
                    "average_share": "Ø %",
                    "n_surveys": "n",
                    "swing": "Swing",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Sitzprojektion")
    h1, h2 = st.columns([1.4, 1])
    with h1:
        st.plotly_chart(
            hemicycle_figure(seats_named, title="Hemicycle"),
            use_container_width=True,
        )
    with h2:
        st.plotly_chart(seats_bar_figure(seats_named), use_container_width=True)
        total = sum(seats_named.values())
        st.metric("Sitze gesamt", total)

    st.markdown("### Koalitionsrechner")
    apply_ex = st.toggle("Ausschlussregeln anwenden", value=True, key=f"ex_on_{parliament_id}")
    toggles = default_exclusion_toggles(parliament_id)
    if not toggles:
        # Fallback für Landtage: gleiche AfD-Ausschlüsse wie Bund
        toggles = default_exclusion_toggles("de_bundestag")

    enabled: list[tuple[str, str]] = []
    if toggles:
        cols = st.columns(min(3, len(toggles)))
        for i, (label, party, excluded) in enumerate(toggles):
            short = label.replace("de:", "").replace("_", " ")
            if cols[i % len(cols)].checkbox(short, value=True, key=f"ex_{parliament_id}_{i}"):
                enabled.append((party, excluded))

    result = compute_majorities(
        seats_id,
        avg_df,
        parliament_id=parliament_id,
        enabled_rules=enabled,
        apply_exclusions=apply_ex,
    )

    inv_canon = {v: k for k, v in SHORT_TO_CANONICAL.items()}
    rows = []
    for c in result.coalitions[:20]:
        names = " + ".join(inv_canon.get(p, p) for p in c.parties)
        rows.append(
            {
                "Koalition": names,
                "Sitze": c.seats,
                "Mehrheit": "ja" if c.seats >= result.majority_threshold else "nein",
                "Span": c.compatibility_span,
                "Minimal": "ja" if c.is_minimal_winning else "nein",
            }
        )
    st.caption(
        f"Mehrheit ab {result.majority_threshold} Sitzen · "
        f"{result.excluded_by_rules} Kombinationen durch Regeln ausgeschlossen"
    )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("Keine Mehrheitskoalition unter den aktuellen Regeln.")
