// Optional compatibility check against the adjacent, unchanged study output.
const fs = require('node:fs');
const zlib = require('node:zlib');
const path = require('node:path');
const assert = require('node:assert/strict');
const E = require('../static/engine.js');
const Papa = require('../static/vendor/papaparse.min.js');
const source = process.argv[2] || path.resolve(__dirname, '../../hotspot_detection_new/general_study/reanalysis_20261010/outputs/review_candidate_all_report_predictions.csv.gz');
const content = zlib.gunzipSync(fs.readFileSync(source)).toString();
const parsed = Papa.parse(content, { header:true, skipEmptyLines:'greedy' });
const mapping = E.guessColumns(parsed.meta.fields);
const data = E.normalizeRows(parsed.data, mapping, 0);
const results = E.filterRows(data.rows, { mode:'optimized' });
assert.equal(parsed.errors.length,0);
assert.equal(data.rows.length,43945);
assert.equal(data.rejected.length,0);
assert.equal(data.missingTime,0);
assert.equal(results.results.filter(r => r.retained !== r.reviewRetain).length,0);
console.log(JSON.stringify({ source_rows:data.rows.length, invalid_coordinates:data.rejected.length, missing_timestamps:data.missingTime, timestamp_column:mapping.date, retained:results.retained.length, excluded:results.excluded.length, decision_mismatches:0 }));
