# SenseNet Hotspot Studio

A local web application for exploring satellite hotspots anywhere in the world, with a SenseNet-inspired interface. This first release focuses on the interface and working data-exploration flows.

## Start

Requires **Python 3.9 or newer** and a modern browser. No Python packages, Node.js, build step, account, or internet connection are required for file analysis.

From this folder:

```sh
python3 serve.py --open
```

On Windows:

```powershell
py -3 serve.py --open
```

Or use the included launcher:

| Platform | Launcher |
| --- | --- |
| macOS | Double-click `start.command` |
| Windows | Double-click `start_windows.bat` |
| Linux | Run `./start.sh` |

Open **http://127.0.0.1:8765**. Keep the terminal open; Ctrl+C stops the app. If the port is already occupied, run `python3 serve.py --port 8766 --open`. The server binds only to loopback.

## Included

- **Offline analysis:** CSV, XLSX, and XLS imports; worksheet selection; column mapping; timezone choice; invalid-coordinate reporting; worldwide pan/zoom map; observation popups; paginated data table; filtered CSV export.
- **Filters:** dedicated optimized-workflow selector; sensor-aware confidence, FRP, satellite, day/night, UTC dates, map bounds, and numeric imported-feature thresholds. Missing optional values have an explicit keep/exclude policy.
- **Feature library:** 127 source fields in six selectable groups, including the 49-feature optimized candidate subset. Exact names, availability constraints, definitions from the latest dictionary, and earlier feature variants remain inspectable.
- **Satellite & API:** a functioning NASA FIRMS query adapter, availability check, free-key instructions, global/bounding-box queries, and a separate SenseNet service placeholder.
- **Assistant on both pages:** Ollama, LM Studio / compatible local servers, and compatible hosted chat APIs. Each workspace has its own conversation and dataset.
- **Analysis below results:** input and retained counts, mean FRP, confidence distribution, time series, satellite contributions, and data quality.
- **Offline assets:** libraries, Poppins fonts, and a Natural Earth world basemap are included. Optional OpenStreetMap street tiles require internet access.

The initial dataset contains **620 explicitly labelled synthetic observations** across several continents. It demonstrates the interface and is not a satellite feed or evidence of fires.

## Optimized workflow: exact scope

The latest source is `../hotspot_detection_new/general_study/reanalysis_20261010`, especially its README, derived feature dictionary, frozen review-candidate predictions, and model selections.

Its history-only logistic model is explicitly a **post-selection review candidate**, not an independently validated production optimum. It uses 49 history features, threshold `0.178169086490223`, hour-end batches, and conservative retention when history or source support is insufficient. Later-year results depend on the truth-label policy and selected customer-list context.

In this interface release, the optimized workflow **reads imported `retain_for_review` and `reason` columns**. An optional `score` column can also be mapped. It does not compute history features or load a trained model. The Apply button remains unavailable when no imported decisions exist. Missing decisions and conservative fallback reasons are retained.

To inspect the latest study output, decompress `review_candidate_all_report_predictions.csv.gz` locally, import its CSV, and map its coordinates and `retain_for_review` / `reason` columns. Use an explicitly UTC timestamp column if available; choose UTC+07:00 when mapping the study's `local_time`.

Manual filters operate on the imported observations. The library allows numeric thresholds on imported feature columns; spatial, temporal, retrospective, and trained-model features are not silently recomputed. Earlier locked model families and their thresholds are shown for inspection. Raw-data feature extraction, inference, incident-level validation, and global model transfer remain separate implementation work.

See [feature groups and provenance](docs/FEATURE_GROUPS.md).

## NASA FIRMS

1. Request a free [FIRMS MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key/) using your email; NASA emails the key.
2. In **Satellite & API**, paste that key and select a MODIS or VIIRS product.
3. Select `world` or a bounding box in `west,south,east,north` order. For antimeridian-crossing regions, make two queries.
4. Select **1–5 days**. Leave the start date blank for the latest period; with a date, the range starts on that date and runs forward.
5. Use **Check availability**, then **Fetch hotspots**.

