const assert = require('node:assert/strict');
const E = require('../static/engine.js');
let count = 0;
function test(name, fn) { fn(); count++; console.log('PASS', name); }
test('Missing numeric values never become zero coordinates', () => {
  assert.equal(E.number(''), null); assert.equal(E.number('  '), null); assert.equal(E.number(null), null); assert.equal(E.number('0'), 0);
  const result = E.normalizeRows([{lat:'',lon:4},{lat:0,lon:0},{lat:91,lon:0},{lat:4,lon:181}],{lat:'lat',lon:'lon'});
  assert.equal(result.rows.length,1); assert.equal(result.rejected.length,3); assert.equal(result.rows[0].lat,0);
});
test('Timestamps validate dates and times, with explicit offset precedence', () => {
  assert.equal(E.timestamp('2026-02-30','1200'),null);
  assert.equal(E.timestamp('2026-10-10','2460'),null);
  assert.equal(E.timestamp('10/11/2026','1200'),null);
  assert.equal(E.timestamp('2026-10-10','0055'),Date.parse('2026-10-10T00:55:00Z'));
  assert.equal(E.timestamp('2026-10-10','0700',7),Date.parse('2026-10-10T00:00:00Z'));
  assert.equal(E.timestamp('2026-10-10T12:00:00+02:00',undefined,7),Date.parse('2026-10-10T10:00:00Z'));
  assert.equal(E.timestamp('2026-10-10T12:00:00+02:00','1300',7),Date.parse('2026-10-10T11:00:00Z'));
  assert.equal(E.timestamp(45943, .5),Date.parse('2025-10-13T12:00:00Z'));
});
test('Sensor-specific confidence does not invent numeric VIIRS probabilities', () => {
  assert.equal(E.confidence('h','VIIRS','NOAA-20').level,'high');
  assert.equal(E.confidence(95,'VIIRS','NOAA-20').level,'unknown');
  assert.equal(E.confidence(90,'MODIS','Terra').level,'high');
  assert.equal(E.confidence(90,'Unknown','Unknown').level,'unknown');
  assert.equal(E.confidence('h','MODIS','Aqua').level,'unknown');
});
const rows = E.normalizeRows([
  {lat:45,lon:-120,satellite:'N',confidence:'h',frp:50,daynight:'D',date:'2026-10-12',retain_for_review:'False',reason:'candidate_suppress_review_required'},
  {lat:-20,lon:135,satellite:'N',confidence:'n',frp:'',daynight:'N',date:'2026-10-13',retain_for_review:'False',reason:'insufficient_history_keep'},
  {lat:0,lon:0,satellite:'A',confidence:'20',frp:5,daynight:'D',date:'2026-10-14',retain_for_review:'',reason:''},
],E.guessColumns(['lat','lon','satellite','confidence','frp','daynight','date','retain_for_review','reason'])).rows;
test('Imported review predictions keep unknown and conservative fallback rows', () => {
  const result = E.filterRows(rows,{mode:'optimized'});
  assert.deepEqual(result.results.map(r=>r.retained),[false,true,true]);
});
test('Manual filtering respects missing-value policy and leaves source rows intact', () => {
  assert.equal(E.filterRows(rows,{mode:'custom',frp:10,keepMissing:true}).retained.length,2);
  assert.equal(E.filterRows(rows,{mode:'custom',frp:10,keepMissing:false}).retained.length,1);
  assert.equal(E.filterRows(rows,{mode:'custom',confidence:'high'}).retained.length,1);
  assert.equal(E.filterRows(rows,{mode:'all',frp:50}).retained.length,3);
  assert.equal(rows[0].retained,undefined);
});
test('Global coordinate and UTC date filters do not assume Indonesia', () => {
  assert.equal(E.filterRows(rows,{bbox:{west:-130,east:-100,south:30,north:60}}).retained.length,1);
  assert.equal(E.filterRows(rows,{dateFrom:'2026-10-13',dateTo:'2026-10-13'}).retained.length,1);
});
test('Statistics exclude missing FRP from means and avoid fabricated accuracy', () => {
  const result = E.stats(rows);
  assert.equal(result.meanFrp,27.5); assert.equal(result.frpCount,2);
  assert.equal(result.confidence.high,1); assert.equal(result.confidence.nominal,1);
  assert.equal(E.stats([]).meanFrp,null); assert.equal(E.stats([]).start,null);
  assert.equal(result.accuracy,undefined);
});
test('Numeric feature rules reject empty thresholds instead of applying zero', () => {
  assert.throws(()=>E.filterRows(rows,{mode:'custom',feature:'frp',value:''}),/numeric/);
  assert.equal(E.filterRows(rows,{mode:'custom',feature:'frp',operator:'lte',value:10,keepMissing:false}).retained.length,1);
});
console.log(`${count} domain checks passed.`);
