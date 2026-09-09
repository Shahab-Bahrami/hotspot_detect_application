#!/bin/zsh
cd "$(dirname "$0")/../.."
if [[ -x ".venv-macos-v3/bin/python" ]]; then
  exec .venv-macos-v3/bin/python apps/fire_gui_v3/app.py
fi
exec python3 apps/fire_gui_v3/app.py
