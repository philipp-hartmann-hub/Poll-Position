#!/usr/bin/env bash
# Einfacher Cron-Wrapper für Hosts ohne GitHub Actions.
# Crontab-Beispiel (täglich 06:15):
#   15 6 * * * /path/to/Umfragen/scripts/cron-pipeline.sh >> /var/log/poll-position-pipeline.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_PREFIX="[poll-position $(date -u +%Y-%m-%dT%H:%M:%SZ)]"

echo "$LOG_PREFIX START data_pipeline.run"

if command -v uv >/dev/null 2>&1; then
  RUN=(uv run python -m data_pipeline.run)
else
  RUN=(python -m data_pipeline.run)
fi

if ! "${RUN[@]}"; then
  echo "$LOG_PREFIX FEHLER: Pipeline abgebrochen (Exit $?)." >&2
  exit 1
fi

echo "$LOG_PREFIX OK"
