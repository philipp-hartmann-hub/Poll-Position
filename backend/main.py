"""
FastAPI-Einstieg für Vercel: `backend.main:app`

Lokal: `uv run uvicorn backend.main:app --reload`
OpenAPI: `/docs`
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query

from backend import schemas, services

app = FastAPI(
    title="Poll-Position API",
    version="0.1.0",
    description="JSON-API über analysis/ (Sitzverteilung, Koalitionen, Unsicherheit, …).",
)

# CORS nur bei explizitem Opt-in (separates Frontend-Origin).
# Empfohlen: Next.js + API im selben Vercel-Projekt → kein CORS nötig.
if os.environ.get("ENABLE_CORS", "").strip().lower() in {"1", "true", "yes"}:
    from fastapi.middleware.cors import CORSMiddleware

    origins = [
        o.strip()
        for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health() -> dict:
    """
    Diagnose ohne Secrets: Token gesetzt? MotherDuck erreichbar? Daten vorhanden?

    Nach Marketplace-Connect ist die DB oft noch leer — erst Daily Pipeline /
    `python -m data_pipeline.run` mit Token füllt Silver/Gold.
    """
    from data_pipeline.warehouse import (
        connect_warehouse,
        motherduck_database,
        uses_motherduck,
        warehouse_connection_target,
    )

    info: dict = {
        "status": "ok",
        "motherduck_configured": uses_motherduck(),
        "warehouse_target": warehouse_connection_target(),
        "database": motherduck_database() if uses_motherduck() else None,
        "vercel": bool(os.environ.get("VERCEL")),
    }
    try:
        # Kein ensure_warehouse: Read-Only-Token darf kein CREATE.
        con = connect_warehouse(read_only=not uses_motherduck())
        try:
            tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            info["tables"] = sorted(tables)
            if "surveys" in tables:
                info["surveys"] = int(con.execute("SELECT COUNT(*) FROM surveys").fetchone()[0])
            if "survey_results" in tables:
                info["survey_results"] = int(
                    con.execute("SELECT COUNT(*) FROM survey_results").fetchone()[0]
                )
            if "party_averages" in tables:
                info["party_averages"] = int(
                    con.execute("SELECT COUNT(*) FROM party_averages").fetchone()[0]
                )
        finally:
            con.close()
        if uses_motherduck() and info.get("surveys", 0) == 0:
            info["hint"] = (
                "MotherDuck verbunden, aber noch keine Surveys. "
                "GitHub Action Daily Pipeline einmal manuell starten "
                "(Secret MOTHERDUCK_TOKEN setzen) oder lokal: "
                "MOTHERDUCK_TOKEN=… uv run python -m data_pipeline.run"
            )
    except Exception as exc:  # noqa: BLE001 — Diagnose an Client
        info["status"] = "degraded"
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


@app.get("/api/parliaments", response_model=list[schemas.ParliamentOut])
def get_parliaments() -> list[schemas.ParliamentOut]:
    return [schemas.ParliamentOut.model_validate(r) for r in services.list_parliaments()]


@app.get("/api/parties/averages", response_model=schemas.AveragesResponse)
def get_party_averages(
    parliament_id: str = Query(..., description="z. B. de_bundestag"),
    days: int = Query(365, ge=7, le=2000),
) -> schemas.AveragesResponse:
    return schemas.AveragesResponse.model_validate(
        services.party_averages_payload(parliament_id, days=days)
    )


@app.get("/api/seats", response_model=schemas.SeatsResponse)
def get_seats(
    parliament_id: str = Query(..., description="z. B. de_bundestag"),
) -> schemas.SeatsResponse:
    data = services.seats_payload(parliament_id)
    if not data["seats"]:
        raise HTTPException(status_code=404, detail="Keine Umfragedaten / Sitze")
    return schemas.SeatsResponse.model_validate(data)


@app.get("/api/coalitions", response_model=schemas.CoalitionsResponse)
def get_coalitions(
    parliament_id: str = Query(...),
    apply_exclusions: bool = Query(True),
    max_parties: int = Query(4, ge=1, le=6),
) -> schemas.CoalitionsResponse:
    data = services.coalitions_payload(
        parliament_id,
        apply_exclusions=apply_exclusions,
        max_parties=max_parties,
    )
    if data["total_seats"] <= 0:
        raise HTTPException(status_code=404, detail="Keine Sitzdaten")
    return schemas.CoalitionsResponse.model_validate(data)


@app.get("/api/uncertainty", response_model=schemas.UncertaintyResponse)
def get_uncertainty(
    parliament_id: str = Query(...),
    n_simulations: int = Query(400, ge=50, le=5000),
) -> schemas.UncertaintyResponse:
    data = services.uncertainty_payload(parliament_id, n_simulations=n_simulations)
    if data["n_simulations"] == 0 and not data["mean_seats"]:
        raise HTTPException(status_code=404, detail="Keine Daten für Unsicherheit")
    return schemas.UncertaintyResponse.model_validate(data)


@app.get("/api/institutes/house-effects", response_model=schemas.HouseEffectsResponse)
def get_house_effects(
    parliament_id: str | None = Query(None),
    window_days: int = Query(14, ge=1, le=90),
) -> schemas.HouseEffectsResponse:
    return schemas.HouseEffectsResponse.model_validate(
        services.house_effects_payload(parliament_id, window_days=window_days)
    )


@app.get("/api/europe/overview", response_model=schemas.EuropeOverviewResponse)
def get_europe_overview() -> schemas.EuropeOverviewResponse:
    return schemas.EuropeOverviewResponse.model_validate(
        services.europe_overview_payload()
    )


@app.post("/api/scenario", response_model=schemas.ScenarioResponse)
def post_scenario(body: schemas.ScenarioRequest) -> schemas.ScenarioResponse:
    try:
        data = services.scenario_payload(
            body.parliament_id,
            body.party_shares,
            apply_exclusions=body.apply_exclusions,
            max_coalition_parties=body.max_coalition_parties,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.ScenarioResponse.model_validate(data)
