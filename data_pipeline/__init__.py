"""ETL: Quellen einlesen, normalisieren, nach DuckDB/Parquet schreiben."""

from data_pipeline.schema import (
    SONSTIGE_PARTY_ID,
    Country,
    ElectionSystem,
    Level,
    Parliament,
    Party,
    Pollster,
    Survey,
    load_parliament_config,
)
from data_pipeline.schema_bridge import observations_to_frame

__all__ = [
    "SONSTIGE_PARTY_ID",
    "Country",
    "ElectionSystem",
    "Level",
    "Parliament",
    "Party",
    "Pollster",
    "Survey",
    "load_parliament_config",
    "observations_to_frame",
]
