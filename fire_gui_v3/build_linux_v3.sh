#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$project_root"

if [[ ! -x ".venv-linux-v3/bin/python" ]]; then
  python3 -m venv .venv-linux-v3
fi

. .venv-linux-v3/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/fire_gui_v3/requirements.txt -r apps/fire_gui_v3/requirements-linux-build.txt
python -m PyInstaller --noconfirm --clean \
  --workpath artifacts/version3/pyinstaller/build \
  --distpath artifacts/version3/pyinstaller/dist \
  apps/fire_gui_v3/SenseNetHotspotV3.spec

echo "Version 3 build complete: artifacts/version3/pyinstaller/dist/SenseNetHotspotV3"
