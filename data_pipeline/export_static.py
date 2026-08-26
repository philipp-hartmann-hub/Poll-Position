"""Statische JSON-Exports für das Next.js-Frontend (kein Function-Cold-Start).

Schreibt unter ``web/public/data/``:
- ``parliaments.json`` (Index)
- optional ``germany-map-leaders.json`` (wenn Service vorhanden)
- ``<safe_parliament_id>/{averages,trend,seats,coalitions}.json``

Parliament-IDs mit ``:`` (z. B. ``dawum:parliament:17``) werden für den
Pfad segmentiert (``dawum_parliament_17``), damit Artifact-Upload und NTFS
keine ungültigen Zeichen sehen. Die ID im JSON-Inhalt bleibt unverändert.

Alt-Verzeichnisse mit ungültigen Zeichen werden beim Export entfernt.

Diese Dateien entstehen beim Pipeline-Lauf und werden von der Daily Pipeline
nach ``main`` committed ([skip ci]), damit Vercel sie als ``public/data/``
ausliefert. Lokal ohne Export: 404 → API-Fallback.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("data_pipeline.export_static")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "web" / "public" / "data"

# upload-artifact / NTFS-agnostisch: keine :, ", <, >, |, *, ?, CR, LF
_UNSAFE_PATH_CHARS = re.compile(r'[":<>|*?\r\n\\/]')


def static_path_segment(parliament_id: str) -> str:
    """Filesystem-/Artifact-sicheres Verzeichnis für eine Parliament-ID."""
    return _UNSAFE_PATH_CHARS.sub("_", parliament_id)


def _purge_unsafe_dirs(out_dir: Path) -> None:
    """Entfernt Alt-Exports mit artifact-ungültigen Verzeichnisnamen (z. B. ``:``)."""
    if not out_dir.is_dir():
        return
    for child in list(out_dir.iterdir()):
        if child.is_dir() and _UNSAFE_PATH_CHARS.search(child.name):
            log.warning(
                "Entferne artifact-ungültiges Static-Verzeichnis: %s", child.name
            )
            shutil.rmtree(child)


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
    segment = static_path_segment(parliament_id)
    for name, factory in writers:
        dest = out_dir / segment / f"{name}.json"
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
    _purge_unsafe_dirs(target)
    parliaments = services.list_parliaments()
    written = 0

    index_path = target / "parliaments.json"
    try:
        _write_json(index_path, parliaments)
        written += 1
        log.info("Static-Export parliaments.json: ok (%d Einträge)", len(parliaments))
    except Exception:
        log.exception("Export parliaments.json fehlgeschlagen")

    map_fn = getattr(services, "germany_map_leaders_payload", None)
    if callable(map_fn):
        map_path = target / "germany-map-leaders.json"
        try:
            _write_json(map_path, map_fn())
            written += 1
            log.info("Static-Export germany-map-leaders.json: ok")
        except Exception:
            log.exception("Export germany-map-leaders.json fehlgeschlagen")

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
