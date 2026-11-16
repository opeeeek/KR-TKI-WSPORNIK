/* KRÓTKI WSPORNIK ST – silnik obliczeń (część 3): orkiestrator analizy (dane → model STM → sprawdzenia → werdykt),
   walidacja danych i wyników, odcisk wyników, optymalizacja. Port 1:1 modułów kwst/analysis.py,
   kwst/validation_engine.py, kwst/core/results.py (Verdict), kwst/design_optimizer.py. */
(function (G) {
'use strict';
const WS = G.WS;
const { n, kN, mm, mm2, MPa, barArea, ST, BASIS, make, SIDE_NAME, clone, StmModelError, ND } = WS;

const STRENGTH_GROUPS = new Set(['Krzyżulce', 'Węzły', 'Cięgna', 'Docisk', 'Rozłupywanie', 'Zakotwienie', 'Zbrojenie poprzeczne', 'Mechanizmy dodatkowe', 'Połączenia prefabrykowane']);
const STATUS_RANK = { fail: 3, warn: 2, ok: 1, na: 0 };
const GROUP_ORDER = ['Model', 'Krzyżulce', 'Węzły', 'Docisk', 'Cięgna', 'Rozłupywanie', 'Zbrojenie poprzeczne', 'Zakotwienie', 'Konstrukcyjne', 'Wykonalność', 'Mechanizmy dodatkowe', 'Połączenia prefabrykowane', 'SGU', 'Poza zakresem'];
const LIMITATIONS = [
  'Lokalny model STM wspornika NIE obejmuje sprawdzenia słupa (nośność przekroju, węzeł słupa, zbrojenie podłużne i poprzeczne słupa) — reakcje modelu przekazywane na słup wymagają osobnej weryfikacji.',
  'Płyta stalowa, łożysko (elastomerowe), spoiny, kotwy i inne elementy stalowe — poza zakresem programu (EN 1993, EN 1337).',
  'Skręcanie wspornika i słupa od mimośrodu poprzecznego e_y — poza zakresem (uwzględniono jedynie redukcję szerokości efektywnej).',
  'Stan graniczny użytkowalności: wyłącznie uproszczona kontrola rys cięgna (tabl. 7.2N/7.3N bez korekt); ugięcia nie są sprawdzane.',
  'Obciążenia dynamiczne, zmęczenie, sytuacja pożarowa, obciążenia sejsmiczne — poza zakresem.',
  'Model płaski (2D) — przestrzenny rozkład naprężeń uwzględniono przez grubości efektywne t_A, t_B.',
  'Wsporniki, dla których a_c ≥ z0 (tan θ < 1), nie są krótkimi wspornikami wg J.3 — należy je projektować jak belki wspornikowe (6.1, 6.2); program nie wykonuje takiego wymiarowania.',
  'Węzły w trójosiowym ściskaniu (6.5.4(6), k₄) — nie są stosowane automatycznie.',
];
const MODULE_STATUS = {
  stm_solver: ['zweryfikowany', 'Porównanie z rozwiązaniami analitycznymi kratownic (testy), kontrola residuów i rzędu macierzy, zgodność z metodą sztywności dla układów niewyznaczalnych.'],
  stm_generator: ['zweryfikowany', 'Rozwiązanie zamknięte modelu J.5 porównywane w każdym obliczeniu z niezależnym rozwiązaniem macierzowym; testy równowagi momentów wg wzoru F_td = F·a_c/z0 + H·(a_H+z0)/z0.'],
  material_engine: ['zweryfikowany', 'Wartości tabl. 3.1 kontrolowane wzorami tabl. 3.1 (f_ctm, f_ctk, E_cm) dla wszystkich klas.'],
  load_engine: ['zweryfikowany', 'Testy kombinacji (6.10), (6.10a/b), blokada podwójnego stosowania γ.'],
  strut_checks: ['częściowo zweryfikowany', 'Zweryfikowane niezależnymi obliczeniami ręcznymi w testach; brak porównania z opublikowanym przykładem obliczeniowym.'],
  node_checks: ['częściowo zweryfikowany', 'Zweryfikowane niezależnymi obliczeniami ręcznymi w testach; brak porównania z opublikowanym przykładem obliczeniowym.'],
  tie_checks: ['częściowo zweryfikowany', 'Zweryfikowane obliczeniami ręcznymi w testach.'],
  anchorage_engine: ['częściowo zweryfikowany', 'Wzory (8.2)–(8.6), tabl. 8.2 zweryfikowane obliczeniami ręcznymi; interpretacja długości dostępnej wg J.3(4) — do oceny projektanta.'],
  reinforcement_design: ['częściowo zweryfikowany', 'Otulina (4.4.1), odstępy (8.2), J.3(2)/(3) sprawdzone testami; zestawienie stali — długości orientacyjne.'],
  design_optimizer: ['częściowo zweryfikowany', 'Każdy wariant przechodzi pełną analizę; optymalizacja przeszukiwaniem siatki (deterministyczna).'],
  js_port: ['zweryfikowany', 'Silnik JavaScript porównywany automatycznie z silnikiem referencyjnym Python (testy krzyżowe na przypadkach kontrolnych: identyczne statusy i wartości E_d/R_d).'],
  sls_crack_check: ['nieweryfikowany', 'Uproszczona kontrola rys wg tabl. 7.2N/7.3N bez korekt (7.6N)/(7.7N) — wyłącznie orientacyjnie.'],
  precast_bearing: ['nieweryfikowany', 'Tabl. 10.2 i f_Rd wg 10.9.5.2 — wartości do potwierdzenia; sprawdzenie nieaktywne bez potwierdzenia.'],
};

/* ------------------------------------------------------------------ SHA-256 (synchroniczny, do odcisku wyników) */
function sha256(str) {
  const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const bytes = Array.from(unescape(encodeURIComponent(str)), c => c.charCodeAt(0)), l = bytes.length * 8;
  bytes.push(0x80); while (bytes.length % 64 !== 56) bytes.push(0);
  for (let i = 7; i >= 0; i--) bytes.push(i >= 4 ? 0 : (l >>> (i * 8)) & 0xff);
  let H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const rr = (x, k) => (x >>> k) | (x << (32 - k));
  for (let o = 0; o < bytes.length; o += 64) {
    const w = new Array(64);
    for (let i = 0; i < 16; i++) w[i] = (bytes[o + 4 * i] << 24) | (bytes[o + 4 * i + 1] << 16) | (bytes[o + 4 * i + 2] << 8) | bytes[o + 4 * i + 3];
    for (let i = 16; i < 64; i++) { const s0 = rr(w[i - 15], 7) ^ rr(w[i - 15], 18) ^ (w[i - 15] >>> 3), s1 = rr(w[i - 2], 17) ^ rr(w[i - 2], 19) ^ (w[i - 2] >>> 10); w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0; }
    let [a, b, c, d, e, f, g, h] = H;
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0, t2 = ((rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    H = H.map((v, i) => (v + [a, b, c, d, e, f, g, h][i]) | 0);
  }
  return H.map(v => (v >>> 0).toString(16).padStart(8, '0')).join('');
}
const stable = o => JSON.stringify(o, (k, v) => (v && typeof v === 'object' && !Array.isArray(v)) ? Object.keys(v).sort().reduce((a, q) => { a[q] = v[q]; return a; }, {}) : v);
const hashObj = o => sha256(stable(o)).slice(0, 16);
function resultFingerprint(res) {
  const r6 = v => v === null || v === undefined ? null : !isFinite(v) ? String(v) : Math.round(v * 1e6) / 1e6;
  const rows = res.checks.slice().sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0).map(c => [c.id, c.status, r6(c.E_d), r6(c.R_d)]);
  return sha256(JSON.stringify(rows)).slice(0, 16);
}

/* ------------------------------------------------------------------ werdykt (core/results.Verdict) */
function buildVerdict(checks, errors, ndp) {
  const fails = checks.filter(c => c.status === ST.FAIL), verify = checks.filter(c => c.status === ST.VERIFY);
  if (errors.length) return { code: 'BLOCKED', title: 'OBLICZENIA ZABLOKOWANE', text: `Wykryto błędy krytyczne danych lub modelu obliczeniowego (${errors.length}). Wynik pozytywny jest niedozwolony.`, positive: false };
  const mv = verify.filter(c => c.group === 'Model');
  if (mv.length) return { code: 'OUT_OF_SCOPE', title: 'MODEL POZA ZAKRESEM STOSOWANIA', positive: false,
    text: `Przyjęty model obliczeniowy (J.3) nie jest właściwy dla tej geometrii / obciążenia (${mv.map(c => c.id).join(', ')}). Wymagana alternatywna metoda projektowania — program jej nie wykonuje; pozytywny wniosek ogólny nie może zostać sformułowany.` + (fails.length ? ` Dodatkowo ${fails.length} sprawdzeń nie jest spełnionych w modelu informacyjnym.` : '') };
  if (fails.length) return { code: 'FAIL', title: 'NIE SPEŁNIONO', text: `Co najmniej jedno sprawdzenie nie jest spełnione (${fails.length}). Wspornik w obecnej postaci nie może zostać przyjęty.`, positive: false };
  const txt = `Wszystkie sprawdzenia objęte zakresem programu są spełnione. Pozycje wymagające osobnej weryfikacji: ${verify.length} — wymienione w zestawieniu; wynik lokalnego modelu STM nie potwierdza nośności słupa, połączenia ani całej konstrukcji.`;
  if (!ndp) return { code: 'CONDITIONAL', title: 'SPEŁNIONO WARUNKOWO', text: txt + ' Parametry NDP nie zostały potwierdzone przez projektanta — wynik warunkowy.', positive: false };
  return { code: 'PASS_SCOPE', title: 'SPEŁNIONO W ZAKRESIE PROGRAMU', text: txt, positive: true };
}

/* ------------------------------------------------------------------ walidacja danych (validation_engine.validate_input) */
function validateInput(v) {
  const msgs = [], err = (t, ref) => msgs.push({ level: 'error', text: t, ref: ref || '', source: 'dane wejściowe' }), warn = (t, ref) => msgs.push({ level: 'warning', text: t, ref: ref || '', source: 'dane wejściowe' });
  const g = v.geometry, col = g.column;
  if (!(g.b > 0)) err('Szerokość wspornika b musi być dodatnia.', 'geometry.b');
  [['h_col', col.h_col], ['b_col', col.b_col]].forEach(([nm, val]) => { if (!(val > 0)) err(`Wymiar słupa ${nm} musi być dodatni.`, 'column.' + nm); });
  if (!(col.cover > 0) || col.cover * 2 >= Math.min(col.h_col, col.b_col)) err('Nieprawidłowa otulina słupa.', 'column.cover');
  if (g.b > col.b_col + 1e-9) warn('Szerokość wspornika b większa od wymiaru słupa b_col — model zakłada przekazanie sił na słup o szerokości ≥ b; wymagana ocena projektanta.', 'geometry.b');
  if (!['single', 'double'].includes(g.layout)) err('Nieznany układ wspornika.');
  WS.activeSides(g).forEach(sd => {
    const s = WS.sideInput(g, sd), tag = `[${sd}] `;
    if (!(s.l_c > 0) || !(s.h_c > 0) || !(s.h_e > 0)) { err(tag + 'Wymiary wspornika l_c, h_c, h_e muszą być dodatnie.', sd + '.l_c'); return; }
    if (s.h_e > s.h_c + 1e-9) err(tag + 'Wysokość na końcu h_e większa od wysokości przy licu h_c — geometria nieobsługiwana (wspornik o wysokości rosnącej od słupa).', sd + '.h_e');
    if (!(s.x_slope >= 0 && s.x_slope <= s.l_c)) err(tag + 'Początek skosu x_slope musi leżeć w przedziale [0; l_c].', sd + '.x_slope');
    if (!(s.a_c > 0 && s.a_c < s.l_c)) err(tag + 'Wysięg obciążenia a_c musi spełniać 0 < a_c < l_c.', sd + '.a_c');
    const p = s.plate;
    if (!(p.length > 0) || !(p.width > 0) || p.thickness < 0) err(tag + 'Wymiary płyty oporowej muszą być dodatnie.', sd + '.plate');
    const xc = s.a_c + p.offset;
    if (xc - p.length / 2 < -1e-9 || xc + p.length / 2 > s.l_c + 1e-9) err(tag + 'Płyta oporowa wychodzi poza obrys wspornika.', sd + '.plate');
    if (p.width > g.b + 1e-9) err(tag + 'Szerokość płyty b_p większa od szerokości wspornika b.', sd + '.plate.width');
    if (s.d_user != null && (s.d_user <= 0 || s.d_user >= s.h_c)) err(tag + 'Ręczna wysokość użyteczna d musi spełniać 0 < d < h_c.', sd + '.d_user');
    if (s.a_H_user != null && s.a_H_user < 0) err(tag + 'Ramię a_H nie może być ujemne.', sd + '.a_H_user');
    if (s.x_c_user != null && s.x_c_user <= 0) err(tag + 'Ręczne x_c musi być dodatnie.', sd + '.x_c_user');
    if (s.z0_user != null && s.z0_user <= 0) err(tag + 'Ręczne z0 musi być dodatnie.', sd + '.z0_user');
    if (s.h_c > 3 * s.l_c) warn(tag + 'Bardzo duża wysokość względem wysięgu — sprawdź zakres stosowania modelu J.3.');
  });
  const m = v.materials;
  if (!ND.t31[m.concrete]) err(`Nieznana klasa betonu ${m.concrete}.`, 'materials.concrete');
  if (!ND.ductility[m.steel_class]) err(`Nieznana klasa ciągliwości ${m.steel_class}.`, 'materials.steel_class');
  if (!ND.expGroup[m.exposure]) err(`Nieobsługiwana klasa ekspozycji ${m.exposure}.`, 'materials.exposure');
  if (!ND.structClasses.includes(m.structural_class)) err(`Nieznana klasa konstrukcji ${m.structural_class}.`, 'materials.structural_class');
  if (!(m.delta_c_dev >= 0 && m.delta_c_dev <= 20)) err('Δc_dev poza zakresem 0–20 mm.', 'materials.delta_c_dev');
  else if (m.delta_c_dev < 10) warn('Δc_dev < 10 mm — redukcja dopuszczalna tylko przy systemie zapewnienia jakości (4.4.1.3(3)).');
  if (m.c_nom_user != null && m.c_nom_user <= 0) err('Otulina nominalna musi być dodatnia.', 'materials.c_nom_user');
  if (!(m.d_g >= 4 && m.d_g <= 63)) err('Wymiar kruszywa d_g poza zakresem 4–63 mm.', 'materials.d_g');
  const mb = v.reinforcement.main;
  if (!mb.auto) {
    if (!(mb.phi > 0) || mb.n_per_layer < 1 || mb.layers < 1) err('Nieprawidłowe parametry zbrojenia głównego.', 'reinforcement.main');
    if (mb.layers > 3) err('Program obsługuje maksymalnie 3 warstwy zbrojenia głównego.', 'reinforcement.main.layers');
    if (mb.anchor_load === 'loop' && mb.n_per_layer % 2) err('Pętle poziome wymagają parzystej liczby prętów w warstwie.', 'reinforcement.main.anchor_load');
  }
  if (mb.anchor_column === 'continuous' && g.layout !== 'double') err("Zakotwienie 'pręt ciągły' dotyczy wyłącznie wsporników dwustronnych.", 'reinforcement.main.anchor_column');
  const li = v.reinforcement.links;
  [['h_phi', li.h_phi], ['v_phi', li.v_phi], ['i_phi', li.i_phi]].forEach(([nm, val]) => { if (!(val > 0)) err(`Średnica strzemion ${nm} musi być dodatnia.`, 'reinforcement.links.' + nm); });
  if (li.h_count < 0 || li.v_count < 0 || li.i_count < 0) err('Liczba strzemion nie może być ujemna.');
  if (!(v.reinforcement.allowed_diameters || []).length) err('Brak dozwolonych średnic prętów dla doboru automatycznego.');
  const st = v.stm;
  if (st.node_10pct && !(st.node_10pct_justification || '').trim()) warn('Zwiększenie σ_Rd,max o 10% (6.5.4(5)) wymaga uzasadnienia — NIE zastosowano.');
  if (st.mode === 'manual' && !(st.manual && st.manual.nodes && st.manual.nodes.length)) err('Tryb ręczny modelu STM: brak węzłów.', 'stm.manual');
  v.loads.actions.forEach(a => { [['V', a.V], ['H', a.H], ['M', a.M], ['e_x', a.e_x], ['e_y', a.e_y]].forEach(([nm, val]) => { if (!isFinite(val)) err(`Oddziaływanie '${a.name}': wartość ${nm} nieskończona.`); }); });
  return msgs;
}
function postValidate(res) {
  const items = [];
  Object.entries(res.stm).forEach(([name, sr]) => {
    const sol = sr.solution; if (sol.status === 'error' || sol.status === 'mechanism') return;
    items.push({ name: 'Równowaga statyczna — ' + name, ok: sol.equilibrium_ok, detail: `max residuum węzłowe ${sol.max_residual.toExponential(2)} N; ΣFx=${sol.global_residual[0].toExponential(2)} N, ΣFy=${sol.global_residual[1].toExponential(2)} N, ΣM=${sol.global_residual[2].toExponential(2)} N·mm; status: ${sol.status}` });
    if (sr.comparison && Object.keys(sr.comparison).length) { const d = sr.comparison.max_rel_diff || 0; items.push({ name: 'Zgodność rozwiązania analitycznego i macierzowego — ' + name, ok: d <= 1e-6, detail: `maksymalna różnica względna ${d.toExponential(2)}` }); }
  });
  const bad = res.checks.filter(c => !(c.kind in WS.UNIT_OF)).map(c => c.id);
  items.push({ name: 'Zgodność jednostek (E_d i R_d tej samej wielkości)', ok: !bad.length, detail: bad.length ? bad.join(', ') : 'wszystkie sprawdzenia mają jednoznaczny wymiar' });
  const neg = res.checks.filter(c => c.R_d !== null && c.R_d < 0).map(c => c.id);
  items.push({ name: 'Dodatniość nośności / wartości granicznych', ok: !neg.length, detail: neg.join(', ') || 'OK' });
  const nan = res.checks.filter(c => c.eta !== null && Number.isNaN(c.eta)).map(c => c.id);
  items.push({ name: 'Brak wartości nieokreślonych (NaN)', ok: !nan.length, detail: nan.join(', ') || 'OK' });
  if (res.materials) {
    const c = res.materials.concrete, s = res.materials.steel;
    items.push({ name: "Poprawność współczynników (0 < ν' ≤ 1, γ ≥ 1, α_cc ≤ 1)", ok: c.nu_prime > 0 && c.nu_prime <= 1 && c.gamma_c >= 1 && s.gamma_s >= 1 && c.alpha_cc > 0 && c.alpha_cc <= 1, detail: `ν'=${c.nu_prime.toFixed(3)}, γ_c=${c.gamma_c}, γ_s=${s.gamma_s}, α_cc=${c.alpha_cc}` });
    const cons = WS.concreteConsistency(c);
    items.push({ name: 'Poprawność parametrów materiałowych (tabl. 3.1 vs wzory)', ok: !cons.length, detail: cons.join('; ') || 'zgodne' });
  }
  if (res.geometry) {
    const gm = res.geometry, ok = Object.values(gm.sides).every(s => s.h_c > 0 && s.l_c > 0 && s.h_e > 0) && gm.b > 0;
    items.push({ name: 'Poprawność geometrii (wymiary dodatnie, obrys zamknięty)', ok, detail: `${gm.outline().length} wierzchołków obrysu` });
  }
  return items;
}

/* ------------------------------------------------------------------ pomocnicze */
const M = (level, text, ref, source) => ({ level, text, ref: ref || '', source: source || '' });
function sideInputs(v) {
  const out = {};
  (v.geometry.layout === 'double' ? ['R', 'L'] : ['R']).forEach(sd => {
    const si = WS.sideInput(v.geometry, sd), u = v.stm.lever_arm === 'user';
    out[sd] = { a_H_user: si.a_H_user, d_user: si.d_user, x_c_user: u ? si.x_c_user : null, z0_user: u ? si.z0_user : null };
  });
  return out;
}
function merge(agg, c) {
  const old = agg.get(c.id);
  if (!old) { agg.set(c.id, c); return; }
  const rn = STATUS_RANK[c.status], ro = STATUS_RANK[old.status];
  if (rn > ro || (rn === ro && (c.eta || 0) > (old.eta || 0))) agg.set(c.id, c);
}
const sortChecks = list => list.sort((a, b) => { const ga = GROUP_ORDER.indexOf(a.group), gb = GROUP_ORDER.indexOf(b.group); const ka = ga < 0 ? 99 : ga, kb = gb < 0 ? 99 : gb; return ka - kb || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0); });
const errorsOf = res => res.messages.filter(m => m.level === 'error');
function critical(res) {
  const strength = c => STRENGTH_GROUPS.has(c.group) && !c.id.endsWith('_T81') && !c.id.endsWith('_LEG');
  const finf = res.checks.filter(c => c.status === ST.FAIL && (c.eta === null || !isFinite(c.eta)));
  if (finf.length) return finf[0];
  const cands = res.checks.filter(c => strength(c) && c.eta !== null && (c.status === ST.OK || c.status === ST.FAIL) && isFinite(c.eta));
  return cands.length ? cands.reduce((a, b) => b.eta > a.eta ? b : a) : null;
}

/* ------------------------------------------------------------------ zakotwienia: geometria i nośność */
function anchorGeometry(gm, sd, cv) {
  const sg = gm.sides[sd], near = gm.column_cover + gm.column_phi_link + gm.column_phi_long / 2, farIn = gm.h_col - gm.column_cover - gm.column_phi_link - gm.column_phi_long;
  return { load_start: sg.plate.xi_inner, load_end: sg.l_c - cv.c_nom, col_start: -near, col_end: -farIn, l_load: sg.l_c - cv.c_nom - sg.plate.xi_inner, l_col: farIn - near };
}
function mandrelAndAb(ml, cv, anchor, userM, ps) {
  const tmin = WS.mandrelMinTable(ml.phi, ps);
  if (anchor === 'loop') {
    const k = Math.floor(ml.n / 2), cc = ml.n >= 2 ? ml.z_positions[k] - ml.z_positions[k - 1] : 0;
    let ab = cv.c_top_main + ml.phi / 2; if (ml.layers > 1) ab = Math.min(ab, (ml.phi + ml.gap_v) / 2);
    return [cc - ml.phi, ab, `pętla najbardziej wewnętrzna: rozstaw osiowy ramion ${cc.toFixed(0)} mm`];
  }
  const phiM = userM != null ? userM : tmin, ab = Math.min(ml.n >= 2 ? ml.s_cc / 2 : Infinity, cv.c_side_main + ml.phi / 2);
  return [phiM, ab, userM != null ? 'przyjęta średnica trzpienia' : 'φ_m = φ_m,min wg tabl. 8.1N'];
}
function anchorSetup(gm, sd, ml, cv, mb, T, links, ps, double, dT) {
  const geo = anchorGeometry(gm, sd, cv), sg = gm.sides[sd];
  let sumAst = 0;
  if (links && mb.alpha3_mode === 'computed') links.v_positions.forEach(x => { if (x >= geo.load_start && x <= geo.load_end) sumAst += 2 * barArea(links.v_phi); });
  const base = { phi: ml.phi, As_prov: ml.As, force: T, a_clear: ml.n >= 2 ? ml.a_clear : 1e6, c1: cv.c_side_main, c: cv.c_top_main, bond: mb.bond, alpha3_mode: mb.alpha3_mode, K: mb.K_alpha3,
    sum_Ast: sumAst, phi_t: mb.welded_bar_phi, s_cc: ml.n >= 2 ? ml.s_cc : 0 };
  const ext = ps.v('hook_extension') * ml.phi;
  let loadBend = null, lLoad = geo.l_load, loadDesc = `od wewnętrznej krawędzi płyty (ξ = ${geo.load_start.toFixed(0)} mm) do zewnętrznej krawędzi pręta (ξ = ${geo.load_end.toFixed(0)} mm)`;
  if (mb.anchor_load === 'bend_down') {
    const [phiM, ab, how] = mandrelAndAb(ml, cv, 'bend_down', mb.mandrel_load, ps), r = (phiM + ml.phi) / 2, straight = geo.l_load - (r + ml.phi / 2), arc = Math.PI * r / 2;
    const legMax = sg.h_e - cv.c_nom - ml.phi / 2 - (cv.c_top_main + ml.phi / 2 + r);
    loadBend = [phiM, ab, how, r, straight, arc, legMax, mb.front_leg];
    lLoad = straight + arc + Math.max(0, Math.min(legMax, mb.front_leg != null ? mb.front_leg : legMax));
    loadDesc = 'wzdłuż osi pręta od wewnętrznej krawędzi płyty: odcinek prosty + łuk + ramię pionowe (rys. 8.1a)';
  } else if (mb.anchor_load === 'loop') loadBend = mandrelAndAb(ml, cv, 'loop', null, ps).concat([0, 0, 0, 0, null]);
  const aLoad = Object.assign({ id: 'ANCH_LOAD_' + sd, title: `Zakotwienie zbrojenia głównego od strony obciążenia (${SIDE_NAME[sd]})`, anchor: mb.anchor_load, l_avail: lLoad, element_ref: 'member:T' + sd }, base);
  let colBend = null, aCol, colDesc;
  if (double) {
    aCol = Object.assign({}, base, { id: 'ANCH_COL_DT', title: 'Przekazanie różnicy sił cięgien w słupie (pręty ciągłe)', anchor: 'continuous', l_avail: gm.h_col - 2 * gm.column_cover, element_ref: 'node:C', force: dT });
    colDesc = 'szerokość słupa w świetle otulin (pręty ciągłe przez słup)';
  } else {
    let lCol = geo.l_col;
    colDesc = 'od prętów pionowych przy bliższej krawędzi słupa do zewnętrznej krawędzi pręta przy dalszej krawędzi (wewnątrz prętów słupa) — J.3(4)';
    if (mb.anchor_column === 'bend_down') {
      const [phiM, ab, how] = mandrelAndAb(ml, cv, 'bend_down', mb.mandrel_column, ps), r = (phiM + ml.phi) / 2, straight = geo.l_col - (r + ml.phi / 2), arc = Math.PI * r / 2;
      const legMax = gm.below + sg.h_c - ml.c_t - r;
      colBend = [phiM, ab, how, r, straight, arc, legMax, mb.column_leg];
      lCol = straight + arc + Math.max(0, Math.min(legMax, mb.column_leg != null ? mb.column_leg : legMax));
      colDesc = 'wzdłuż osi pręta od prętów pionowych przy bliższej krawędzi słupa: odcinek poziomy + łuk + ramię pionowe w słupie (rys. 8.1a, J.3(4))';
    }
    aCol = Object.assign({ id: 'ANCH_COL_' + sd, title: 'Zakotwienie zbrojenia głównego w słupie', anchor: mb.anchor_column, l_avail: lCol, element_ref: 'member:T' + sd }, base);
  }
  return { load: aLoad, col: aCol, load_desc: loadDesc, col_desc: colDesc, load_bend: loadBend, col_bend: colBend, ext };
}
function anchorCapacity(a, mats, ps) {
  if (a.anchor === 'mechanical' || a.As_prov <= 0) return Infinity;
  const Fmax = a.As_prov * mats.steel.fyd, ok = F => WS.anchorageLength(Object.assign({}, a, { force: F }), mats, ps).lbd <= a.l_avail + 1e-9;
  if (ok(Fmax)) return Infinity;
  if (!ok(1e-3)) return 0;
  let lo = 0, hi = Fmax; for (let i = 0; i < 50; i++) { const mid = 0.5 * (lo + hi); if (ok(mid)) lo = mid; else hi = mid; }
  return lo;
}
function mandrelCapacity(ml, bend, mats, ps) {
  if (!bend) return Infinity;
  const [phiM, ab] = bend; if (phiM <= 0 || ab <= 0) return 0;
  const c = mats.concrete, fcd = Math.min(c.fcd, c.alpha_cc * ps.v('fcd_mandrel_cap') / c.gamma_c);
  return phiM * fcd / (1 / ab + 1 / (2 * ml.phi)) * ml.n * ml.layers;
}
function anchorCaps(gm, ml, cv, mb, mats, ps, double) {
  const caps = {};
  Object.keys(gm.sides).forEach(sd => {
    const su = anchorSetup(gm, sd, ml, cv, mb, 0, null, ps, double, 0);
    let c = Math.min(anchorCapacity(su.load, mats, ps), mandrelCapacity(ml, su.load_bend, mats, ps));
    if (!double) c = Math.min(c, anchorCapacity(su.col, mats, ps), mandrelCapacity(ml, su.col_bend, mats, ps));
    caps[sd] = c;
  });
  return caps;
}
function bendChecks(prefix, title, bend, ml, Fbt, mats, ps, combo, ref, lbd, ext, depthLabel) {
  const [phiM, ab, how, r, straight, arc, legMax, legUser] = bend;
  const out = WS.mandrelChecks(prefix, `${title} (${how})`, ml.phi, phiM, Fbt, ab, mats, ps, combo, ref);
  if (legMax <= 0 && straight === 0 && arc === 0) return [out, 0];
  let leg;
  if (legUser != null) leg = legUser;
  else { const need = lbd != null ? lbd - straight - arc : ext; leg = Math.ceil(Math.max(ext, need) / 10) * 10; if (leg > legMax) leg = Math.min(leg, Math.max(legMax, 0)); }
  out.push(make({ id: prefix + '_LEG', group: 'Wykonalność', title: title + ' — ramię pionowe za odgięciem', clause: 'EN 1992-1-1 §8.4.1, rys. 8.1b (przedłużenie ≥ 5φ); geometria elementu', basis: BASIS.NORMATIVE,
    formula: '5φ ≤ l_ramienia ≤ l_ramienia,max', symbols: { 'l_ramienia,max': depthLabel }, substitution: `l_ramienia = ${mm(leg)} (min. 5φ = ${mm(ext)}; max = ${mm(legMax)})`,
    E_d: Math.max(ext, leg), R_d: leg >= ext - 1e-9 ? Math.max(legMax, 0) : leg, kind: 'length', combination: combo, element_ref: ref, E_label: 'wymagane', R_label: 'dostępne' }));
  return [out, leg];
}
function anchorageChecks(gm, sd, ml, cv, mb, T, mats, ps, combo, links, double, dT) {
  let checks = []; const results = {}, sg = gm.sides[sd], geo = anchorGeometry(gm, sd, cv), su = anchorSetup(gm, sd, ml, cv, mb, T, links, ps, double, dT || 0);
  let reason = ''; const info = {};
  const sigma = ml.As > 0 ? Math.min(T / ml.As, mats.steel.fyd) : 0, Fbt = sigma * barArea(ml.phi);
  const lbdLoad = su.load.anchor !== 'mechanical' ? WS.anchorageLength(su.load, mats, ps).lbd : null;
  if (su.load_bend && su.load.anchor === 'bend_down') {
    const [cs, leg] = bendChecks('MANDREL_LOAD_' + sd, 'Gięcie zbrojenia głównego w dół na końcu wspornika', su.load_bend, ml, Fbt, mats, ps, combo, 'member:T' + sd, lbdLoad, su.ext, 'wysokość końca wspornika minus otuliny i promień gięcia');
    const [, , , , straight, arc, legMax] = su.load_bend;
    su.load.l_avail = straight + arc + Math.max(0, Math.min(leg, legMax));
    info.load = su.load_bend[0]; info.leg_front = leg; checks = checks.concat(cs);
  } else if (su.load_bend) {
    const [phiM, ab, how] = su.load_bend; info.load = phiM;
    checks = checks.concat(WS.mandrelChecks('MANDREL_LOAD_' + sd, `Gięcie pętli zbrojenia głównego (${how})`, ml.phi, phiM, Fbt, ab, mats, ps, combo, 'member:T' + sd));
  }
  const [c1, r1] = WS.anchorageCheck(su.load, mats, ps, combo, '; zał. J.3(4), §6.5.4(7)');
  c1.notes.push('Długość dostępna: ' + su.load_desc + ` = ${su.load.l_avail.toFixed(0)} mm.`);
  checks.unshift(c1); if (r1) results['load_' + sd] = r1;
  if (c1.status === ST.FAIL) reason = 'l_bd > l_dost (strona obciążenia)';
  const lbdCol = su.col.anchor !== 'mechanical' ? WS.anchorageLength(su.col, mats, ps).lbd : null;
  if (su.col_bend) {
    const [cs, leg] = bendChecks('MANDREL_COL_' + sd, 'Gięcie zbrojenia głównego w słupie', su.col_bend, ml, Fbt, mats, ps, combo, 'node:C', lbdCol, su.ext, 'długość słupa poniżej wspornika');
    const [, , , , straight, arc, legMax] = su.col_bend;
    su.col.l_avail = straight + arc + Math.max(0, Math.min(leg, legMax));
    info.column = su.col_bend[0]; info.leg_col = leg; checks = checks.concat(cs);
  }
  const [c2, r2] = WS.anchorageCheck(su.col, mats, ps, combo, '; zał. J.3(4)');
  c2.notes.push('Długość dostępna: ' + su.col_desc + ` = ${su.col.l_avail.toFixed(0)} mm.`);
  checks.splice(1, 0, c2); if (r2) results[c2.id] = r2;
  if (c2.status === ST.FAIL && !reason) reason = 'l_bd > l_dost (strona słupa)';
  const bad = checks.slice(2).find(c => c.status === ST.FAIL);
  if (bad && !reason) reason = bad.title;
  if (mb.anchor_load === 'loop' && ml.n % 2) {
    checks.push(make({ id: 'FIT_LOOP_' + sd, group: 'Wykonalność', title: 'Pętle poziome — parzysta liczba prętów', clause: 'Zasady konstruowania', basis: BASIS.NORMATIVE, formula: 'n parzyste', substitution: `n = ${ml.n}`, kind: 'none', combination: combo, element_ref: 'member:T' + sd, status: ST.FAIL }));
    reason = reason || 'nieparzysta liczba prętów dla pętli';
  }
  const na = make({ id: 'NODE_A_ANCH_' + sd, group: 'Zakotwienie', title: 'Zbrojenie główne przechodzi przez cały węzeł A (poza zewnętrzną krawędź płyty)', clause: 'EN 1992-1-1 §6.5.4(7)', basis: BASIS.NORMATIVE,
    formula: 'ξ_koniec pręta ≥ ξ_zewn. krawędź płyty', substitution: `ξ_koniec = ${mm(geo.load_end)}; ξ_płyta,zewn = ${mm(sg.plate.xi_outer)}`, E_d: sg.plate.xi_outer, R_d: geo.load_end, kind: 'length', combination: combo, element_ref: 'node:A' + sd, E_label: 'ξ_płyta', R_label: 'ξ_pręt' });
  checks.push(na);
  if (na.status === ST.FAIL && !reason) reason = 'pręty nie obejmują węzła A';
  return [checks, results, !reason, reason, info];
}
function designT(gm, combos, mats, ps, st, c_t, si) {
  const Tm = {};
  combos.forEach(c => {
    const r = WS.buildCorbelModel(gm, c, mats, ps, st, c_t, null, true, si);
    const e = r.messages.find(m => m[0] === 'error'); if (e) throw new StmModelError(e[1]);
    Object.entries(r.sides).forEach(([sd, sm]) => { Tm[sd] = Math.max(Tm[sd] || 0, sm.state.T); });
    Object.entries(c.sides).forEach(([sd, act]) => { if (act.V <= 1e-6 && act.H > 0) Tm[sd] = Math.max(Tm[sd] || 0, act.H); });
  });
  return Tm;
}

/* ------------------------------------------------------------------ tryb automatyczny */
function governingOf(stm) {
  let best = -1, g = '';
  Object.entries(stm).forEach(([name, r]) => Object.values(r.sides).forEach(sm => { const e = sm.state.eta_max(); if (e > best) { best = e; g = name; } }));
  return g || Object.keys(stm)[0] || '';
}
function linksLayouts(v, gm, ml, cv, li, gov, ps) {
  const out = {};
  Object.keys(gm.sides).forEach(sd => {
    const sm = gov ? gov.sides[sd] : null;
    out[sd] = WS.linksLayout(gm, sd, ml, cv, li, sm ? sm.params.d : gm.sides[sd].h_c - ml.c_t, sm ? sm.state.xi_A : gm.sides[sd].a_c, v.materials.d_g, ps);
  });
  return out;
}
function autoLinks(v, gm, ml, cv, li, stm, mats, ps, dlog) {
  const k1 = ps.v('J3_k1'), k2 = ps.v('J3_k2'), fywd = mats.steel.link_fyd;
  let needH = 0, needV = 0, split = 0, sinT = 1, cosT = 0, roomH = 0, roomV = 0;
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    Object.values(stm).forEach(r => {
      const sm = r.sides[sd]; if (!sm) return;
      const s = sm.state, strut = r.struts.find(x => x.id === 'S' + sd);
      if (strut && strut.shape === 'butelkowy') { const T = Math.max(...[s.w_A, s.w_B].map(a => WS.splittingForce(s.C, a, strut.b_avail, strut.length)[0])); if (T > split) { split = T; sinT = Math.sin(s.theta); cosT = Math.cos(s.theta); } }
      if (sg.a_c > 0.5 * sg.h_c) { const [Vc] = WS.vrdc(gm.b, sm.params.d, ml.As, Math.max(sm.params.H, 0), sg.h_c, mats, ps); if (sm.params.V > Vc) needV = Math.max(needV, k2 * sm.params.V / fywd); }
    });
    if (sg.a_c < 0.5 * sg.h_c) needH = Math.max(needH, k1 * ml.As);
    const d = sg.h_c - ml.c_t, zone = li.h_zone != null ? li.h_zone : ps.v('h_link_zone') * d;
    const yFirst = ml.layer_depths[ml.layer_depths.length - 1] + ml.phi / 2 + ml.s_min, yEnd = Math.min(ml.c_t + zone, sg.h_c - cv.c_nom - 8);
    const pitch = 16 + WS.sMin(16, v.materials.d_g, ps);
    const rh = yEnd >= yFirst ? Math.floor(Math.max(0, yEnd - yFirst) / pitch) + 1 : 0; roomH = roomH === 0 ? rh : Math.min(roomH, rh);
    const xs = sg.a_c - (cv.c_nom + 25), rv = xs > 0 ? Math.floor(Math.max(0, xs) / pitch) + 1 : 0; roomV = roomV === 0 ? rv : Math.min(roomV, rv);
  });
  return WS.designLinks(needH, needV, split, sinT, cosT, fywd, li, roomH, roomV, dlog);
}
function modelAssumptions(v) {
  const st = v.stm, a = [
    'Model STM wg EN 1992-1-1 zał. J.3, rys. J.5: węzeł A (CCT) pod obciążeniem na osi cięgna, węzeł B (CCC) w strefie ściskanej przy licu słupa, cięgno zakotwione w słupie.',
    st.node_b_position === 'in_column' ? 'Węzeł B umieszczony w słupie (pozioma ścianka węzła przekazuje V na słup), ξ_B = −a_B/2 — założenie inżynierskie (konserwatywne względem rys. J.5).' : 'Węzeł B na licu słupa (ξ_B = 0) — zgodnie z rys. J.5.',
    { optimal: 'Wysokość strefy ściskanej x_c dobierana jako najkorzystniejsze dopuszczalne pole naprężeń (minimalizacja maksymalnego wykorzystania przy 1,0 ≤ tan θ ≤ 2,5) — twierdzenie o dolnej ocenie nośności.',
      node_limit: 'Wysokość strefy ściskanej x_c z warunku σ_B = min(σ_Rd,max węzła CCC; σ_Rd,max krzyżulca).', user: 'Wysokość strefy ściskanej x_c / ramię z0 przyjęte przez użytkownika.' }[st.lever_arm],
    `Nośność krzyżulca wg ${st.strut_limit === '6.56' ? '(6.56): 0,6·ν′·f_cd (strefa zarysowana)' : '(6.55): f_cd'}.`,
    st.include_aH ? 'Siła pozioma H przyłożona na górnej powierzchni płyty oporowej (a_H = c_t + t_p), wypadkowa (V, H) przecina oś cięgna w węźle A.' : 'Pominięto ramię a_H siły poziomej.',
    st.neglect_favourable_H ? 'Korzystne działanie siły H skierowanej do słupa jest pomijane.' : 'Uwzględniono siłę H skierowaną do słupa (zmniejsza siłę w cięgnie).',
    `Warunki przyczepności zbrojenia głównego: ${v.reinforcement.main.bond === 'good' ? 'dobre (η₁ = 1,0)' : 'słabe (η₁ = 0,7) — założenie konserwatywne dla prętów górnych'}.`,
    'Grubość efektywna węzła A i krzyżulca przy A równa szerokości płyty oporowej b_p (bez rozchodzenia w kierunku szerokości) — założenie bezpieczne.',
  ];
  if (st.node_10pct && (st.node_10pct_justification || '').trim()) a.push('Zwiększenie σ_Rd,max węzłów o 10% (6.5.4(5)) — uzasadnienie: ' + st.node_10pct_justification);
  return a;
}
function columnTransfer(r, combo, v) {
  const parts = Object.keys(r.solution.reactions).sort().map(nid => { const [rx, ry] = r.solution.reactions[nid]; return `${nid}: R_x = ${kN(rx)}, R_y = ${kN(ry)}`; });
  const N = v.geometry.column.N_Ed;
  return make({ id: 'COLUMN_TRANSFER', group: 'Poza zakresem', title: 'Przekazanie sił ze wspornika na słup', clause: 'EN 1992-1-1 §6.5, J.3(4); nośność słupa — rozdz. 6.1, 5.8', basis: BASIS.MODEL,
    formula: 'reakcje modelu lokalnego = obciążenie strefy słupa', substitution: parts.join('; ') + (N ? `; N_Ed słupa = ${kN(N)} (informacyjnie)` : ''), kind: 'force', combination: combo, element_ref: 'node:C', status: ST.VERIFY,
    conclusion: 'Siły przekazywane na słup wymagają sprawdzenia słupa i jego strefy węzłowej — wynik STM wspornika nie potwierdza nośności słupa.' });
}
function scopeChecks(v, res, gm, mats, ps, ml, uls) {
  const out = [], all = []; uls.forEach(c => Object.values(c.sides).forEach(a => all.push(a)));
  const Hany = all.some(a => Math.abs(a.H) > 1e-6), eyAny = all.some(a => Math.abs(a.e_y) > 1e-6), precast = v.geometry.construction === 'precast';
  const Hmax = all.length ? Math.max(...all.map(a => a.H)) : 0;
  if (Hany) out.push(make({ id: 'H_EFFECT', group: 'Mechanizmy dodatkowe', title: 'Wpływ siły poziomej H_Ed', clause: 'EN 1992-1-1 zał. J.3, rys. J.5', basis: BASIS.INFORMATIVE, formula: 'F_td = F_Ed·a_c/z0 + H_Ed·(a_H + z0)/z0 — uwzględnione w modelu',
    substitution: `Maksymalna siła pozioma w kombinacjach SGN: ${kN(Hmax)} — uwzględniona w równowadze węzła A i sile w cięgnie.`, kind: 'force', element_ref: 'model', status: ST.OK, conclusion: 'Wpływ siły poziomej uwzględniony w modelu STM.' }));
  else if (precast && !v.geometry.precast.restraint_considered) out.push(make({ id: 'H_EFFECT', group: 'Mechanizmy dodatkowe', title: 'Wpływ siły poziomej H_Ed (połączenie prefabrykowane)', clause: 'EN 1992-1-1 §10.9.5 (oparcia elementów prefabrykowanych) — zalecenie', basis: BASIS.ENGINEERING,
    formula: 'H_Ed od więzów (skurcz, pełzanie, temperatura)', substitution: 'Brak siły poziomej w połączeniu prefabrykowanym i brak potwierdzenia, że oddziaływania od więzów zostały rozważone.', kind: 'force', element_ref: 'model', status: ST.VERIFY }));
  else out.push(make({ id: 'H_EFFECT', group: 'Mechanizmy dodatkowe', title: 'Wpływ siły poziomej H_Ed', clause: 'EN 1992-1-1 zał. J.3', basis: BASIS.INFORMATIVE, formula: '—', substitution: 'Brak siły poziomej w kombinacjach SGN.', kind: 'force', element_ref: 'model', status: ST.NA }));
  out.push(make({ id: 'TORSION', group: 'Poza zakresem', title: 'Skręcanie od mimośrodu poprzecznego', clause: 'EN 1992-1-1 §6.3', basis: BASIS.NORMATIVE, formula: 'T_Ed = V_Ed·e_y',
    substitution: eyAny ? 'Występuje mimośród poprzeczny e_y — skręcanie wspornika i słupa wymaga osobnej weryfikacji.' : 'Brak mimośrodu poprzecznego.', kind: 'moment', element_ref: 'model', status: eyAny ? ST.VERIFY : ST.NA }));
  out.push(make({ id: 'PLATE_STEEL', group: 'Poza zakresem', title: 'Płyta oporowa / łożysko / spoiny', clause: 'EN 1993-1-8, EN 1337', basis: BASIS.NORMATIVE, formula: '—', substitution: 'Nośność płyty stalowej, łożyska i połączeń stalowych nie jest sprawdzana przez program.', kind: 'none', element_ref: 'model', status: ST.VERIFY }));
  if (precast) {
    const pc = v.geometry.precast, keys = [pc.dry_connection ? 'fRd_dry' : 'fRd_other', 'table_10_2'], confirmed = keys.every(k => ps.isConfirmed(k)), c = mats.concrete;
    Object.entries(gm.sides).forEach(([sd, sg]) => {
      const Vs = uls.filter(cc => cc.sides[sd]).map(cc => cc.sides[sd].V), Vmax = Vs.length ? Math.max(...Vs) : 0;
      let fRd, ftxt;
      if (pc.dry_connection) { fRd = ps.v('fRd_dry') * c.fcd; ftxt = `f_Rd = 0,4·f_cd = ${MPa(fRd)} (połączenie na sucho)`; }
      else { fRd = pc.f_bed > 0 ? Math.min(pc.f_bed, ps.v('fRd_other') * c.fcd) : ps.v('fRd_other') * c.fcd; ftxt = `f_Rd = min(f_bed; 0,85·f_cd) = ${MPa(fRd)}`; }
      const b1 = sg.plate.width, a1 = fRd > 0 ? Vmax / (b1 * fRd) : Infinity, rel = (Vmax / (sg.plate.length * b1)) / c.fcd;
      const col = rel <= 0.15 ? 0 : rel <= 0.4 ? 1 : 2, a1min = ND.t102[pc.support_type][col], a1req = Math.max(a1, a1min);
      out.push(make({ id: 'PRECAST_BEARING_' + sd, group: 'Połączenia prefabrykowane', title: `Długość oparcia netto a₁ elementu prefabrykowanego (${SIDE_NAME[sd]})`, clause: 'EN 1992-1-1 §10.9.5.2, wzór (10.6), tabl. 10.2', basis: BASIS.NORMATIVE,
        formula: 'a₁ = F_Ed/(b₁·f_Rd) ≥ a₁,min (tabl. 10.2);  a₁ ≤ a_p', symbols: { 'b₁': 'szerokość oparcia netto', f_Rd: 'obliczeniowa wytrzymałość na docisk' },
        substitution: `${ftxt}; a₁ = ${kN(Vmax)}·10³/(${n(b1, 0)}·${n(fRd)}) = ${mm(a1, 1)}; σ_Ed/f_cd = ${n(rel, 3)} → a₁,min = ${mm(a1min)}; a₁,req = ${mm(a1req, 1)}; a_p = ${mm(sg.plate.length)}`,
        E_d: a1req, R_d: sg.plate.length, kind: 'length', combination: 'obwiednia SGN', element_ref: 'node:A' + sd,
        notes: ["Wartości tabl. 10.2 i f_Rd wymagają potwierdzenia z treścią normy (parametry 'fRd_dry'/'fRd_other' w zakładce Parametry normowe). Odległości a₂, a₃ i tolerancje Δa₂, Δa₃ (tabl. 10.3–10.5) — do sprawdzenia przez projektanta."],
        status: confirmed ? undefined : ST.VERIFY, E_label: 'a₁,req', R_label: 'a_p' }));
    });
    out.push(make({ id: 'PRECAST_OTHER', group: 'Połączenia prefabrykowane', title: 'Pozostałe wymagania połączeń prefabrykowanych (a₂, a₃, Δa, zabezpieczenie przed zsunięciem)', clause: 'EN 1992-1-1 §10.9.4, §10.9.5', basis: BASIS.NORMATIVE, formula: '—',
      substitution: 'Wymagania geometryczne oparcia (tabl. 10.3–10.5), przesunięcia i zabezpieczenia połączenia wymagają osobnej weryfikacji.', kind: 'none', element_ref: 'model', status: ST.VERIFY }));
  } else out.push(make({ id: 'PRECAST_BEARING', group: 'Połączenia prefabrykowane', title: 'Wymagania dla połączeń prefabrykowanych', clause: 'EN 1992-1-1 §10.9.5', basis: BASIS.NORMATIVE, formula: '—', substitution: 'Wspornik monolityczny.', kind: 'none', element_ref: 'model', status: ST.NA }));
  if (v.reinforcement.links.i_count === 0) out.push(make({ id: 'J35_INCLINED', group: 'Zbrojenie poprzeczne', title: 'Strzemiona ukośne przy narożu wklęsłym (rysy)', clause: 'EN 1992-1-1 zał. J.3(5)', basis: BASIS.INFORMATIVE, formula: '—',
    substitution: 'Przy szczególnych wymaganiach ograniczenia rys skuteczne są strzemiona ukośne w narożu wklęsłym — nie zastosowano (decyzja projektanta).', kind: 'none', element_ref: 'rebar:links', status: ST.NA }));
  return out;
}
function interp(table, sigma, col) {
  const keys = Object.keys(table).map(Number).sort((a, b) => a - b), val = k => table[String(k)] !== undefined ? table[String(k)][col] : table[k.toFixed(1)][col];
  if (sigma <= keys[0]) return val(keys[0]);
  if (sigma > keys[keys.length - 1]) return null;
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (sigma >= a && sigma <= b) { const va = val(a), vb = val(b); if (va === null || vb === null) return null; return va + (vb - va) * (sigma - a) / (b - a); }
  }
  return null;
}
function slsChecks(v, res, gm, mats, ps, ml, sls, gov, si) {
  const out = [];
  if (!sls.length || !gov) {
    out.push(make({ id: 'SLS_CRACK', group: 'SGU', title: 'Ograniczenie zarysowania cięgna', clause: 'EN 1992-1-1 §7.3', basis: BASIS.NORMATIVE, formula: '—',
      substitution: 'Brak kombinacji quasi-stałej SGU (obciążenia podane jako wartości obliczeniowe) — kontrola rys nie została wykonana.', kind: 'stress', element_ref: 'rebar:main', status: ST.VERIFY }));
    return out;
  }
  const exp = v.materials.exposure, wmax = ['X0', 'XC1'].includes(exp) ? ps.v('wmax_X0_XC1') : ps.v('wmax_other');
  const col = { '0.4': 0, '0.3': 1, '0.2': 2 }[(Math.round(wmax * 10) / 10).toFixed(1)]; const cc = col === undefined ? 1 : col;
  const stU = Object.assign(clone(v.stm), { lever_arm: 'user' });
  sls.forEach(c => {
    const s2 = {}; Object.keys(gov.sides).forEach(sd => { s2[sd] = Object.assign({}, si[sd] || {}, { x_c_user: gov.sides[sd].state.x_c, z0_user: null }); });
    const r = WS.buildCorbelModel(gm, c, mats, ps, stU, ml.c_t, ml.As, false, s2);
    Object.entries(r.sides).forEach(([sd, sm]) => {
      const sig = sm.state.T / ml.As; res.sls[c.name + ':' + sd] = sig;
      const phiMax = interp(ND.t72N, sig, cc), sMax = interp(ND.t73N, sig, cc);
      const okPhi = phiMax !== null && ml.phi <= phiMax + 1e-9, okS = sMax !== null && ml.s_cc <= sMax + 1e-9;
      out.push(make({ id: 'SLS_CRACK_' + sd, group: 'SGU', title: `Ograniczenie zarysowania — cięgno ${SIDE_NAME[sd]} (uproszczone)`, clause: 'EN 1992-1-1 §7.3.3(2), tabl. 7.1N, 7.2N, 7.3N', basis: BASIS.NORMATIVE,
        formula: 'φ ≤ φ*_s(σ_s) lub s ≤ s_max(σ_s);  σ_s = T_qp / A_s', symbols: { 'σ_s': 'naprężenie w zbrojeniu w kombinacji quasi-stałej (x_c jak w SGN)' },
        substitution: `T_qp = ${kN(sm.state.T)}; σ_s = ${MPa(sig, 1)}; w_max = ${n(wmax, 1)} mm → φ*_s = ${phiMax === null ? '—' : mm(phiMax, 1)} (φ = ${mm(ml.phi)}), s_max = ${sMax === null ? '—' : mm(sMax, 0)} (s = ${mm(ml.s_cc, 0)})`,
        kind: 'stress', combination: c.name, element_ref: 'member:T' + sd, status: (okPhi || okS) ? ST.OK : ST.FAIL,
        notes: ["Tablice zastosowano bez korekt (7.6N)/(7.7N) — kontrola orientacyjna; moduł o statusie 'nieweryfikowany'."] }));
    });
  });
  return out;
}
function allChecks(v, res, ps, gm, mats, cv, ml, mb, li, lls, stm, uls, sls, si, double) {
  const agg = new Map(), st = v.stm, Tmax = {}, Vmax = {}, fywd = mats.steel.link_fyd; let dT = 0;
  res.messages = res.messages.filter(m => m.source !== 'model');
  const seen = new Set(), msg = (lv, t, ref) => { if (!seen.has(t)) { seen.add(t); res.messages.push(M(lv, t, ref, 'model')); } };
  uls.forEach(c => {
    const r = stm[c.name];
    r.messages.forEach(m => msg(m[0], `[${c.name}] ${m[1]}`, m[2]));
    const sol = r.solution;
    if (sol.status !== 'error') {
      merge(agg, make({ id: 'MODEL_STABILITY', group: 'Model', title: 'Stateczność / wyznaczalność modelu kratownicowego', clause: 'EN 1992-1-1 §5.6.4, §6.5.1 — kontrola modelu', basis: BASIS.MODEL,
        formula: 'rank(A) = liczba równań; stopień niewyznaczalności m + r − 2w', symbols: { A: 'macierz równowagi węzłów' },
        substitution: `rank(A) = ${sol.rank}, równań ${sol.n_equations}, niewiadomych ${sol.n_unknowns}, stopień = ${sol.degree}; status: ${sol.status}`, kind: 'none', combination: c.name, element_ref: 'model',
        status: sol.stable ? ST.OK : ST.FAIL, conclusion: sol.status === 'determinate' ? 'Model geometrycznie niezmienny i statycznie wyznaczalny.' : sol.stable ? 'Model niewyznaczalny — siły zależne od sztywności.' : 'Model ZMIENNY — wynik pozytywny zablokowany.' }));
      const resid = Math.max(sol.max_residual, Math.abs(sol.global_residual[0]), Math.abs(sol.global_residual[1]));
      merge(agg, make({ id: 'MODEL_EQUILIBRIUM', group: 'Model', title: 'Residuum równowagi węzłów i równowaga globalna', clause: 'Kontrola numeryczna modelu', basis: BASIS.MODEL, formula: 'max|A·f + P| ≤ tol; ΣF = 0; ΣM = 0',
        substitution: `max residuum = ${resid.toExponential(3)} N; tol = ${sol.tolerance.toExponential(3)} N; ΣM = ${sol.global_residual[2].toExponential(3)} N·mm; różnica rozw. analitycznego i macierzowego = ${(r.comparison.max_rel_diff || 0).toExponential(2)}`,
        E_d: resid, R_d: sol.tolerance, kind: 'force', combination: c.name, element_ref: 'model', E_label: 'residuum', R_label: 'tol' }));
    }
    Object.entries(r.sides).forEach(([sd, sm]) => {
      const s = sm.state, p = sm.params, strut = r.struts.find(x => x.id === 'S' + sd);
      WS.strutChecks(sm, strut, mats, ps, st, c.name).forEach(k => merge(agg, k));
      WS.nodeChecks(sm, mats, ps, st, c.name).forEach(k => merge(agg, k));
      WS.tieChecks(sm, ml.As, ml.desc(), ml.c_t, mats, ps, c.name).forEach(k => merge(agg, k));
      merge(agg, WS.localBearingCheck(gm, sm, mats, ps, c.name));
      const ll = lls[sd], [nh, nv] = ll ? WS.linksCrossingStrut(ll, gm, sd, cv, s.xi_A, s.y_A, s.xi_B, s.y_B) : [0, 0];
      const Rl = ll ? nh * 2 * barArea(ll.h_phi) * fywd * Math.sin(s.theta) + nv * 2 * barArea(ll.v_phi) * fywd * Math.cos(s.theta) : 0;
      const desc = `${nh}×2·${n(ll ? barArea(ll.h_phi) : 0, 1)}·${n(fywd, 1)}·sin θ + ${nv}×2·${n(ll ? barArea(ll.v_phi) : 0, 1)}·${n(fywd, 1)}·cos θ`;
      merge(agg, WS.splittingCheck(sm, strut, Rl, desc, c.name)[0]);
      merge(agg, make({ id: 'J3_SCOPE_' + sd, group: 'Model', title: `Zakres modelu krótkiego wspornika: a_c < z0 (${SIDE_NAME[sd]})`, clause: 'EN 1992-1-1 zał. J.3(1)', basis: BASIS.INFORMATIVE, formula: 'a_c < z0',
        symbols: { a_c: 'odległość obciążenia od lica słupa', z0: 'ramię sił wewnętrznych' }, substitution: `a_c,ef = ${mm(p.xi_A, 1)} (z uwzgl. M i H·a_H); z0 = ${mm(s.z0, 1)}`,
        E_d: p.xi_A, R_d: s.z0, kind: 'length', combination: c.name, element_ref: 'member:S' + sd, recommendation: true, E_label: 'a_c', R_label: 'z0', notes: sm.feasible ? [] : [sm.infeasible_reason] }));
      if (!sm.feasible) msg('warning', `Strona ${sd}: ${sm.infeasible_reason}`, 'side:' + sd);
      const cont = r.containment, keys = ['strut_lower', 'strut_upper', 'node_A', 'node_B'], bad = keys.filter(k => cont[k + '_' + sd] === false), okc = !bad.length;
      merge(agg, make({ id: 'CONTAIN_' + sd, group: 'Model', title: `Pole naprężeń mieści się w obrysie betonu (${SIDE_NAME[sd]})`, clause: 'Spójność geometrii modelu (6.5.1) — krzyżulce i węzły w obrysie', basis: BASIS.MODEL,
        formula: 'krawędzie krzyżulca i strefy węzłowe w obrysie wspornika/słupa', substitution: okc ? 'Wszystkie elementy pola naprężeń leżą w obrysie.' : 'Poza obrysem: ' + bad.join(', ') + ' — geometria (np. skos dolnej krawędzi) niezgodna z przyjętym modelem.',
        kind: 'none', combination: c.name, element_ref: 'member:S' + sd, status: okc ? ST.OK : ST.FAIL }));
      if (st.node_b_position === 'in_column') {
        const lim = double ? gm.h_col / 2 : gm.h_col;
        merge(agg, make({ id: 'NODE_B_FIT_' + sd, group: 'Model', title: `Strefa węzła B${sd} mieści się w słupie`, clause: 'Spójność geometrii modelu', basis: BASIS.MODEL, formula: 'a_B ≤ h_col (dwustronne: a_B ≤ h_col/2)',
          substitution: `a_B = ${mm(s.a_B, 1)}; limit = ${mm(lim)}`, E_d: s.a_B, R_d: lim, kind: 'length', combination: c.name, element_ref: 'node:B' + sd, E_label: 'a_B', R_label: 'limit' }));
      }
      Tmax[sd] = Math.max(Tmax[sd] || 0, s.T);
      if (p.V > (Vmax[sd] ? Vmax[sd][0] : 0)) Vmax[sd] = [p.V, p.H, p.d];
    });
    if (double) { const Ts = {}; Object.entries(r.sides).forEach(([sd, sm]) => { Ts[sd] = sm.state.T; }); dT = Math.max(dT, Math.abs((Ts.R || 0) - (Ts.L || 0))); }
    const Tt = Object.values(r.sides).length ? Math.max(...Object.values(r.sides).map(sm => sm.state.T)) : 0;
    merge(agg, WS.nodeCCheck(Tt, c.name, double));
    merge(agg, columnTransfer(r, c.name, v));
  });
  uls.forEach(c => Object.entries(c.sides).forEach(([sd, a]) => { if (a.V <= 1e-6 && a.H > 0) Tmax[sd] = Math.max(Tmax[sd] || 0, a.H); }));
  const gov = stm[governingOf(stm)];
  res.anchorage = {}; res.mandrels = {};
  Object.keys(gm.sides).forEach(sd => {
    const [cks, ares, , , mand] = anchorageChecks(gm, sd, ml, cv, mb, Tmax[sd] || 0, mats, ps, 'obwiednia SGN', lls[sd], double, dT);
    cks.forEach(k => merge(agg, k)); Object.assign(res.anchorage, ares); Object.assign(res.mandrels, mand);
  });
  WS.coverChecks(cv, ml.phi).forEach(k => merge(agg, k));
  Object.keys(gm.sides).forEach(sd => WS.spacingChecks(ml, lls[sd], sd).forEach(k => merge(agg, k)));
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    const d = sg.h_c - ml.c_t;
    WS.minMaxChecks(gm.b, d, sg.h_c, ml.As, mats, ps, sd).forEach(k => merge(agg, k));
    if (Vmax[sd]) {
      const [Vd, Hd, dd] = Vmax[sd], [Vc, vtxt] = WS.vrdc(gm.b, dd, ml.As, Math.max(Hd, 0), sg.h_c, mats, ps);
      WS.j3LinkChecks(sd, sg.a_c, sg.h_c, Vd, Vc, vtxt, ml, lls[sd], mats, ps, 'obwiednia SGN').forEach(k => merge(agg, k));
      const c_ = mats.concrete, VR = ps.v('shear_max_factor') * gm.b * dd * c_.nu_shear * c_.fcd;
      merge(agg, make({ id: 'SHEAR_MAX_' + sd, group: 'Mechanizmy dodatkowe', title: `Graniczna siła poprzeczna przy licu słupa (${SIDE_NAME[sd]})`, clause: 'EN 1992-1-1 §6.2.2(6), wzory (6.5), (6.6N)', basis: BASIS.NORMATIVE,
        formula: 'V_Ed ≤ 0,5·b_w·d·ν·f_cd;  ν = 0,6·(1 − f_ck/250)', symbols: { b_w: 'szerokość wspornika', d: 'wysokość użyteczna przy licu' },
        substitution: `0,5·${n(gm.b, 0)}·${n(dd, 0)}·${n(c_.nu_shear, 3)}·${n(c_.fcd)} = ${kN(VR)}; V_Ed = ${kN(Vd)}`, E_d: Vd, R_d: VR, kind: 'force', combination: 'obwiednia SGN', element_ref: 'member:S' + sd, E_label: 'V_Ed', R_label: 'V_Rd,max',
        notes: ['Sprawdzenie uzupełniające: obciążenie przyłożone w odległości ≤ 2d od podpory (słupa); nośność krzyżulców i węzłów sprawdzono w modelu STM.'] }));
      const hOut = sg.depth_at(sg.plate.xi_outer), ratio = ps.v('outer_depth_ratio');
      if (v.normative.apply_engineering_recommendations) merge(agg, make({ id: 'OUTER_DEPTH_' + sd, group: 'Konstrukcyjne', title: `Wysokość wspornika pod zewnętrzną krawędzią płyty (${SIDE_NAME[sd]})`, clause: ps.param('outer_depth_ratio').clause, basis: BASIS.ENGINEERING,
        formula: 'h(ξ_płyta,zewn) ≥ 0,5·h_c', substitution: `h = ${mm(hOut)}; 0,5·h_c = ${mm(ratio * sg.h_c)}`, E_d: ratio * sg.h_c, R_d: hOut, kind: 'length', element_ref: 'node:A' + sd, recommendation: true, E_label: '0,5·h_c', R_label: 'h_zewn' }));
    }
  });
  scopeChecks(v, res, gm, mats, ps, ml, uls).forEach(k => merge(agg, k));
  slsChecks(v, res, gm, mats, ps, ml, sls, gov, si).forEach(k => merge(agg, k));
  return sortChecks(Array.from(agg.values()));
}
function runAuto(v, res, ps) {
  const gm = res.geometry, mats = res.materials, st = v.stm, ri = v.reinforcement, double = v.geometry.layout === 'double';
  const uls = res.combinations.filter(c => c.is_uls), sls = res.combinations.filter(c => c.kind === 'SLS_QP'), si = sideInputs(v);
  const mb = clone(ri.main); let li = clone(ri.links);
  if (double) mb.anchor_column = 'continuous';
  const fyd = mats.steel.fyd;
  res.model_type = double ? 'J.3 — wsporniki dwustronne' : 'J.3 — wspornik jednostronny';
  res.assumptions = res.assumptions.concat(modelAssumptions(v));
  const Tc = new Map(), key = ct => ct.toFixed(6);
  const asReq = ct => { const k = key(ct); if (!Tc.has(k)) Tc.set(k, designT(gm, uls, mats, ps, st, ct, si)); const T = Tc.get(k), vals = Object.values(T); return vals.length ? Math.max(...vals) / fyd : 0; };
  const cvC = phi => WS.coverRequirements(v.materials, ps, phi, li.h_phi, li.v_phi, li.v_count > 0, li.h_count > 0);
  let lls = {}, prev = null, cv, ml, stm, sideChk;
  for (let outer = 0; outer < 4; outer++) {
    cv = cvC(mb.phi);
    if (ri.main.auto) {
      const dlog = [];
      const anchorOk = (mlT, anchor) => {
        let Tm = Tc.get(key(mlT.c_t)); if (!Tm || !Object.keys(Tm).length) Tm = designT(gm, uls, mats, ps, st, mlT.c_t, si);
        const trial = Object.assign(clone(mb), { anchor_load: anchor });
        for (const sd of Object.keys(gm.sides)) {
          const dT = double ? Math.abs((Tm.R || 0) - (Tm.L || 0)) : 0;
          const [, , ok, why] = anchorageChecks(gm, sd, mlT, cvC(mlT.phi), trial, Tm[sd] || 0, mats, ps, '', null, double, dT);
          if (!ok) return [false, why];
        }
        return [true, ''];
      };
      const cand = WS.designMainBars(gm, v.materials, ri, ps, asReq, anchorOk, dlog);
      if (!cand) {
        res.design_log = res.design_log.concat(dlog);
        const reasons = [];
        dlog.forEach(line => { const i = line.indexOf(' ('), j = line.lastIndexOf(')'); if (i >= 0 && j > i) { const r_ = line.slice(i + 2, j); if (!reasons.includes(r_)) reasons.push(r_); } });
        res.messages.push(M('error', 'Automatyczny dobór zbrojenia głównego: brak wykonalnego układu prętów. Przyczyny: ' + reasons.slice(0, 4).join('; ') + '. Zmień geometrię (wysięg, wysokość końca, położenie płyty), typ zakotwienia, klasę betonu lub dobierz zbrojenie ręcznie.', 'reinforcement.main'));
        return;
      }
      mb.phi = cand.phi; mb.n_per_layer = cand.n; mb.layers = cand.layers; mb.anchor_load = cand.anchor_load;
      cv = cvC(mb.phi);
      if (outer === 0) res.design_log = res.design_log.concat(dlog);
      res.design_log.push(`Przyjęto zbrojenie główne: ${cand.layout.desc()} (A_s = ${cand.layout.As.toFixed(0)} mm² ≥ A_s,req = ${cand.As_req.toFixed(0)} mm²), kotwienie: ${WS.ANCHOR_LABEL[cand.anchor_load]}.`);
    }
    ml = WS.mainLayout(gm.b, cv, mb.phi, mb.n_per_layer, mb.layers, mb.layer_gap, v.materials.d_g, ps);
    const caps = anchorCaps(gm, ml, cv, mb, mats, ps, double);
    sideChk = {}; Object.keys(gm.sides).forEach(sd => { sideChk[sd] = Object.assign({}, si[sd] || {}, { T_anch: caps[sd] }); });
    stm = {}; uls.forEach(c => { stm[c.name] = WS.buildCorbelModel(gm, c, mats, ps, st, ml.c_t, ml.As, false, sideChk); });
    const gov = governingOf(stm);
    if (ri.links.auto) li = autoLinks(v, gm, ml, cv, li, stm, mats, ps, res.design_log);
    lls = linksLayouts(v, gm, ml, cv, li, stm[gov], ps);
    const sig = [mb.phi, mb.n_per_layer, mb.layers, li.h_phi, li.h_count, li.v_phi, li.v_count].join('|');
    if (sig === prev || (!ri.main.auto && !ri.links.auto)) break;
    prev = sig;
  }
  let checks;
  for (let it = 0; it < 8; it++) {
    checks = allChecks(v, res, ps, gm, mats, cv, ml, mb, li, lls, stm, uls, sls, sideChk, double);
    if (!ri.links.auto) break;
    const more = checks.some(c => c.status === ST.FAIL && (c.id.startsWith('SPLIT_') || c.id.startsWith('J32_'))), needV = checks.some(c => c.status === ST.FAIL && c.id.startsWith('J33_'));
    if (!more && !needV) break;
    if (more) li.h_count++; if (needV) li.v_count++;
    res.design_log.push(`Korekta doboru strzemion: poziome ${li.h_count}×φ${li.h_phi.toFixed(0)}, pionowe ${li.v_count}×φ${li.v_phi.toFixed(0)}.`);
    lls = linksLayouts(v, gm, ml, cv, li, stm[governingOf(stm)], ps);
  }
  Object.assign(res, { cover: cv, main: ml, main_input: mb, links_input: li, links: lls, stm, governing: governingOf(stm), checks });
  try {
    res.schedule = WS.barSchedule(gm, ml, lls, cv, mb, { load: res.mandrels.load || WS.mandrelMinTable(ml.phi, ps), column: res.mandrels.column || WS.mandrelMinTable(ml.phi, ps),
      leg_front: mb.front_leg == null ? undefined : mb.front_leg, leg_col: mb.column_leg == null ? undefined : mb.column_leg }, v.materials.steel_name);
  } catch (e) { res.messages.push(M('warning', 'Zestawienie stali niekompletne: ' + e.message)); }
}

