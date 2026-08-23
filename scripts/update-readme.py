#!/usr/bin/env python3
"""Aktualisiert die Auto-Abschnitte in README.md anhand des Projektzustands."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

IGNORE_DIRS = {
    ".git",
    ".cursor",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "coverage",
    ".turbo",
}

MARKER_RE = re.compile(
    r"(<!--\s*AUTO:START:(\w+)\s*-->)(.*?)(<!--\s*AUTO:END:\2\s*-->)",
    re.DOTALL,
)


def now_stamp() -> str:
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def list_tree(max_entries: int = 80) -> list[str]:
    entries: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if rel.name == "README.md":
            continue
        entries.append(str(rel))
        if len(entries) >= max_entries:
            entries.append("… (weitere Dateien ausgeblendet)")
            break
    return entries


def detect_stack() -> list[str]:
    hints: list[str] = []
    mapping = {
        "package.json": "Node.js / npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "Yarn",
        "bun.lockb": "Bun",
        "requirements.txt": "Python (pip)",
        "pyproject.toml": "Python (pyproject)",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "composer.json": "PHP (Composer)",
        "Gemfile": "Ruby",
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose",
    }
    for name, label in mapping.items():
        if (ROOT / name).exists():
            hints.append(label)
    return hints


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def git_info() -> dict[str, str]:
    info = {
        "branch": "—",
        "commits": "0",
        "status": "kein Git",
        "remote": "—",
    }
    if not (ROOT / ".git").exists():
        return info
    try:
        try:
            remote = _git("remote", "get-url", "origin")
        except subprocess.CalledProcessError:
            remote = "—"
        try:
            branch = _git("branch", "--show-current") or _git(
                "symbolic-ref", "--short", "HEAD"
            )
        except subprocess.CalledProcessError:
            branch = "main"
        try:
            commits = _git("rev-list", "--count", "HEAD")
        except subprocess.CalledProcessError:
            commits = "0"
        dirty = _git("status", "--porcelain")
        info = {
            "branch": branch or "—",
            "commits": commits or "0",
            "status": (
                "Arbeitsbaum unsauber"
                if dirty
                else ("sauber" if commits != "0" else "noch kein Commit")
            ),
            "remote": remote,
        }
    except subprocess.CalledProcessError:
        info["status"] = "Git vorhanden (noch kein Commit)"
    return info


def count_by_extension(files: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rel in files:
        if rel.startswith("…"):
            continue
        ext = Path(rel).suffix.lower() or "(ohne Endung)"
        counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def section_meta() -> str:
    return (
        f"_Zuletzt automatisch aktualisiert: **{now_stamp()}**_\n\n"
        "Diese Abschnitte werden von `scripts/update-readme.py` gepflegt "
        "(Cursor-Hook nach jeder Agent-Session + manueller Aufruf)."
    )


def section_overview() -> str:
    files = list_tree()
    stack = detect_stack()
    git = git_info()
    stack_line = ", ".join(stack) if stack else "noch nicht erkannt (Projekt startet)"
    return "\n".join(
        [
            f"- **Repo:** [Poll-Position](https://github.com/philipp-hartmann-hub/Poll-Position)",
            f"- **Remote:** `{git['remote']}`",
            f"- **Projektroot:** `{ROOT.name}`",
            f"- **Dateien (sichtbar):** {len([f for f in files if not f.startswith('…')])}",
            f"- **Stack-Hinweise:** {stack_line}",
            f"- **Git-Branch:** `{git['branch']}` · Commits: {git['commits']} · Status: {git['status']}",
        ]
    )


def section_structure() -> str:
    files = list_tree()
    if not files:
        return "_Noch keine Projektdateien außer der README. Struktur füllt sich automatisch._"
    lines = ["```text"]
    lines.extend(files)
    lines.append("```")
    return "\n".join(lines)


def section_languages() -> str:
    files = [f for f in list_tree() if not f.startswith("…")]
    counts = count_by_extension(files)
    if not counts:
        return "_Noch keine Quellcode-Dateien erkannt._"
    rows = ["| Endung | Anzahl |", "| --- | ---: |"]
    for ext, count in counts.items():
        rows.append(f"| `{ext}` | {count} |")
    return "\n".join(rows)


def section_howto() -> str:
    return "\n".join(
        [
            "```bash",
            "python3 scripts/update-readme.py",
            "```",
            "",
            "Der Cursor-Hook `.cursor/hooks/update-readme.sh` ruft dasselbe Skript",
            "am Ende jeder Agent-Session (`stop`) auf.",
        ]
    )


SECTIONS = {
    "meta": section_meta,
    "overview": section_overview,
    "structure": section_structure,
    "languages": section_languages,
    "howto": section_howto,
}


TEMPLATE = """# Poll-Position

