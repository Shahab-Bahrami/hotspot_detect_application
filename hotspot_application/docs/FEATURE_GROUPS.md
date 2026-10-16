# Feature groups and source provenance

The interface catalogue is saved in `static/data/feature-catalog.json`. It contains 127 distinct field names. The optimized group overlaps the full catalogue: its 49 fields are an explicit model subset, not 49 additional fields.

| Group | Fields | Contents | Interface behavior |
| --- | ---: | --- | --- |
| Optimized workflow | 49-field subset | Latest history-only logistic review candidate | Dedicated selector; applies imported frozen `retain_for_review` decisions and conservative fallback reasons. Raw-data inference is not implemented. |
| Detection quality | 18 | FRP, temperature, thermal contrast, confidence, scan/track, pixel area, earlier snapshot variants | Core confidence and FRP controls work on mapped input. Other numeric fields can be selected when imported. |
| Spatial support & growth | 11 | Current-batch neighbors and other satellites, recent/previous/new cells, extent, causal and strict-prior cluster variants | Definitions available; numeric imported columns can be filtered. No implicit neighborhood recomputation. |
| Temporal history | 69 | Detection/day/visit counts at 0.5/1/2 km and 1/3/7/30 days; recurrence, stationary fraction, concentration, recent share, earlier temporal variants | Definitions and historical variants retained for study. Numeric imported columns can be filtered. |
| Sensor, location & time | 13 | Spacecraft one-hot features, latitude/longitude, cyclic hour and season; earlier coordinate aliases | Satellite, UTC dates, and current-map-area filters work on input. Study-derived encodings require imported columns. |
| Retrospective research | 16 | Future 24/72-hour features and archive-type indicators | Kept explicitly separate as retrospective features. Numeric imported fields can be examined; no immediate-detection claim. |

## Primary source files

Paths are relative to the repository root:

- `hotspot_detection_new/general_study/reanalysis_20261010/README.txt`
- `hotspot_detection_new/general_study/reanalysis_20261010/outputs/derived_feature_dictionary.csv`: exact definitions for the 60 latest customer-derived fields.
- `hotspot_detection_new/general_study/reanalysis_20261010/outputs/fire_run_manifest.json`: exact 49-feature history subset and larger families.
- `hotspot_detection_new/general_study/reanalysis_20261010/outputs/review_candidate_confusions.csv`: frozen-candidate results and threshold.
- `hotspot_detection_new/general_study/reanalysis_20261010/outputs/locked_fire_selections.json`: six historical model/policy selections.
- `hotspot_detection_new/general_study/reanalysis_20261010/outputs/nasa_fire_selections.json`: NASA thermal, sensor, and causal cluster features.
- `hotspot_detection_new/notebooks/outputs/hotspot_temporal_study/feature_specifications.json`: earlier snapshot, history, delayed, geography, and archive-type fields.

The latest dictionary definitions are preserved. Earlier-only fields are identified as earlier variants and direct the reader to their original notebook definitions; humanized field names are not presented as a complete computation specification. Thermal-field descriptions summarize the latest NASA study. Duplicate names appear once in the full catalogue.

## Interpretation preserved from the latest study

The primary historical model selection used 2019/2023 only and failed later fire-retention targets. The history-only logistic candidate was highlighted after reviewing later-year results, so it requires a new independent test. Its score is not a calibrated probability. The first month and unsupported/conflicting observations were conservatively retained in the source inference.

| Label policy | Year | Checked non-fire removed | Fire reports retained | Fire reports missed |
| --- | --- | ---: | ---: | ---: |
| Explicitly verified | 2025 | 426 / 1,138 | 39 / 39 | 0 |
| Explicitly verified | 2026 | 541 / 956 | 41 / 41 | 0 |
| Sitrep-inclusive | 2025 | 426 / 1,138 | 145 / 171 | 26 |
| Sitrep-inclusive | 2026 | 541 / 956 | 192 / 192 | 0 |

2026 ends on 7 August. These are report-level results conditional on the customer's filtered list. They do not establish independent-event recall or global performance. List-membership reconstruction is a separate research target and is not treated as fire truth.

## Next inference integration

Add feature extraction and model adapters behind an explicit pipeline contract that returns row-level decisions, reasons, feature coverage, and provenance. Preserve the source timestamp convention, hour-end batch completion, first-month fallback, unsupported-source fallback, duplicate/label-conflict policy, feature order, and preprocessing. Do not substitute a new global geometry/timezone convention and present it as the frozen study model. A globally usable inference implementation needs its own validation, including dateline/high-latitude behavior and genuinely independent locations.

The current explorer has no Indonesia bounding restriction. Its manual map and coordinate filters operate on global WGS 84 inputs.