/* ------------------------------------------------------------------ tryb ręczny */
function runManual(v, res, ps) {
  const man = v.stm.manual, mats = res.materials, combo = 'model ręczny';
  res.model_type = 'Model STM zdefiniowany ręcznie';
  res.assumptions.push('Model STM zdefiniowany ręcznie przez użytkownika — obciążenia węzłowe są wartościami obliczeniowymi; kombinacje obciążeń projektu nie są stosowane do modelu ręcznego.');
  const truss = WS.buildManualModel(man), sol = WS.trussSolve(truss), agg = new Map();
  agg.set('MODEL_STABILITY', make({ id: 'MODEL_STABILITY', group: 'Model', title: 'Stateczność / wyznaczalność modelu kratownicowego', clause: 'EN 1992-1-1 §5.6.4 — kontrola modelu', basis: BASIS.MODEL, formula: 'rank(A) = liczba równań',
    substitution: `rank = ${sol.rank}, równań ${sol.n_equations}, niewiadomych ${sol.n_unknowns}; status: ${sol.status}. ` + sol.messages.join(' '), kind: 'none', combination: combo, element_ref: 'model', status: sol.stable ? ST.OK : ST.FAIL }));
  if (sol.stable) {
    const resid = Math.max(sol.max_residual, Math.abs(sol.global_residual[0]), Math.abs(sol.global_residual[1]));
    agg.set('MODEL_EQUILIBRIUM', make({ id: 'MODEL_EQUILIBRIUM', group: 'Model', title: 'Residuum równowagi', clause: 'Kontrola numeryczna', basis: BASIS.MODEL, formula: 'max|A·f + P| ≤ tol',
      substitution: `max residuum = ${resid.toExponential(3)} N; tol = ${sol.tolerance.toExponential(3)} N`, E_d: resid, R_d: sol.tolerance, kind: 'force', combination: combo, element_ref: 'model' }));
    WS.manualMemberChecks(truss, sol, man, mats, ps, v.stm, combo).forEach(k => agg.set(k.id, k));
    if (sol.status === 'indeterminate') res.messages.push(M('warning', 'Model ręczny statycznie niewyznaczalny — siły zależą od sztywności (EA krzyżulca = E·w·t, cięgna = E_s·A_s).'));
  } else res.messages.push(M('error', 'Model ręczny jest geometrycznie zmienny — ' + sol.messages.join(' ')));
  agg.set('MANUAL_SCOPE', make({ id: 'MANUAL_SCOPE', group: 'Poza zakresem', title: 'Sprawdzenia konstrukcyjne zbrojenia w trybie ręcznym', clause: 'EN 1992-1-1 rozdz. 8, 9', basis: BASIS.NORMATIVE, formula: '—',
    substitution: 'W trybie ręcznym zakotwienia, otulina, rozstaw i zbrojenie poprzeczne nie są sprawdzane automatycznie.', kind: 'none', combination: combo, element_ref: 'model', status: ST.VERIFY }));
  res.stm = { [combo]: { combination: combo, model_type: 'ręczny', truss, solution: sol, sides: {}, nodes: {}, struts: [], ties: [], comparison: { max_rel_diff: 0 }, messages: [], containment: {} } };
  res.governing = combo;
  res.checks = Array.from(agg.values()).sort((a, b) => a.group < b.group ? -1 : a.group > b.group ? 1 : (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/* ------------------------------------------------------------------ analiza */
function newResult(v) {
  return { variant_name: v.name, edition_id: '', edition_title: '', materials: null, geometry: null, cover: null, main: null, main_input: null, links_input: null, links: {}, combinations: [], stm: {},
    governing: '', checks: [], messages: [], assumptions: [], limitations: LIMITATIONS.slice(), design_log: [], schedule: [], anchorage: {}, mandrels: {}, verdict: null, validation: [], params_used: [],
    input_hash: '', fingerprint: '', model_type: '', sls: {}, geometry_signature: '' };
}
function finish(res, ndp) { res.verdict = buildVerdict(res.checks, errorsOf(res), ndp); res.fingerprint = resultFingerprint(res); return res; }
function analyze(v) {
  const res = newResult(v);
  res.input_hash = hashObj(v);
  let ps;
  try { ps = WS.getParameterSet(v.normative); } catch (e) { res.messages.push(M('error', e.message, 'normative', 'parametry normowe')); return finish(res, false); }
  res.edition_id = ps.edition.id; res.edition_title = ps.edition.title; res.ps = ps;
  res.messages = res.messages.concat(validateInput(v));
  try { res.geometry = WS.buildGeometry(v.geometry); res.geometry_signature = res.geometry.signature(); }
  catch (e) { res.messages.push(M('error', 'Błąd geometrii: ' + e.message)); }
  const ndp = !!v.normative.ndp_confirmed;
  if (errorsOf(res).length) return finish(res, ndp);
  try { res.materials = WS.buildMaterials(v.materials, ps); } catch (e) { res.messages.push(M('error', e.message, 'materials')); return finish(res, ndp); }
  const ev = WS.evaluateCombinations(v.loads, v.geometry, ps);
  res.combinations = ev.combos;
  ev.msgs.forEach(m => res.messages.push(Array.isArray(m) ? M(m[0], m[1], m[2] || '') : m));
  res.assumptions = res.assumptions.concat(ev.assumptions || []);
  if (errorsOf(res).length) return finish(res, ndp);
  try { if (v.stm.mode === 'manual') runManual(v, res, ps); else runAuto(v, res, ps); }
  catch (e) {
    if (e instanceof StmModelError) res.messages.push(M('error', 'Model STM: ' + e.message, 'stm'));
    else { res.messages.push(M('error', `Błąd wewnętrzny obliczeń: ${e.name}: ${e.message}`)); if (typeof console !== 'undefined') console.error(e); }
  }
  res.params_used = Array.from(ps.used).sort().map(k => ps.describe(k));
  if (!ndp) res.messages.push(M('warning', 'Parametry NDP nie zostały potwierdzone przez projektanta (sekcja Parametry normowe) — wynik ma charakter warunkowy.'));
  res.validation = postValidate(res);
  res.validation.forEach(it => { if (!it.ok) res.messages.push(M('error', `Walidacja automatyczna: ${it.name} — ${it.detail}`, 'validation')); });
  return finish(res, ndp);
}

/* ------------------------------------------------------------------ optymalizacja (design_optimizer) */
const OBJECTIVES = { steel: 'Minimalne zużycie stali [kg]', concrete: 'Minimalna objętość betonu wspornika [m³]', height: 'Minimalna wysokość wspornika h_c [mm]', length: 'Minimalna długość wysięgu l_c [mm]', cost: 'Minimalny koszt materiałów [zł]', eta: 'Najmniejsze maksymalne wykorzystanie η_max' };
const DEFAULT_CONCRETE_PRICE = { 'C20/25': 380, 'C25/30': 400, 'C30/37': 430, 'C35/45': 460, 'C40/50': 500, 'C45/55': 540, 'C50/60': 590 };
function rng(t, base) {
  if (!t) return [base];
  const [lo, hi, st] = t; if (!(st > 0) || hi < lo) return [base];
  const k = Math.round((hi - lo) / st) + 1; return Array.from({ length: k }, (_, i) => Math.round((lo + i * st) * 1e6) / 1e6);
}
function optEvaluate(v, s) {
  const r = analyze(v), g = v.geometry;
  const vol = r.geometry ? Object.values(r.geometry.sides).reduce((a, sd) => a + sd.area(), 0) * g.b / 1e9 : 0;
  const steel = r.schedule.reduce((a, b) => a + b.mass, 0), cost = steel * s.steel_price + vol * ((s.concrete_price || DEFAULT_CONCRETE_PRICE)[v.materials.concrete] || 450);
  const cr = critical(r), eta = cr && cr.eta !== null ? cr.eta : Infinity, fails = r.checks.filter(c => c.status === ST.FAIL).map(c => c.id);
  const code = r.verdict ? r.verdict.code : 'BLOCKED', errs = errorsOf(r), feasible = ['PASS_SCOPE', 'CONDITIONAL'].includes(code) && !fails.length && !errs.length;
  return { variant: v, h_c: g.right.h_c, h_e: g.right.h_e, l_c: g.right.l_c, b: g.b, concrete: v.materials.concrete, main: r.main ? r.main.desc() : '—',
    links: Object.keys(r.links).length ? Object.values(r.links).map(ll => ll.desc_h() + ', ' + ll.desc_v()).join('; ') : '—', steel_kg: steel, concrete_m3: vol, cost, eta_max: eta, verdict: code, feasible,
    reason: feasible ? '' : (errs.length ? errs[0].text : (fails.slice(0, 4).join(', ') || r.verdict.title)) };
}
function optGrid(base, s) {
  const g = base.geometry, grid = [], out = [];
  rng(s.h_c, g.right.h_c).forEach(hc => rng(s.l_c, g.right.l_c).forEach(lc => rng(s.b, g.b).forEach(b => (s.concretes && s.concretes.length ? s.concretes : [base.materials.concrete]).forEach(cls => grid.push([hc, lc, b, cls])))));
  grid.slice(0, s.max_variants || 400).forEach(([hc, lc, b, cls]) => {
    const v = clone(base), ratio = g.right.h_e / g.right.h_c;
    v.name = `${base.name} | h_c=${hc.toFixed(0)}, l_c=${lc.toFixed(0)}, b=${b.toFixed(0)}, ${cls}`;
    Object.assign(v.geometry.right, { h_c: hc, h_e: Math.round(hc * ratio * 10) / 10, x_slope: Math.min(v.geometry.right.x_slope, lc), l_c: lc, d_user: null, x_c_user: null, z0_user: null });
    v.geometry.b = b; v.geometry.right.plate.width = Math.min(v.geometry.right.plate.width, b); v.materials.concrete = cls;
    v.reinforcement.main.auto = true; v.reinforcement.links.auto = true;
    if (s.diameters && s.diameters.length) v.reinforcement.allowed_diameters = s.diameters.slice();
    out.push(v);
  });
  return { list: out, total: grid.length };
}
function optObjective(o, key) { return { steel: o.steel_kg, concrete: o.concrete_m3, height: o.h_c, length: o.l_c, cost: o.cost, eta: o.eta_max }[key]; }
function optSort(out) { return out.sort((a, b) => (a.feasible === b.feasible ? 0 : a.feasible ? -1 : 1) || a.objective - b.objective || a.eta_max - b.eta_max); }
function optimize(base, s, progress) {
  const g = base.geometry, grid = [];
  rng(s.h_c, g.right.h_c).forEach(hc => rng(s.l_c, g.right.l_c).forEach(lc => rng(s.b, g.b).forEach(b => (s.concretes && s.concretes.length ? s.concretes : [base.materials.concrete]).forEach(cls => grid.push([hc, lc, b, cls])))));
  const out = [], list = grid.slice(0, s.max_variants || 400);
  list.forEach(([hc, lc, b, cls], k) => {
    const v = clone(base), ratio = g.right.h_e / g.right.h_c;
    v.name = `${base.name} | h_c=${hc.toFixed(0)}, l_c=${lc.toFixed(0)}, b=${b.toFixed(0)}, ${cls}`;
    Object.assign(v.geometry.right, { h_c: hc, h_e: Math.round(hc * ratio * 10) / 10, x_slope: Math.min(v.geometry.right.x_slope, lc), l_c: lc, d_user: null, x_c_user: null, z0_user: null });
    v.geometry.b = b; v.geometry.right.plate.width = Math.min(v.geometry.right.plate.width, b); v.materials.concrete = cls;
    v.reinforcement.main.auto = true; v.reinforcement.links.auto = true;
    if (s.diameters && s.diameters.length) v.reinforcement.allowed_diameters = s.diameters.slice();
    const o = optEvaluate(v, s); o.objective = { steel: o.steel_kg, concrete: o.concrete_m3, height: o.h_c, length: o.l_c, cost: o.cost, eta: o.eta_max }[s.objective];
    out.push(o); if (progress) progress(k + 1, list.length);
  });
  out.sort((a, b) => (a.feasible === b.feasible ? 0 : a.feasible ? -1 : 1) || a.objective - b.objective || a.eta_max - b.eta_max);
  return out;
}

Object.assign(WS, { analyze, critical, errorsOf, buildVerdict, validateInput, postValidate, sha256, hashObj, resultFingerprint, LIMITATIONS, MODULE_STATUS, GROUP_ORDER, STRENGTH_GROUPS,
  anchorGeometry, anchorSetup, OBJECTIVES, DEFAULT_CONCRETE_PRICE, optimize, optGrid, optEvaluate, optObjective, optSort, governingOf });
})(typeof window !== 'undefined' ? window : globalThis);
