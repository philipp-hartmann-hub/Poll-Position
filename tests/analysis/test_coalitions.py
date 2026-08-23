from analysis.coalitions import has_majority, majority_coalitions


def test_has_majority_strict():
    seats = {"A": 50, "B": 50}
    assert has_majority(seats, ["A", "B"]) is True
    assert has_majority(seats, ["A"]) is False


def test_majority_coalitions_finds_pairs():
    seats = {"A": 40, "B": 35, "C": 25}
    combos = majority_coalitions(seats, max_parties=2)
    assert ("A", "B") in combos
    assert ("A",) not in combos
