from datetime import date

from analysis.schema import CountryCode, ElectionType, PartyResult, PollObservation


def test_poll_observation_accepts_valid_payload():
    obs = PollObservation(
        source="dawum",
        pollster="Forschungsgruppe Wahlen",
        published=date(2024, 1, 15),
        country=CountryCode.DE,
        election_type=ElectionType.BUNDESTAG,
        results=[
            PartyResult(party="CDU/CSU", share=32.0),
            PartyResult(party="SPD", share=16.0),
        ],
    )
    assert obs.source == "dawum"
    assert len(obs.results) == 2
