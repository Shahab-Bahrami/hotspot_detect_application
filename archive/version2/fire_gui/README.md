# Indonesia hotspot verification GUI

This is a local Flask application with an ordinary HTML/CSS/JavaScript frontend. It supports the persisted scikit-learn, TensorFlow ANN, and hybrid CNN models without converting them to JavaScript. It also provides nearby historical report analytics and an optional AI evidence analyst.

## Run

From the project directory:

```bash
python3 apps/fire_gui/app.py
```

The browser opens at `http://127.0.0.1:5050`. If it does not open automatically, visit that address manually. The OpenStreetMap basemap requires an internet connection; predictions run locally.

On macOS, you may also double-click `start_gui.command`.

## Nearby spatial and temporal context

After an estimate, the left-side history panel searches the bundled workbook around
the entered coordinate. Users can select a radius from 500 m to 10 km and a lookback
window from 30 days to all earlier reports. It shows:

- total, determinate, fire-associated, no-fire, and unverified reports;
- the observed fire rate among determinate reports;
- cumulative comparisons at 0.5, 1, 2, 5, and 10 km;
- year-by-year results and the closest source rows; and
- a CSV download of the displayed nearby rows.

Reports later than the entered alert time are always excluded so this panel does not
leak future information into a retrospective decision.

## AI evidence analyst

The panel below the map supports three provider modes:

- **Ollama (local):** enter the name of a model already installed in Ollama. The
  default server address is `http://127.0.0.1:11434` and no key is needed.
- **OpenAI:** enter an OpenAI model name and API key. The backend uses the Responses
  API and sets `store` to false.
- **OpenAI-compatible:** enter the base URL, model name, and an API key if the server
  requires one. This works with local servers such as LM Studio and compatible hosted
  services that expose `/chat/completions`.

Keys are held only in the browser field for the current session, sent to the local
Flask process for each request, and never written to disk. A remote provider receives
a compact workbook profile, the selected nearby statistics, up to 25 nearby rows, the
current estimate, and recent chat messages. It does not receive the entire workbook.
The provider therefore cannot answer row-level questions outside that supplied
evidence; it is instructed to say when evidence is unavailable.

The OpenAI request shape follows the official [Responses API documentation](https://developers.openai.com/api/reference/cli/resources/responses/methods/create).

## Build a macOS application

Install Python 3.11, then double-click `build_macos.command`. The standalone app is
written to:

```text
artifacts/pyinstaller/dist/IndonesiaFireGUI.app
```

The existing `start_gui.command` remains available for running directly from source.

## Build a Windows executable

PyInstaller must build Windows applications on Windows. Copy the complete project
folder to a 64-bit Windows machine, install 64-bit Python 3.11, and double-click:

```text
apps\fire_gui\build_windows.bat
```

The script creates an isolated environment, installs the dependencies, and writes
the standalone application to:

```text
dist\IndonesiaFireGUI.exe
```

The executable bundles the trained models, templates, map data, and the historical
workbook. Python is not required on the computer that runs the finished executable.
Because TensorFlow is included, the file is large and the first launch may take a
little while. Windows SmartScreen may also warn about an unsigned locally built app.

## Retrain artifacts

```bash
python3 modeling/baseline/train_gui_models.py
```

Click the map to fill the latitude and longitude fields, or enter coordinates manually. The backend screens every point against the bundled Natural Earth 1:10m land and lake polygons. Ocean and mapped-lake points return exactly 0% and skip model inference. Very small islands and points close to a shoreline should be checked against a higher-resolution local coastline layer.

The GUI is a retrospective decision-support prototype. “Fire-associated” combines `Verified Fire` and `Fire inside Sitrep`; it is not a replacement for ground verification.

See `GUI_ENHANCEMENT_REPORT.md` for the analytics definitions, AI data flow, privacy
boundaries, and validation checklist.