Umfragetracker für Deutschland und Europa.

Ziel: Umfragen aus **Dawum** und paneuropäischen Quellen zusammenführen, daraus
**Sitzverteilung** und **Koalitionsszenarien** berechnen. Die Analyse-Logik liegt
UI-frei in `analysis/` und wird mit pytest abgesichert.

> Manuelle Abschnitte (dieser Intro und die Architektur/Start-Anleitung) bleiben erhalten.
> Alles zwischen `AUTO:START` / `AUTO:END` wird automatisch überschrieben.

## Datenarchitektur (Bronze / Silver / Gold)

| Layer | Ort | Inhalt |
| --- | --- | --- |
| **Bronze** | `data/raw/<quelle>/<YYYY-MM-DD>.parquet` | Roh-Snapshots je Quelle und Abrufdatum, bereits im einheitlichen Beobachtungsschema |
| **Silver** | `data/warehouse.duckdb` → u. a. `polls_silver` | Vereinheitlichte, bereinigte Umfragezeilen |
| **Gold** | `data/warehouse.duckdb` (aggregierte Tabellen, folgen) | Auswertungsfertige Kennzahlen, Sitze, Koalitionen |

## Start

```bash
# Abhängigkeiten (uv)
uv sync

# Pipeline (ETL → Parquet + DuckDB)
uv run python -m data_pipeline.run

# Streamlit-App
uv run streamlit run app/Home.py

# Tests
uv run pytest
```

## Status

<!-- AUTO:START:meta -->
<!-- AUTO:END:meta -->

## Überblick

<!-- AUTO:START:overview -->
<!-- AUTO:END:overview -->

## Projektstruktur

<!-- AUTO:START:structure -->
<!-- AUTO:END:structure -->

## Dateitypen

<!-- AUTO:START:languages -->
<!-- AUTO:END:languages -->

## README aktualisieren

<!-- AUTO:START:howto -->
<!-- AUTO:END:howto -->
"""


def ensure_readme() -> str:
    if README.exists():
        return README.read_text(encoding="utf-8")
    README.write_text(TEMPLATE, encoding="utf-8")
    return TEMPLATE


def replace_section(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!--\s*AUTO:START:{name}\s*-->)(.*?)(<!--\s*AUTO:END:{name}\s*-->)",
        re.DOTALL,
    )
    replacement = rf"\1\n{body.strip()}\n\3"
    if not pattern.search(text):
        # Marker fehlen: Abschnitt am Ende anhängen
        block = (
            f"\n\n## {name.capitalize()}\n\n"
            f"<!-- AUTO:START:{name} -->\n{body.strip()}\n<!-- AUTO:END:{name} -->\n"
        )
        return text.rstrip() + block
    return pattern.sub(replacement, text, count=1)


def update() -> dict:
    text = ensure_readme()
    for name, builder in SECTIONS.items():
        text = replace_section(text, name, builder())
    README.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    return {"updated": True, "path": str(README), "at": now_stamp()}


if __name__ == "__main__":
    result = update()
    print(json.dumps(result, ensure_ascii=False))
