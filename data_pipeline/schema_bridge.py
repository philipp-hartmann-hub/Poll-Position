"""Konvertierung vom einheitlichen Schema in tabellarische Form (Polars)."""

from __future__ import annotations

import polars as pl

from analysis.schema import PollObservation


def observations_to_frame(observations: list[PollObservation]) -> pl.DataFrame:
    """Eine Zeile pro Partei-Ergebnis (denormalisiert für Bronze-Parquet)."""
    rows: list[dict] = []
    for obs in observations:
        base = {
            "source": obs.source,
            "pollster": obs.pollster,
            "published": obs.published,
            "fieldwork_start": obs.fieldwork_start,
            "fieldwork_end": obs.fieldwork_end,
            "country": obs.country.value,
            "region": obs.region,
            "election_type": obs.election_type.value,
            "sample_size": obs.sample_size,
            "methodology": obs.methodology,
            "scope_label": obs.scope_label,
            "source_url": obs.source_url,
            "retrieved_at": obs.retrieved_at,
            "raw_id": obs.raw_id,
        }
        for result in obs.results:
            rows.append(
                {
                    **base,
                    "party": result.party,
                    "share": result.share,
                    "seats_hint": result.seats_hint,
                }
            )
    if not rows:
        return pl.DataFrame(
            schema={
                "source": pl.Utf8,
                "pollster": pl.Utf8,
                "published": pl.Date,
                "fieldwork_start": pl.Date,
                "fieldwork_end": pl.Date,
                "country": pl.Utf8,
                "region": pl.Utf8,
                "election_type": pl.Utf8,
                "sample_size": pl.Int64,
                "methodology": pl.Utf8,
                "scope_label": pl.Utf8,
                "source_url": pl.Utf8,
                "retrieved_at": pl.Datetime,
                "raw_id": pl.Utf8,
                "party": pl.Utf8,
                "share": pl.Float64,
                "seats_hint": pl.Int64,
            }
        )
    return pl.DataFrame(rows)
