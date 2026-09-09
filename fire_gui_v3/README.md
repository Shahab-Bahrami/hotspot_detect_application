# SenseNet Hotspot Intelligence — Version 3

Version 3 is the maintained local research-evaluation application. It follows
the internal model study by keeping two meanings visibly separate:

- **Verified-fire evidence baseline:** regularized logistic regression using
  G7 online non-label features; trained on Verified Fire versus Verified No
  fire with Sitrep rows excluded.
- **Operational-context benchmark:** tuned histogram gradient boosting using
  G8 features, including strictly prior status history; trained on Verified
  Fire or Fire inside Sitrep versus Verified No fire.

Both pipelines train on 2019+2023, were selected/evaluated on 2025, and show
their saved validation metrics in the interface. Partial 2026 is a previously
examined forward benchmark. Neither score is autonomous dispatch guidance or a
guarantee of physical fire.

## Relationship to the customer baseline

The customer's existing rule is provisionally understood to alert when at
least two hotspots form a sequence within 1 km and successive detections occur
within 30 minutes. Its supplied pooled matrix has 92.6% recall, 81.6%
precision, 27.1% specificity, and an 88.2% alert rate. Version 3 does not yet
replace that rule: it produces continuous research scores intended for
downstream prioritization. The published Version 3 top-20% metrics and the
customer rule's 88.2% operating point are not directly comparable. See
`modeling/baseline/customer_baseline/Customer_Baseline_Comparison_Report.html`.

## Run from source

Use Python 3.11 or newer, install `requirements.txt`, then run from the project
root:

```bash
python3 apps/fire_gui_v3/app.py
```

The browser opens at `http://127.0.0.1:5050`. Linux users can run
`apps/fire_gui_v3/start_linux_v3.sh`; macOS users can double-click
`start_v3.command`. The OpenStreetMap basemap requires internet access, while
model scoring is local.

## Native builds

Build on the target operating system; PyInstaller does not cross-compile:

- Linux: `apps/fire_gui_v3/build_linux_v3.sh`
- macOS: double-click `apps/fire_gui_v3/build_macos_v3.command`
- Windows: double-click `apps\\fire_gui_v3\\build_windows_v3.bat`

Outputs are written to `artifacts/version3/pyinstaller/dist/` as
`SenseNetHotspotV3`, `SenseNetHotspotV3.app`, or
`SenseNetHotspotV3.exe`. Each build bundles the workbook, two model pipelines,
normalization rules, templates, logo, and Natural Earth land/water data.

## Feature and model contract

`v3_features.py` computes features using only report timestamps strictly
earlier than the candidate alert, excluding its entire same-time batch. The
normalization parameters and exact feature order live in `models/`. Re-export
models only through:

```bash
modeling/sensenet_study/.venv/bin/python modeling/sensenet_study/export_v3_models.py
```

The nearby-history panel is descriptive and may include records at the entered
timestamp; it is not the model feature calculation. The optional AI analyst is
also separate from prediction. Provider keys are not written to disk.

See the internal paper in `modeling/sensenet_study/` for metrics, limitations,
and the Version 3 translation.
