// Test krzyżowy: silnik JavaScript (web/engine_*.js) vs silnik referencyjny Python (tests/js/cases.json).
// Uruchomienie: python tools/export_crosscases.py && node tests/js/crosscheck.js
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.resolve(__dirname, '..', '..');
const ctx = { console, Math, JSON, Object, Array, Set, Map, Error, Number, String, isFinite, unescape, encodeURIComponent };
ctx.globalThis = ctx;
vm.createContext(ctx);
['normdata.js', 'engine_core.js', 'engine_stm.js', 'engine_analysis.js'].forEach(f => vm.runInContext(fs.readFileSync(path.join(ROOT, 'web', f), 'utf8'), ctx, { filename: f }));
const WS = ctx.WS;
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, 'cases.json'), 'utf8'));
const REL = 1e-6;
const close = (a, b) => {
  if (a === null || b === null || a === undefined || b === undefined) return (a === null || a === undefined) && (b === null || b === undefined);
  if (a === 'inf' || b === 'inf') return (a === 'inf' || a === Infinity) && (b === 'inf' || b === Infinity);
  if (!isFinite(a)) return a === Infinity && b === 'inf';
  return Math.abs(a - b) <= REL * Math.max(1, Math.abs(a), Math.abs(b));
};
let fails = 0, total = 0;
cases.forEach(cs => {
  const r = WS.analyze(cs.variant), py = cs.py, errs = [];
  total++;
  if (r.verdict.code !== py.verdict) errs.push(`werdykt JS ${r.verdict.code} ≠ PY ${py.verdict}`);
  const jsErr = WS.errorsOf(r).map(m => m.text);
  if (jsErr.length !== py.errors.length) errs.push(`błędy JS ${JSON.stringify(jsErr)} ≠ PY ${JSON.stringify(py.errors)}`);
  const jm = new Map(r.checks.map(c => [c.id, c]));
  py.checks.forEach(pc => {
    const jc = jm.get(pc.id);
    if (!jc) { errs.push('brak w JS: ' + pc.id); return; }
    if (jc.status !== pc.status) errs.push(`${pc.id}: status JS ${jc.status} ≠ PY ${pc.status} (η JS ${jc.eta}, PY ${pc.eta})`);
    const noise = pc.id === 'MODEL_EQUILIBRIUM';   // residuum ~1e-12 N: szum numeryczny, porównywany jest tylko status
    if (!noise && !close(jc.E_d, pc.E_d)) errs.push(`${pc.id}: E_d JS ${jc.E_d} ≠ PY ${pc.E_d}`);
    if (!noise && !close(jc.R_d, pc.R_d)) errs.push(`${pc.id}: R_d JS ${jc.R_d} ≠ PY ${pc.R_d}`);
    jm.delete(pc.id);
  });
  jm.forEach((c, id) => errs.push('nadmiarowe w JS: ' + id));
  const jmain = r.main ? r.main.desc() : null;
  if (jmain !== py.main) errs.push(`zbrojenie JS ${jmain} ≠ PY ${py.main}`);
  Object.entries(py.links).forEach(([sd, l]) => { const ll = r.links[sd]; const jl = ll ? [ll.h_depths.length, ll.h_phi, ll.v_positions.length, ll.v_phi] : null; if (JSON.stringify(jl) !== JSON.stringify(l)) errs.push(`strzemiona ${sd}: JS ${JSON.stringify(jl)} ≠ PY ${JSON.stringify(l)}`); });
  const gs = r.stm[r.governing];
  Object.entries(py.T).forEach(([sd, T]) => { const s = gs && gs.sides[sd]; if (!s || !close(s.state.T, T)) errs.push(`T_${sd}: JS ${s && s.state.T} ≠ PY ${T}`); });
  Object.entries(py.x_c).forEach(([sd, x]) => { const s = gs && gs.sides[sd]; if (!s || !close(s.state.x_c, x)) errs.push(`x_c ${sd}: JS ${s && s.state.x_c} ≠ PY ${x}`); });
  const kg = r.schedule.reduce((a, b) => a + b.mass, 0);
  if (Math.abs(kg - py.schedule_kg) > 1e-6 * Math.max(1, kg)) errs.push(`masa stali JS ${kg.toFixed(3)} ≠ PY ${py.schedule_kg.toFixed(3)}`);
  if (errs.length) { fails++; console.log(`✗ ${cs.name} (${r.verdict.code})`); errs.slice(0, 12).forEach(e => console.log('    ' + e)); if (errs.length > 12) console.log(`    … +${errs.length - 12}`); }
  else console.log(`✓ ${cs.name} — ${r.verdict.code}, ${r.checks.length} sprawdzeń zgodnych`);
});
console.log(`\n${total - fails}/${total} przypadków zgodnych`);
process.exit(fails ? 1 : 0);
