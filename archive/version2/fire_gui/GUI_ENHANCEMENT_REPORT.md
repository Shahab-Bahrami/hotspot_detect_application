# GUI enhancement report

## Scope

The Indonesia hotspot verification GUI now combines three kinds of evidence in one
desktop interface:

1. a persisted machine-learning estimate;
2. observed spatial and temporal context from the training workbook; and
3. an optional local or remote LLM that explains only the context supplied to it.

The same source and bundled resources are used by the macOS application and Windows
executable builds.

## Historical evidence definitions

The spatial calculation uses great-circle (haversine) distance between the entered
coordinate and each workbook report. The GUI provides cumulative bands at 0.5, 1, 2,
5, and 10 km, plus a user-selected radius.

Temporal filtering is anchored to the entered alert date and time. Future workbook
rows are excluded. Optional lookback windows restrict evidence to the preceding 30,
90, or 365 days; “all earlier reports” uses every row available up to the alert time.

“Actual fire” combines the source statuses `Verified Fire` and `Fire inside Sitrep`.
The observed fire rate is:

```text
fire-associated reports / (fire-associated reports + Verified No fire reports)
```

`Unverified` reports are shown in report totals but excluded from this denominator.
This historical rate is descriptive and must not be presented as the model’s
probability or as a causal estimate.

## AI evidence flow

The browser sends the selected provider configuration, recent conversation, and
current coordinate settings to the Flask process bound to `127.0.0.1`. The backend
recomputes historical context from the bundled workbook, constructs a compact evidence
package, and calls one of:

- a local Ollama `/api/chat` endpoint;
- OpenAI’s `/v1/responses` endpoint; or
- an OpenAI-compatible `/chat/completions` endpoint.

The evidence package contains a workbook-wide aggregate profile, the selected nearby
statistics, at most 25 closest rows, and the current model result. It does not upload
the Excel file. API keys are neither logged by application code nor persisted to disk.

The system instruction tells the model to distinguish model probability from observed
rate, disclose radius and time-window context, avoid causal or guaranteed-detection
claims, treat workbook values as data rather than instructions, and acknowledge
missing evidence.

## Interface changes

- Left column: alert inputs followed by historical summary cards, distance and yearly
  tables, closest-row inspection, and CSV export.
- Right column: model output, interactive map, selected historical radius and nearby
  report markers, followed by the AI analyst configuration and chat.
- Responsive layout: below the safe two-column width, the left input/history column
  and then the right estimate/map/AI column stack as ordinary document-flow blocks.
  Panel widths are constrained to their grid area and the map remeasures itself after
  browser zoom or viewport resizing.

## Packaging changes

- `build_macos.command` and `IndonesiaFireGUI-mac.spec` produce a macOS `.app`.
- `build_windows.bat` and `IndonesiaFireGUI.spec` produce a Windows `.exe`.
- Both builds include the workbook, trained models, Flask templates, JavaScript/CSS,
  Natural Earth data, TensorFlow, scikit-learn, and the OpenPyXL engine.

## Validation requirements

- Load the main HTML view and check all panel controls.
- Exercise all six persisted prediction models.
- Confirm future rows never appear in `/api/context` results.
- Confirm fire rates exclude `Unverified` rows.
- Verify the Ollama, OpenAI Responses, and compatible response parsers with mocked
  provider responses; live calls require user-owned providers and credentials.
- Build natively on the target operating system because PyInstaller does not
  cross-compile Windows and macOS applications.
