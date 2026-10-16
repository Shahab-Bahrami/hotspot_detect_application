/* Pure import, filtering, and statistics functions, shared by both workspaces. */
(function (global) {
  'use strict';
  const number = v => v === null || v === undefined || String(v).trim() === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const norm = v => String(v || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const aliases = {
    lat: ['latitude', 'lat', 'y'], lon: ['longitude', 'lon', 'lng', 'long', 'x'],
    date: ['acq_date', 'acquisition_date', 'datetime', 'timestamp', 'utc', 'utc_time', 'date', 'local_time'],
    time: ['acq_time', 'acquisition_time', 'time'], satellite: ['satellite', 'sat', 'spacecraft', 'sensor', 'source'],
    instrument: ['instrument'], confidence: ['confidence', 'confidence_modis', 'confidence_viirs'],
    frp: ['frp', 'fire_radiative_power'], daynight: ['daynight', 'day_night'],
    brightness: ['bright_ti4', 'brightness', 'hot_K', 'brightness_main'],
    background: ['bright_ti5', 'bright_t31', 'background_K', 'brightness_background'],
    retain: ['retain_for_review'], reason: ['reason'], score: ['score'],
  };
  function guessColumns(headers) {
    const result = {};
    for (const [field, options] of Object.entries(aliases)) result[field] = options.map(a => headers.find(h => norm(h) === norm(a))).find(Boolean) || '';
    return result;
  }
  function satelliteName(value, instrument = '') {
    const s = norm(value);
    if (['n', 'snpp', 'suominpp', 'viirssnppnrt', 'viirssnppsp'].includes(s)) return 'Suomi NPP';
    if (['1', 'n20', 'noaa20', 'j1', 'jpss1', 'viirsnoaa20nrt', 'viirsnoaa20sp'].includes(s)) return 'NOAA-20';
    if (['2', 'n21', 'noaa21', 'j2', 'jpss2', 'viirsnoaa21nrt'].includes(s)) return 'NOAA-21';
    if (['a', 'aqua'].includes(s)) return 'Aqua';
    if (['t', 'terra'].includes(s)) return 'Terra';
    return String(value || instrument || 'Unknown').trim();
  }
  function timestamp(date, time, offset = 0) {
    if (date === null || date === undefined || String(date).trim() === '') return null;
    let dateString;
    if (date instanceof Date) dateString = date.toISOString().replace('Z', '');
    else if (typeof date === 'number' && date > 0 && date < 2958466) dateString = new Date(Date.UTC(1899, 11, 30) + date * 86400000).toISOString().replace('Z', '');
    else dateString = String(date).trim();
    // Ambiguous locale dates require explicit ISO data rather than browser-dependent parsing.
    if (!/^\d{4}-\d{2}-\d{2}(?:$|[T ])/.test(dateString)) return null;
    const day = dateString.slice(0, 10);
    const calendar = new Date(day + 'T00:00:00Z');
    if (!Number.isFinite(+calendar) || calendar.toISOString().slice(0, 10) !== day) return null;
    if (time !== '' && time !== undefined && time !== null) {
      const explicitZone = dateString.match(/(?:Z|[+-]\d{2}:?\d{2})$/i)?.[0] || '';
      let clock;
      if (typeof time === 'number' && time > 0 && time < 1) {
        const minutes = Math.round(time * 1440) % 1440;
        clock = String(Math.floor(minutes / 60)).padStart(2, '0') + ':' + String(minutes % 60).padStart(2, '0');
      } else {
        const s = String(time).trim();
        if (/^\d{1,4}$/.test(s)) { const p = s.padStart(4, '0'); clock = p.slice(0, 2) + ':' + p.slice(2); }
        else if (/^\d{1,2}:\d{2}(?::\d{2})?$/.test(s)) clock = s.padStart(s.length <= 5 ? 5 : 8, '0');
        else return null;
      }
      if (Number(clock.slice(0, 2)) > 23 || Number(clock.slice(3, 5)) > 59 || Number(clock.slice(6) || 0) > 59) return null;
      dateString = day + 'T' + clock + explicitZone;
    }
    const zoned = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(dateString);
    if (dateString.length === 10) dateString += 'T00:00:00';
    dateString = dateString.replace(' ', 'T');
    const t = Date.parse(dateString + (zoned ? '' : 'Z'));
    return Number.isFinite(t) ? t - (zoned ? 0 : Number(offset) * 3600000) : null;
  }
  function confidence(value, instrument, satellite) {
    const s = String(value ?? '').trim().toLowerCase();
    const viirs = /viirs/i.test(instrument) || /NOAA|Suomi/i.test(satellite);
    const modis = /modis/i.test(instrument) || /Aqua|Terra/i.test(satellite);
    if (!modis && ['l', 'low', 'n', 'nominal', 'h', 'high'].includes(s)) return { value: s[0], kind: 'VIIRS', level: ['l', 'low'].includes(s) ? 'low' : ['h', 'high'].includes(s) ? 'high' : 'nominal' };
    const n = number(value);
    if (modis && !viirs && n !== null && n >= 0 && n <= 100) return { value: n, kind: 'MODIS', level: n < 30 ? 'low' : n < 80 ? 'nominal' : 'high' };
    return { value: s || null, kind: viirs ? 'VIIRS' : 'unknown', level: 'unknown' };
  }
  function parseBoolean(value) {
    if (typeof value === 'boolean') return value;
    if (['true', '1'].includes(String(value).toLowerCase().trim())) return true;
    if (['false', '0'].includes(String(value).toLowerCase().trim())) return false;
    return null;
  }
  function normalizeRows(rawRows, mapping, offset = 0) {
    const rows = [], rejected = [];
    let missingTime = 0;
    rawRows.forEach((raw, index) => {
      const get = key => mapping[key] ? raw[mapping[key]] : undefined;
      const lat = number(get('lat')), lon = number(get('lon'));
      if (lat === null || lon === null || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
        rejected.push({ row: index + 2, reason: 'Missing or invalid coordinates', raw }); return;
      }
      const satellite = satelliteName(get('satellite'), get('instrument'));
      const instrument = String(get('instrument') || (/NOAA|Suomi/i.test(satellite) ? 'VIIRS' : /Aqua|Terra/i.test(satellite) ? 'MODIS' : 'Unknown'));
      const time = timestamp(get('date'), get('time'), offset);
      if (time === null) missingTime++;
      const bright = number(get('brightness')), back = number(get('background'));
      const frp = number(get('frp'));
      rows.push({ id: index + 1, lat, lon, time, satellite, instrument,
        confidence: confidence(get('confidence'), instrument, satellite),
        frp: frp !== null && frp >= 0 ? frp : null,
        daynight: /^d(ay)?$/i.test(get('daynight')) ? 'D' : /^n(ight)?$/i.test(get('daynight')) ? 'N' : 'Unknown',
        brightness: bright, background: back, contrast: bright !== null && back !== null ? bright - back : null,
        reviewRetain: parseBoolean(get('retain')), reviewReason: String(get('reason') || ''), score: number(get('score')), raw });
    });
    return { rows, rejected, missingTime };
  }
  const defaults = () => ({ mode: 'all', confidence: 'all', frp: 0, daynight: 'all', satellite: 'all', dateFrom: '', dateTo: '', keepMissing: true, feature: '', operator: 'gte', value: 0, bbox: null });
  function filterRows(rows, options) {
    const f = { ...defaults(), ...options };
    const results = rows.map(row => {
      const reasons = [];
      if (f.mode === 'optimized') {
        if (row.reviewRetain === false && !/insufficient_history|unsupported|conflict/i.test(row.reviewReason)) reasons.push('Imported study result: review exclusion');
      } else if (f.mode === 'custom') {
        if (f.confidence !== 'all' && (row.confidence.level === 'unknown' ? !f.keepMissing : f.confidence === 'high' ? row.confidence.level !== 'high' : row.confidence.level === 'low')) reasons.push('Confidence');
        if (Number(f.frp) > 0 && (row.frp === null ? !f.keepMissing : row.frp < Number(f.frp))) reasons.push('Fire radiative power');
        if (f.daynight !== 'all' && (row.daynight === 'Unknown' ? !f.keepMissing : row.daynight !== f.daynight)) reasons.push('Day / night');
        if (f.satellite !== 'all' && row.satellite !== f.satellite) reasons.push('Satellite');
        if (f.feature) {
          const v = number(row.raw[f.feature]);
          const threshold = number(f.value);
          if (threshold === null) throw new Error('Enter a numeric feature threshold.');
          if (v === null ? !f.keepMissing : f.operator === 'gte' ? v < threshold : v > threshold) reasons.push('Feature: ' + f.feature);
        }
      }
      if (f.dateFrom || f.dateTo) {
        const day = row.time === null ? null : new Date(row.time).toISOString().slice(0, 10);
        if (day === null ? !f.keepMissing : (f.dateFrom && day < f.dateFrom) || (f.dateTo && day > f.dateTo)) reasons.push('Date range');
      }
      if (f.bbox && !(row.lat >= f.bbox.south && row.lat <= f.bbox.north && (f.bbox.west <= f.bbox.east ? row.lon >= f.bbox.west && row.lon <= f.bbox.east : row.lon >= f.bbox.west || row.lon <= f.bbox.east))) reasons.push('Map area');
      return { ...row, retained: reasons.length === 0, filterReason: reasons.join('; ') || (f.mode === 'optimized' ? row.reviewReason || (row.reviewRetain === null ? 'No prediction: kept for review' : 'Imported result: retained') : 'Retained') };
    });
    return { results, retained: results.filter(r => r.retained), excluded: results.filter(r => !r.retained) };
  }
  function stats(rows) {
    const frp = rows.map(r => r.frp).filter(v => v !== null);
    const times = rows.map(r => r.time).filter(v => v !== null).sort((a, b) => a - b);
    const confidenceCounts = { high: 0, nominal: 0, low: 0, unknown: 0 }, satellites = {}, dates = {}, daynight = { D: 0, N: 0, Unknown: 0 };
    rows.forEach(r => { confidenceCounts[r.confidence.level]++; satellites[r.satellite] = (satellites[r.satellite] || 0) + 1; daynight[r.daynight]++;
      if (r.time !== null) { const day = new Date(r.time).toISOString().slice(0, 10); dates[day] = (dates[day] || 0) + 1; } });
    return { total: rows.length, meanFrp: frp.length ? frp.reduce((a, b) => a + b, 0) / frp.length : null,
      maxFrp: frp.length ? frp.reduce((a, b) => Math.max(a, b), 0) : null, frpCount: frp.length,
      start: times[0] ?? null, end: times[times.length - 1] ?? null, confidence: confidenceCounts, satellites, dates, daynight, missingTime: rows.length - times.length };
  }
  global.HotspotEngine = { number, norm, guessColumns, satelliteName, timestamp, confidence, parseBoolean, normalizeRows, defaults, filterRows, stats };
  if (typeof module !== 'undefined') module.exports = global.HotspotEngine;
})(typeof window !== 'undefined' ? window : globalThis);
