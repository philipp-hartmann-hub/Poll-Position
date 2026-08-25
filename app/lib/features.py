"""Produkt-Feature-Flags (Streamlit).

Europa vorerst aus — Seite bleibt unter pages/, wird nur nicht verlinkt.
Wieder aktivieren: ENABLE_EUROPE=1 in der Umgebung oder europe=True unten.
"""

from __future__ import annotations

import os

features = {
    "europe": os.environ.get("ENABLE_EUROPE", "").strip().lower() in {"1", "true", "yes"},
}
