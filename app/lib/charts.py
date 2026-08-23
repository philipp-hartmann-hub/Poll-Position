"""Plotly-/Pydeck-Visualisierungen (nur Rendering)."""

from __future__ import annotations

import math
from typing import Mapping

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk

from app.lib.ui import party_color


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(128,128,128,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def trend_figure(df: pd.DataFrame, *, title: str = "Umfragetrend") -> go.Figure:
    """df: columns as_of, party_name, share (optional: lo, hi for Bänder)."""
    fig = go.Figure()
    if df.empty:
        fig.update_layout(title=title, height=420)
        return fig
    for party in sorted(df["party_name"].unique()):
        sub = df[df["party_name"] == party].sort_values("as_of")
        color = party_color(str(party))
        if {"lo", "hi"}.issubset(sub.columns):
            fill = _hex_to_rgba(color, 0.15)
            fig.add_trace(
                go.Scatter(
                    x=list(sub["as_of"]) + list(sub["as_of"])[::-1],
                    y=list(sub["hi"]) + list(sub["lo"])[::-1],
                    fill="toself",
                    fillcolor=fill,
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False,
                    hoverinfo="skip",
                    name=f"{party} Band",
                )
            )
        fig.add_trace(
            go.Scatter(
                x=sub["as_of"],
                y=sub["share"],
                mode="lines",
                name=str(party),
                line=dict(color=color, width=2),
            )
        )
    fig.update_layout(
        title=title,
        yaxis_title="%",
        height=420,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=40, r=20, t=50, b=60),
    )
    return fig


def hemicycle_figure(seats: Mapping[str, int], *, title: str = "Sitzverteilung") -> go.Figure:
    """Halbkreis-/Hemicycle aus Sitzzahlen (Plotly Scatter)."""
    items = [(k, v) for k, v in seats.items() if v > 0]
    items.sort(key=lambda kv: -kv[1])
    total = sum(v for _, v in items) or 1
    # Reihen wie in einem Plenum
    rows = max(4, int(math.ceil(math.sqrt(total / 2))))
    points_x: list[float] = []
    points_y: list[float] = []
    colors: list[str] = []
    texts: list[str] = []

    seat_list: list[str] = []
    for name, n in items:
        seat_list.extend([name] * n)

    idx = 0
    for row in range(rows):
        n_in_row = max(1, int((row + 1) / rows * (total * 2 / rows)))
        n_in_row = min(n_in_row, total - idx)
        if n_in_row <= 0:
            break
        radius = 0.45 + 0.55 * (row / max(rows - 1, 1))
        for i in range(n_in_row):
            if idx >= len(seat_list):
                break
            angle = math.pi * (i + 0.5) / n_in_row  # 0..pi
            points_x.append(radius * math.cos(angle))
            points_y.append(radius * math.sin(angle))
            party = seat_list[idx]
            colors.append(party_color(party))
            texts.append(party)
            idx += 1

    fig = go.Figure(
        go.Scatter(
            x=points_x,
            y=points_y,
            mode="markers",
            marker=dict(size=9, color=colors, line=dict(width=0)),
            text=texts,
            hovertemplate="%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis=dict(visible=False, scaleanchor="y", range=[-1.15, 1.15]),
        yaxis=dict(visible=False, range=[-0.1, 1.2]),
        height=380,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
        annotations=[
            dict(
                text="<br>".join(f"<b>{n}</b>: {s}" for n, s in items),
                x=1.02,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                align="left",
                font=dict(size=12),
            )
        ],
    )
    return fig


def seats_bar_figure(seats: Mapping[str, int]) -> go.Figure:
    items = sorted(((k, v) for k, v in seats.items() if v > 0), key=lambda kv: -kv[1])
    fig = go.Figure(
        go.Bar(
            x=[k for k, _ in items],
            y=[v for _, v in items],
            marker_color=[party_color(k) for k, _ in items],
            text=[v for _, v in items],
            textposition="outside",
        )
    )
    fig.update_layout(height=320, yaxis_title="Sitze", margin=dict(l=40, r=20, t=30, b=40))
    return fig


# Länderschwerpunkte für Europa-Karte (Näherung)
COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "DE": (51.16, 10.45),
    "AT": (47.52, 14.55),
    "FR": (46.23, 2.21),
    "IT": (41.87, 12.57),
    "ES": (40.46, -3.75),
    "NL": (52.13, 5.29),
    "PL": (51.92, 19.15),
    "SE": (60.13, 18.64),
    "PT": (39.40, -8.22),
    "BE": (50.50, 4.47),
}


FAMILY_COLORS: dict[str, list[int]] = {
    "EPP": [0, 51, 153],
    "S&D": [230, 0, 35],
    "Renew": [255, 204, 0],
    "Greens/EFA": [100, 161, 45],
    "ECR": [0, 80, 160],
    "ID": [0, 158, 224],
    "Left": [190, 48, 117],
    "NI": [140, 140, 140],
}


def europe_family_deck(rows: list[dict]) -> pdk.Deck:
    """
    rows: dicts with country, lat, lon, family, label, share
    """
    data = []
    for r in rows:
        rgb = FAMILY_COLORS.get(r.get("family", "NI"), [120, 120, 120])
        data.append(
            {
                **r,
                "color": rgb + [200],
                "radius": 120000 + 4000 * float(r.get("share", 0)),
            }
        )
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius="radius",
        pickable=True,
    )
    view = pdk.ViewState(latitude=50.0, longitude=10.0, zoom=3.2)
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip={"text": "{country}\n{label}\n{family}: {share}%"},
        map_style=None,
    )
