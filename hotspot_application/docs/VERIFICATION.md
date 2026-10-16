# Verification record

Verified locally on 16 October 2026 using Python 3.9, the Node runtime bundled with the temporary Playwright test tooling, and an isolated headless Brave/Chromium browser on macOS. Application runtime requires only Python and a browser; the QA packages are not included in the application or needed by users.

## Passed

- Eight domain checks in `tests/engine.test.cjs`: missing numbers and coordinates; ISO/Excel timestamps and timezone offsets; sensor-specific confidence; conservative imported decisions; missing-value filtering; worldwide coordinates and date ranges; statistics; numeric feature thresholds.
- Seven Python adapter tests in `tests/test_server.py`: NASA URL construction, worldwide and custom bounds, allowed products and 1–5-day ranges, availability queries, local model endpoint restrictions, Ollama responses, and compatible chat responses/errors.
- End-to-end browser checks in `tests/browser_smoke.py`: demo map; manual filters; CSV export; optimized workflow unavailable without predictions; study details; CSV invalid rows; multi-sheet XLSX import; independent API state; NASA adapter UI with mocked response; SenseNet placeholder; model configuration; chat with a mocked response; payload exclusion of the NASA key and raw coordinate columns; separate conversations; 49-feature candidate catalogue; guide; desktop/tablet/mobile layouts.
- No JavaScript page errors in the browser run. No horizontal overflow at 390 px and 1024 px widths.
- Clean visual previews inspected at 1512 px desktop and 390 px mobile; tablet preview captured at 1024 px.
- The **actual latest study prediction file** imported through the same parsing/normalization/filter functions: **43,945 rows**, no invalid coordinates, no missing timestamps, correctly detected `utc`, **35,466 retained**, **8,479 excluded**, **zero decision mismatches** against frozen `retain_for_review` values. This validates import compatibility, not model inference or scientific generalization. The source file was not modified or copied into the app.

## Verification limits

- No NASA MAP_KEY or live LLM credentials were supplied. Live authenticated NASA and hosted/local model requests were not exercised. Request construction, response handling, and UI flows were tested with mocks.
- Windows and Linux launchers and the Python/browser architecture are provided; this session executed on macOS only.
- The trained model and raw-data history extraction are not implemented in this interface release. Optimized decisions are imported from study outputs.
- The SenseNet service is a planned connector, not a working remote service.
- Optional online street tiles depend on network access. The bundled basemap works locally.

## Preview files

- [Offline workspace](preview-offline.png)
- [Satellite/API workspace](preview-satellite.png)
- [Mobile layout](preview-mobile.png)

Only the labelled synthetic example appears in preview images. No customer study observations, keys, or private conversations are included.
