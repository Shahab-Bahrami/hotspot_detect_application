#!/bin/zsh
set -e
cd "$(dirname "$0")/../.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.11, then run this file again."
  read -k 1 "?Press any key to close."
  exit 1
fi

if [[ ! -x ".venv-macos/bin/python" ]]; then
  python3 -m venv .venv-macos
fi

source .venv-macos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/fire_gui/requirements.txt -r apps/fire_gui/requirements-macos-build.txt
python -m PyInstaller --noconfirm --clean --workpath artifacts/pyinstaller/build --distpath artifacts/pyinstaller/dist apps/fire_gui/IndonesiaFireGUI-mac.spec

echo "Build complete: artifacts/pyinstaller/dist/IndonesiaFireGUI.app"
read -k 1 "?Press any key to close."
