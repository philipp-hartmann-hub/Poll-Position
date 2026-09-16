"""Regressionstests Wahlabend: Sperrklausel-Nenner inkl. implizitem Sonstige."""

from __future__ import annotations

import pytest

# BTW 2025 — Anteile wie im Wahlabend-Formular (ohne Sonstige; Summe 95,52 %)
BTW_2025_ELECTION_NIGHT_SHARES = {
    "de:cdu_csu": 28.52,
    "de:afd": 20.8,
    "de:spd": 16.4,
    "de:gruene": 11.6,
    "de:linke": 8.8,
    "de:fdp": 4.3,
    "de:bsw": 4.9,
    "de:ssw": 0.2,
}

_NAMES = {
    "de:cdu_csu": "CDU/CSU",
    "de:afd": "AfD",
    "de:spd": "SPD",
    "de:gruene": "Grüne",
    "de:linke": "Linke",
    "de:fdp": "FDP",
    "de:bsw": "BSW",
    "de:ssw": "SSW",
    "de:sonstige": "Sonstige",
}


@pytest.fixture
def election_night_names(monkeypatch):
    """Kanonische Namen, damit Sitze/Koalitionen ohne Umfrage-Warehouse-IDs laufen."""
    from backend import services

    monkeypatch.setattr(services, "_votes_from_averages", lambda _pid: ({}, _NAMES))
    services.clear_payload_caches()
    return _NAMES


def test_election_night_btw_2025_threshold_uses_full_denominator(
    election_night_names,
):
    """
    Ohne Rest zu 100 % würde BSW (4,9 % von 95,52 %) fälschlich über 5 % rutschen
    und CDU/CSU+SPD unter die Mehrheit fallen — Regression gegen BTW-2025-Anteile.
    """
    from backend import services

    payload = services.election_night_payload(
        "de_bundestag",
        BTW_2025_ELECTION_NIGHT_SHARES,
        n_simulations=50,
        apply_exclusions=True,
    )

    seats = payload["seats"]["seats"]
    assert "de:bsw" not in seats
    assert "de:fdp" not in seats
    assert seats.get("de:ssw", 0) >= 1  # Minderheiten-Exemption
    assert int(payload["seats"]["total_seats"] or 0) == 630

    union_spd = [
        c
        for c in payload["coalitions"]["coalitions"]
        if set(c["parties"]) == {"de:cdu_csu", "de:spd"}
    ]
    assert union_spd, "CDU/CSU+SPD fehlt in der Koalitionsliste"
    assert union_spd[0]["seats"] >= 316


def test_seats_from_votes_payload_adds_implicit_residual(election_night_names):
    from backend import services

    data = services.seats_from_votes_payload(
        "de_bundestag",
        BTW_2025_ELECTION_NIGHT_SHARES,
        election_night_names,
    )
    assert "de:bsw" not in data["seats"]
    assert "de:fdp" not in data["seats"]
    assert "de:sonstige" not in data["seats"]
    assert data["seats"].get("de:cdu_csu", 0) + data["seats"].get("de:spd", 0) >= 316