The area endpoint is:

```text
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAYS}[/{START_DATE}]
```

NASA documents 5,000 transactions per 10-minute interval; larger queries can consume more than one transaction. The MAP_KEY is a FIRMS key, not an Earthdata bearer token. Source coverage and dates vary by product. [Area API](https://firms.modaps.eosdis.nasa.gov/api/area/) · [Availability API](https://firms.modaps.eosdis.nasa.gov/api/data_availability/). Documentation checked 16 October 2026.

The Python adapter forwards only the requested query to NASA, avoids browser CORS restrictions, and does not store or log the key. The SenseNet service panel is deliberately unavailable until its API is developed; its endpoint currently returns HTTP 501.

## Language models

Open the assistant's settings, choose a provider, and enter the exact model ID:

| Provider | Base URL example | Appended path |
| --- | --- | --- |
| Ollama | `http://localhost:11434` | `/api/chat` |
| LM Studio / compatible local | `http://localhost:1234/v1` | `/chat/completions` |
| Compatible hosted API | Your provider's HTTPS base URL, usually ending in `/v1` | `/chat/completions` |

Start and load your local model first. Hosted providers use the key you supply and require the interface's selection to send your messages and aggregate statistics to that provider. Some providers with different API formats or parameters need a future adapter.

The context includes aggregate statistics, filter configuration, and study limitations. It omits raw rows, coordinates, file names, and NASA keys. Keys, file data, and chats are held in memory, not in local storage or a database. Your own messages can still include information you choose to type. Disconnect clears the assistant key and conversation history. Refresh clears all session data.

[Ollama chat reference](https://docs.ollama.com/api/chat) · [LM Studio chat reference](https://lmstudio.ai/docs/developer/openai-compat/chat-completions).

## Data conventions and limits

- Latitude and longitude must be finite decimal degrees within −90…90 and −180…180. Blanks are never converted to zero. Invalid-coordinate rows are counted and excluded from maps, filters, and exports; source files are unchanged.
- Input dates must use ISO `YYYY-MM-DD` or ISO timestamps. NASA `acq_time` is HHMM; Excel serial dates/times are supported. Ambiguous locale dates are reported as missing. Explicit offsets take precedence over the import timezone.
- Confidence uses VIIRS `l/n/h`, and MODIS numeric values when a MODIS instrument or Terra/Aqua spacecraft is identified. The interface's MODIS screening bands are `<30`, `30–79`, and `≥80`. Unknown sensor/scale combinations remain unknown. No cross-sensor confidence probability is fabricated.
- FRP is in MW. Blank, nonnumeric, and negative FRP are treated as unavailable and excluded from the mean.
- The page accepts up to 20 MB, 100,000 rows, and 300 columns. It renders at most 8,000 evenly sampled map points for larger inputs and labels that sampling. Tables, exports, and statistics use all valid rows.
- Export includes all valid input rows (original fields prefixed `input_`), normalized values, decisions, reasons, workflow, and settings. Spreadsheet formula-like strings are escaped. Invalid-coordinate rows are reported in data quality and remain in your original file.
- Counts refer to observations/reports, not independent fire incidents. No live ground-truth accuracy is claimed.

## Development and verification

`static/index.html`, `styles.css`, and `app.js` implement the interface. `engine.js` contains pure import/filter/statistics logic. `serve.py` serves local assets and provides narrow NASA and LLM adapters using the Python standard library. There is no deployment or persistent storage in this release.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/engine.test.cjs
```

Browser checks require a separately installed Playwright package and a Chromium-compatible executable; these are development-only dependencies:

```sh
python3 tests/browser_smoke.py --browser "/path/to/chromium" --url http://127.0.0.1:8765 --screenshots /tmp/hotspot_previews
```

See [verification record](docs/VERIFICATION.md) for observed results and limits. Third-party assets are documented in [THIRD_PARTY.txt](THIRD_PARTY.txt).
