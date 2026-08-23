"""Tests für analysis.seats — gespiegelt zur Paketstruktur."""

from analysis.seats.sainte_lague import allocate_sainte_lague


def test_sainte_lague_equal_split():
    seats = allocate_sainte_lague({"A": 50, "B": 50}, seats=10)
    assert seats["A"] == 5
    assert seats["B"] == 5


def test_sainte_lague_threshold_excludes_small_party():
    seats = allocate_sainte_lague(
        {"A": 48, "B": 48, "C": 4},
        seats=100,
        threshold=0.05,
    )
    assert seats["C"] == 0
    assert seats["A"] + seats["B"] == 100


def test_sainte_lague_known_toy_result():
    """Bekanntes Mini-Beispiel: 3 Parteien, 7 Sitze."""
    seats = allocate_sainte_lague({"A": 53000, "B": 25000, "C": 22000}, seats=7)
    assert seats == {"A": 4, "B": 2, "C": 1}
