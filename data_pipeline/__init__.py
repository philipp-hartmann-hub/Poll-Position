"""ETL: Quellen einlesen, normalisieren, nach DuckDB/Parquet schreiben."""

from data_pipeline.schema_bridge import observations_to_frame

__all__ = ["observations_to_frame"]
