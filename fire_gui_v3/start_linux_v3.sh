#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$project_root"
if [[ -x ".venv-linux-v3/bin/python" ]]; then
  exec .venv-linux-v3/bin/python apps/fire_gui_v3/app.py
fi
exec python3 apps/fire_gui_v3/app.py
