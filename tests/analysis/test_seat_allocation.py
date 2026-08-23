"""
Regressionstests gegen echte Wahlergebnisse.

Quellen:
- BTW 2025: Die Bundeswahlleiterin (endgültiges Ergebnis)
- Saarland 2022: Landeswahlleiterin Saarland (d’Hondt, 51 Sitze)
- Thüringen 2024: Landeswahlleiter Thüringen / Bundeswahlleiterin (Hare/Niemeyer, 88 Sitze)
"""

from __future__ import annotations

import pytest

from analysis.seat_allocation import (
    BundestagAllocationResult,
    allocate_seats,
    bundestag_seat_allocation,
    dhondt,
    hare_niemeyer,
    sainte_lague_schepers,
)
from data_pipeline.schema import AllocationMethod, ElectionSystem, load_parliament_config

# --- Amtliche Stimmen / Sitze ---

# Bundestagswahl 2025 — Zweitstimmen (endgültig), gültige Zweitstimmen gesamt: 49_649_512
# Sitze: CDU 164, AfD 152, SPD 120, Grüne 85, Linke 64, CSU 44, SSW 1 (= 630)
BTW_2025_VOTES: dict[str, float] = {
    "CDU": 11_196_374,
    "AfD": 10_328_780,
    "SPD": 8_149_124,
    "GRUENE": 5_762_380,
    "LINKE": 4_356_532,
    "CSU": 2_964_028,
    "SSW": 76_138,
    "FDP": 2_148_757,
    "BSW": 2_472_947,
    "FREIE_WAEHLER": 769_279,
    "Tierschutz": 482_201,
    "Volt": 355_262,
    "DiePARTEI": 242_741,
    "Sonst_klein": 49_649_512
    - (
        11_196_374
        + 10_328_780
        + 8_149_124
        + 5_762_380
        + 4_356_532
        + 2_964_028
        + 76_138
        + 2_148_757
        + 2_472_947
        + 769_279
        + 482_201
        + 355_262
        + 242_741
    ),
}
BTW_2025_SEATS = {
    "CDU": 164,
    "AfD": 152,
    "SPD": 120,
    "GRUENE": 85,
    "LINKE": 64,
    "CSU": 44,
    "SSW": 1,
}
BTW_2025_TOTAL = 49_649_512

# Saarland LTW 2022 — gültige Stimmen 452_411; Sitze SPD 29, CDU 19, AfD 3
SAARLAND_2022_VOTES: dict[str, float] = {
    "SPD": 196_801,
    "CDU": 129_154,
    "AfD": 25_719,
    "GRUENE": 22_598,
    "FDP": 21_618,
    "LINKE": 11_689,
    "Tierschutz": 10_391,
    "FW": 7_636,
    "dieBasis": 6_448,
    "bunt": 6_216,
    "PARTEI": 4_716,
    "FAMILIE": 3_836,
    "Volt": 2_645,
    "PIRATEN": 1_318,
    "OEDP": 613,
    "SGV": 412,
    "Gesundheit": 368,
    "Humanisten": 233,
}
SAARLAND_2022_SEATS = {"SPD": 29, "CDU": 19, "AfD": 3}
SAARLAND_2022_TOTAL = 452_411

# Thüringen LTW 2024 — Landesstimmen; Sitze AfD 32, CDU 23, BSW 15, Linke 12, SPD 6
THURINGEN_2024_VOTES: dict[str, float] = {
    "AfD": 396_711,
    "CDU": 285_097,
    "BSW": 190_664,
    "LINKE": 157_689,
    "SPD": 73_126,
    "GRUENE": 38_275,
    "FW": 15_385,
    "FDP": 13_591,
    "TIERSCHUTZ": 12_112,
    "WU": 6_778,
    "FAMILIE": 5_709,
    "BD": 5_309,
    "PIRATEN": 3_721,
    "OEDP": 2_389,
    "MLPD": 1_327,
}
THURINGEN_2024_SEATS = {"AfD": 32, "CDU": 23, "BSW": 15, "LINKE": 12, "SPD": 6}
THURINGEN_2024_TOTAL = 1_207_883


def test_sainte_lague_bundestag_2025_official_seats():
    result = sainte_lague_schepers(
        BTW_2025_VOTES,
        630,
        threshold=0.05,
        total_votes=BTW_2025_TOTAL,
        exempt_party_ids=("SSW",),
    )
    for party, seats in BTW_2025_SEATS.items():
        assert result[party] == seats, f"{party}: {result[party]} != {seats}"
    assert sum(result.values()) == 630
    assert result["FDP"] == 0
    assert result["BSW"] == 0


def test_bundestag_seat_allocation_matches_2025_oberverteilung():
    result = bundestag_seat_allocation(
        BTW_2025_VOTES,
        seats=630,
        threshold=0.05,
        minority_party_ids=("SSW",),
        total_votes=BTW_2025_TOTAL,
    )
    assert isinstance(result, BundestagAllocationResult)
    for party, seats in BTW_2025_SEATS.items():
        assert result.party_seats[party] == seats
    assert sum(result.party_seats.values()) == 630


