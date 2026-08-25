"""Statische JSON-Exports für das Next.js-Frontend (kein Function-Cold-Start).

Schreibt unter ``web/public/data/``:
- ``parliaments.json`` (Index)
- ``<parliament_id>/{averages,trend,seats,coalitions}.json``

Diese Dateien gehören NICHT ins Git — sie entstehen beim Pipeline-Lauf.

Auslieferung in Produktion (Kurzfazit):
- Vercel Blob: aus GHA mit ``BLOB_READ_WRITE_TOKEN`` machbar, Frontend müsste
  Blob-URLs nutzen (zusätzliche Konfiguration).
- Deploy-Hook / ``vercel deploy`` nach Export: bringt Dateien als ``public/``
  in ein neues Deployment, braucht aber ``VERCEL_TOKEN`` und einen vollen
  Rebuild — schwerer als nötig, solange die Function noch warm gehalten wird.
- Zwischenlösung: Warm-Ping-Cron (``.github/workflows/warm-ping.yml``) hält
  ``/health`` warm; Static-Fallback greift, sobald die JSONs per Deploy/Blob
  erreichbar sind. Lokal: fehlende Dateien → 404 → API-Fallback.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("data_pipeline.export_static")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "web" / "public" / "data"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Nicht JSON-serialisierbar: {type(obj)!r}")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )


def export_parliament_static(
    parliament_id: str,
    *,
    out_dir: Path,
) -> dict[str, bool]:
    """Exportiert die vier Standard-Payloads für ein Parlament. Rückgabe: ok je Datei."""
    from backend import services

    results: dict[str, bool] = {}
    writers: list[tuple[str, Any]] = [
        ("averages", lambda: services.party_averages_payload(parliament_id, days=365)),
        ("trend", lambda: services.party_trend_series_payload(parliament_id, days=365)),
        ("seats", lambda: services.seats_payload(parliament_id)),
        (
            "coalitions",
            lambda: services.coalitions_payload(
                parliament_id,
                apply_exclusions=True,
                disabled_rule_ids=None,
            ),
        ),
    ]
    for name, factory in writers:
        dest = out_dir / parliament_id / f"{name}.json"
        try:
            payload = factory()
            _write_json(dest, payload)
            results[name] = True
        except Exception:
            log.exception("Export %s/%s fehlgeschlagen", parliament_id, name)
            results[name] = False
    return results


def export_all_static(*, out_dir: Path | None = None) -> int:
    """
    Exportiert alle Parlamente. Rückgabe: Anzahl erfolgreich geschriebener Dateien.
    """
    from backend import services

    target = out_dir or DEFAULT_OUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    parliaments = services.list_parliaments()
    written = 0

    index_path = target / "parliaments.json"
    try:
        _write_json(index_path, parliaments)
        written += 1
        log.info("Static-Export parliaments.json: ok (%d Einträge)", len(parliaments))
    except Exception:
        log.exception("Export parliaments.json fehlgeschlagen")

    for row in parliaments:
        pid = str(row["id"])
        ok = export_parliament_static(pid, out_dir=target)
        written += sum(1 for v in ok.values() if v)
        log.info(
            "Static-Export %s: %s",
            pid,
            ", ".join(f"{k}={'ok' if v else 'fail'}" for k, v in ok.items()),
        )
    log.info(
        "Static-Export fertig: %d Dateien unter %s (%d Parlamente)",
        written,
        target,
        len(parliaments),
    )
    return written
