#!/bin/zsh
set -e
cd "$(dirname "$0")/../.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.11 or newer, then run this file again."
  read -k 1 "?Press any key to close."
  exit 1
fi

if [[ ! -x ".venv-macos-v3/bin/python" ]]; then
  python3 -m venv .venv-macos-v3
fi

source .venv-macos-v3/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/fire_gui_v3/requirements.txt -r apps/fire_gui_v3/requirements-macos-build.txt
python -m PyInstaller --noconfirm --clean --workpath artifacts/version3/pyinstaller/build --distpath artifacts/version3/pyinstaller/dist apps/fire_gui_v3/SenseNetHotspotV3-mac.spec

echo "Version 3 build complete: artifacts/version3/pyinstaller/dist/SenseNetHotspotV3.app"
read -k 1 "?Press any key to close."