def test_bundestag_zweitstimmendeckung_caps_direct_seats():
    """
    Illustration Zweitstimmendeckung: Partei hat in Land X 2 Zweitstimmen-Sitze,
    aber 4 Wahlkreissiege → nur 2 Direktmandate werden gedeckt.
    """
    national = {"A": 60.0, "B": 40.0}
    land_votes = {
        "Land1": {"A": 30.0, "B": 20.0},
        "Land2": {"A": 30.0, "B": 20.0},
    }
    # künstlich: A gewinnt 3 WK in Land1
    land_wins = {"Land1": {"A": 3, "B": 0}, "Land2": {"A": 0, "B": 1}}
    result = bundestag_seat_allocation(
        national,
        seats=10,
        threshold=0.0,
        land_votes=land_votes,
        land_direct_wins=land_wins,
    )
    assert sum(result.party_seats.values()) == 10
    assert "Land1" in result.land_party_seats
    a_quota_l1 = result.land_party_seats["Land1"].get("A", 0)
    assert result.capped_direct_seats["Land1"]["A"] == min(3, a_quota_l1)
    assert result.capped_direct_seats["Land1"]["A"] <= a_quota_l1


def test_dhondt_saarland_2022_official_seats():
    result = dhondt(
        SAARLAND_2022_VOTES,
        51,
        threshold=0.05,
        total_votes=SAARLAND_2022_TOTAL,
    )
    for party, seats in SAARLAND_2022_SEATS.items():
        assert result[party] == seats
    assert sum(result.values()) == 51
    assert result["GRUENE"] == 0  # 4,995 % < 5 %


def test_hare_niemeyer_thueringen_2024_official_seats():
    result = hare_niemeyer(
        THURINGEN_2024_VOTES,
        88,
        threshold=0.05,
        total_votes=THURINGEN_2024_TOTAL,
    )
    for party, seats in THURINGEN_2024_SEATS.items():
        assert result[party] == seats
    assert sum(result.values()) == 88
    assert result["GRUENE"] == 0


def test_threshold_does_not_rescale_remaining_shares():
    """
    Ausgeschlossene Stimmen werden nicht umverteilt: bei gleicher Relation der
    großen Parteien bleibt die Sitzrelation zur Variante ohne Kleinstpartei-Stimme
    nicht identisch zur „Hochskalierung auf 100 %“, aber Kleinstpartei hat 0 Sitze.
    """
    votes = {"A": 48.0, "B": 47.0, "C": 5.0}
    with_c = sainte_lague_schepers(votes, 100, threshold=0.06)
    assert with_c["C"] == 0
    assert with_c["A"] + with_c["B"] == 100


def test_allocate_seats_dispatch_bundestag_config():
    bundle = load_parliament_config()
    bt = next(p for p in bundle.parliaments if p.id == "de_bundestag")
    system = next(s for s in bundle.election_systems if s.key == bt.election_system_key)
    seats = allocate_seats(
        bt,
        BTW_2025_VOTES,
        election_system=system,
        total_votes=BTW_2025_TOTAL,
        # SSW-ID in Config ist de:ssw — Stimmen-Key hier "SSW"
    )
    # minority_exempt in YAML: [] — SSW braucht Exemption; daher explizit mit System-Kopie
    system_ssw = ElectionSystem(
        key=system.key,
        allocation_method=system.allocation_method,
        threshold_percent=system.threshold_percent,
        seats_total=system.seats_total,
        zweitstimmendeckung=True,
        direct_seats=system.direct_seats,
        grundmandat_seats=system.grundmandat_seats,
        minority_exempt_party_ids=["SSW"],
    )
    seats = allocate_seats(
        bt,
        BTW_2025_VOTES,
        election_system=system_ssw,
        total_votes=BTW_2025_TOTAL,
    )
    assert seats["CDU"] == 164
    assert seats["SSW"] == 1
    assert sum(seats.values()) == 630


def test_allocate_seats_dispatch_saarland_dhondt():
    bundle = load_parliament_config()
    system = next(s for s in bundle.election_systems if s.key == "de_sl_lt")
    assert system.allocation_method == AllocationMethod.DHONDT
    seats = allocate_seats(system, SAARLAND_2022_VOTES, total_votes=SAARLAND_2022_TOTAL)
    assert seats["SPD"] == 29
    assert seats["CDU"] == 19
    assert seats["AfD"] == 3


def test_allocate_seats_dispatch_thueringen_hare():
    bundle = load_parliament_config()
    system = next(s for s in bundle.election_systems if s.key == "de_th_lt")
    assert system.allocation_method == AllocationMethod.HARE_NIEMEYER
    seats = allocate_seats(system, THURINGEN_2024_VOTES, total_votes=THURINGEN_2024_TOTAL)
    assert seats["AfD"] == 32
    assert seats["CDU"] == 23
    assert seats["BSW"] == 15
