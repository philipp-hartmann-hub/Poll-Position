#!/usr/bin/env bash
# Cursor stop-Hook: aktualisiert README.md nach jeder Agent-Session.
set -euo pipefail

# Hook-Payload von stdin lesen (muss konsumiert werden)
cat >/dev/null

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/scripts/update-readme.py" >/dev/null

# stop-Hooks erwarten gültiges JSON auf stdout
echo '{}'
