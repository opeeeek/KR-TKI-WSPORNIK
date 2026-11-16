/* KRÓTKI WSPORNIK ST – silnik obliczeń (część 1): narzędzia, parametry normowe, materiały, geometria,
   obciążenia i ogólny solver kratownic płaskich. Port 1:1 modułów Python kwst/* (wzorzec do testów krzyżowych).
   Jednostki wewnętrzne: N, mm, MPa (= N/mm²), N·mm. Działa w przeglądarce i w Node.js. */
(function (G) {
'use strict';
const WS = G.WS = G.WS || {};
const ND = G.WSN_DATA;

/* ------------------------------------------------------------------ narzędzia */
const n = (v, p) => { if (p === undefined) p = 2; if (v === null || v === undefined || !isFinite(v)) return v === Infinity ? '∞' : '—'; return v.toFixed(p).replace('.', ','); };
const kN = (v, p) => n(v / 1e3, p === undefined ? 1 : p) + ' kN';
const mm = (v, p) => n(v, p === undefined ? 0 : p) + ' mm';
const mm2 = (v, p) => n(v, p === undefined ? 0 : p) + ' mm²';
const MPa = (v, p) => n(v, p === undefined ? 2 : p) + ' MPa';
const barArea = phi => Math.PI * phi * phi / 4;
const barMass = phi => barArea(phi) * 1e-6 * 7850;
const SIDE_NAME = { R: 'prawy', L: 'lewy' };
const clone = o => JSON.parse(JSON.stringify(o));
Object.assign(WS, { n, kN, mm, mm2, MPa, barArea, barMass, SIDE_NAME, clone });

/* Statusy i podstawy sprawdzeń */
const ST = { OK: 'ok', FAIL: 'fail', VERIFY: 'warn', NA: 'na' };
const ST_LABEL = { ok: 'SPEŁNIONO', fail: 'NIE SPEŁNIONO', warn: 'WYMAGA OSOBNEJ WERYFIKACJI', na: 'NIE DOTYCZY' };
const BASIS = { NORMATIVE: 'normatywne', INFORMATIVE: 'informacyjne (zał. J EN 1992-1-1)', ENGINEERING: 'zalecenie inżynierskie', MODEL: 'kontrola modelu' };
const UNIT_OF = { force: 'kN', stress: 'MPa', length: 'mm', area: 'mm²', ratio: '', moment: 'kNm', none: '' };
const ETA_TOL = 1e-9;
Object.assign(WS, { ST, ST_LABEL, BASIS, UNIT_OF });

/* Rekord sprawdzenia — odpowiednik kwst.checks_common.make (wartości E_d, R_d w jednostkach bazowych) */
function make(o) {
  const c = {
    id: o.id, group: o.group, title: o.title, clause: o.clause, basis: o.basis, formula: o.formula || '',
    symbols: o.symbols || {}, substitution: o.substitution || '', E_d: o.E_d === undefined ? null : o.E_d,
    R_d: o.R_d === undefined ? null : o.R_d, kind: o.kind || 'none', eta: null, status: ST.NA,
    conclusion: o.conclusion || '', combination: o.combination || '', element_ref: o.element_ref || '',
    notes: (o.notes || []).slice(), E_label: o.E_label || 'E_d', R_label: o.R_label || 'R_d',
  };
  if (o.status) {
    c.status = o.status;
    if (c.E_d !== null && c.R_d !== null && c.R_d > 0) c.eta = c.E_d / c.R_d;
    if (!c.conclusion) c.conclusion = { na: 'Nie dotyczy.', warn: 'Wymaga osobnej weryfikacji poza zakresem programu.', ok: 'Warunek spełniony.', fail: 'Warunek NIE jest spełniony.' }[o.status];
    return c;
  }
  return evaluate(c, !!o.recommendation);
}
function evaluate(c, rec) {
  if (c.E_d === null || c.R_d === null) return c;
  if (c.R_d <= 0) c.eta = c.E_d > 0 ? Infinity : 0;
  else c.eta = Math.max(c.E_d, 0) / c.R_d;
  const ok = c.eta <= 1 + ETA_TOL;
  c.status = ok ? ST.OK : (rec ? ST.VERIFY : ST.FAIL);
  if (!c.conclusion) c.conclusion = ok ? 'Warunek spełniony.' : rec ? 'Zalecenie niespełnione — wymagana ocena projektanta.' : 'Warunek NIE jest spełniony.';
  return c;
}
WS.make = make;

/* ------------------------------------------------------------------ parametry normowe */
class EditionNotImplemented extends Error {}
function getParameterSet(norm) {
  const ed = ND.editions[norm.edition];
  if (!ed) throw new EditionNotImplemented('Nieznana edycja normy: ' + norm.edition);
  if (!ed.implemented) throw new EditionNotImplemented(`Edycja '${ed.title}' nie jest zaimplementowana — obliczenia niemożliwe.`);
  const params = {}; ed.params.forEach(p => { params[p.key] = p; });
  const values = {}; ed.params.forEach(p => { values[p.key] = p.value; });
  const over = norm.overrides || {};
  Object.keys(over).forEach(k => {
    if (!params[k]) throw new Error(`Parametr '${k}' nie należy do edycji ${ed.id}`);
    if (!params[k].editable) throw new Error(`Parametr '${k}' nie jest edytowalny`);
    values[k] = +over[k];
  });
  const used = new Set();
  return {
    edition: ed, input: norm, used,
    v(k) { if (!(k in values)) throw new Error(`Brak parametru '${k}' w edycji ${ed.id}`); used.add(k); return values[k]; },
    param: k => params[k],
    isOverridden: k => k in over,
    isConfirmed(k) { const p = params[k]; return p.blocking ? (norm.confirmed_params || []).includes(k) : true; },
    describe(k) {
      const p = params[k];
      return { key: k, symbol: p.symbol, value: values[k], unit: p.unit, clause: p.clause, category: ND.categoryLabel[p.category],
        recommended: p.recommended, status: (k in over) ? 'nadpisana przez użytkownika: ' + ((norm.override_notes || {})[k] || '—') : p.status,
        na_note: p.na_note, description: p.description, blocking: p.blocking, confirmed: this.isConfirmed(k) };
    },
  };
}
Object.assign(WS, { getParameterSet, EditionNotImplemented, ND });

/* ------------------------------------------------------------------ materiały */
const CONCRETE_CLASSES = Object.keys(ND.t31);
function concreteProps(cls, ps, situation) {
  if (!ND.t31[cls]) throw new Error('Nieznana klasa betonu: ' + cls);
  const [fck, fckc, fcm, fctm, fctk005, fctk095, Ecm] = ND.t31[cls];
  const gc = situation === 'accidental' ? ps.v('gamma_c_acc') : ps.v('gamma_c');
  const acc = ps.v('alpha_cc'), act = ps.v('alpha_ct');
  const fcd = acc * fck / gc, fctd = act * fctk005 / gc;
  const nuP = 1 - fck / ps.v('nu_prime_div');
  const nuS = ps.v('nu_shear_coef') * (1 - fck / 250);
  const fctdB = act * Math.min(fctk005, ps.v('fctk_bond_cap')) / gc;
  return { cls, fck, fck_cube: fckc, fcm, fctm, fctk005, fctk095, Ecm: Ecm * 1000, gamma_c: gc, alpha_cc: acc, alpha_ct: act,
    fcd, fctd, nu_prime: nuP, nu_shear: nuS, fctd_bond: fctdB };
}
function concreteConsistency(c) {
  const issues = [];
  const ff = c.fck <= 50 ? 0.30 * Math.pow(c.fck, 2 / 3) : 2.12 * Math.log(1 + c.fcm / 10);
  if (Math.abs(ff - c.fctm) > 0.051 + 1e-9) issues.push(`f_ctm tablicowe ${c.fctm} ≠ wzór ${ff.toFixed(2)}`);
  if (Math.abs(0.7 * ff - c.fctk005) > 0.06 + 1e-9) issues.push(`f_ctk,0,05 ${c.fctk005} ≠ 0,7·f_ctm`);
  const Ef = 22 * Math.pow(c.fcm / 10, 0.3) * 1000;
  if (Math.abs(Ef - c.Ecm) > 600) issues.push(`E_cm ${c.Ecm} ≠ wzór ${Ef.toFixed(0)}`);
  if (Math.abs(c.fcm - (c.fck + 8)) > 1e-9) issues.push('f_cm ≠ f_ck + 8 MPa');
  return issues;
}
function buildMaterials(m, ps) {
  if (!['persistent', 'accidental'].includes(m.design_situation)) throw new Error('Nieznana sytuacja obliczeniowa');
  if (!(m.d_g > 0)) throw new Error('Wymiar kruszywa d_g musi być dodatni');
  if (!ND.ductility[m.steel_class]) throw new Error('Nieznana klasa ciągliwości stali: ' + m.steel_class);
  if (!(m.steel_fyk >= 400 && m.steel_fyk <= 600)) throw new Error('f_yk poza zakresem 400–600 MPa (EN 1992-1-1 §3.2.2(3)P, zał. C)');
  if (!(m.link_fyk >= 400 && m.link_fyk <= 600)) throw new Error('f_yk strzemion poza zakresem 400–600 MPa');
  const c = concreteProps(m.concrete, ps, m.design_situation);
  const gs = m.design_situation === 'persistent' ? ps.v('gamma_s') : ps.v('gamma_s_acc');
  const [k, eps] = ND.ductility[m.steel_class];
  const Es = ps.v('Es');
  const s = { name: m.steel_name, fyk: m.steel_fyk, ductility: m.steel_class, k_min: k, eps_uk_min: eps, gamma_s: gs,
    fyd: m.steel_fyk / gs, Es, link_fyk: m.link_fyk, link_fyd: m.link_fyk / gs };
  return { concrete: c, steel: s, situation: m.design_situation, d_g: m.d_g };
}
function nodeLimits(c, ps, inc) {
  const f = inc ? ps.v('node_increase') : 1;
  return { CCC: f * ps.v('k1_node') * c.nu_prime * c.fcd, CCT: f * ps.v('k2_node') * c.nu_prime * c.fcd, CTT: f * ps.v('k3_node') * c.nu_prime * c.fcd };
}
function strutLimit(c, ps, mode) {
  if (mode === '6.55') return [c.fcd, 'σ_Rd,max = f_cd', '(6.55) — brak naprężeń poprzecznych lub ściskanie poprzeczne'];
  return [ps.v('strut_cracked') * c.nu_prime * c.fcd, "σ_Rd,max = 0,6·ν'·f_cd", '(6.56) — strefa zarysowana / rozciąganie poprzeczne'];
}
Object.assign(WS, { CONCRETE_CLASSES, concreteProps, concreteConsistency, buildMaterials, nodeLimits, strutLimit });

/* ------------------------------------------------------------------ geometria */
function sideInput(geo, sd) {
  if (sd === 'R') return geo.right;
  if (geo.left_mirror) { const s = clone(geo.right); s.side = 'L'; return s; }
  return geo.left;
}
const activeSides = geo => geo.layout === 'double' ? ['R', 'L'] : ['R'];
function makeSide(sd, si, hcol) {
  const s = sd === 'R' ? 1 : -1;
  const xs = Math.min(Math.max(si.x_slope, 0), si.l_c);
  const plate = { kind: si.plate.kind, length: si.plate.length, width: si.plate.width, thickness: si.plate.thickness, xi_center: si.a_c + si.plate.offset };
  plate.xi_inner = plate.xi_center - plate.length / 2; plate.xi_outer = plate.xi_center + plate.length / 2;
  const sg = { side: sd, s, l_c: si.l_c, h_c: si.h_c, h_e: si.h_e, x_slope: xs, a_c: si.a_c, plate, x_face: s * hcol / 2 };
  sg.depth_at = xi => {
    if (xi <= sg.x_slope || sg.l_c <= sg.x_slope) return sg.h_c;
    if (xi >= sg.l_c) return sg.h_e;
    const t = (xi - sg.x_slope) / (sg.l_c - sg.x_slope); return sg.h_c + t * (sg.h_e - sg.h_c);
  };
  sg.g = (xi, y) => [sg.x_face + sg.s * xi, y];
  sg.local_outline = () => { const p = [[0, 0], [sg.l_c, 0], [sg.l_c, -sg.h_e]]; if (sg.x_slope > 1e-9 && sg.x_slope < sg.l_c - 1e-9) p.push([sg.x_slope, -sg.h_c]); p.push([0, -sg.h_c]); return p; };
  sg.outline = () => sg.local_outline().map(([a, b]) => sg.g(a, b));
  sg.shape = Math.abs(sg.h_e - sg.h_c) < 1e-9 ? 'stała wysokość' : sg.x_slope > 1e-9 ? `zmienna wysokość (skos od ξ = ${sg.x_slope.toFixed(0)} mm)` : 'ukośna dolna krawędź (zmienna wysokość)';
  sg.area = () => sg.h_c * Math.min(sg.x_slope, sg.l_c) + Math.max(sg.l_c - sg.x_slope, 0) * (sg.h_c + sg.h_e) / 2;
  return sg;
}
function buildGeometry(geo) {
  const c = geo.column;
  const gm = { layout: geo.layout, construction: geo.construction, b: geo.b, h_col: c.h_col, b_col: c.b_col, above: c.above, below: c.below,
    column_cover: c.cover, column_phi_long: c.phi_long, column_phi_link: c.phi_link, sides: {} };
  activeSides(geo).forEach(sd => { gm.sides[sd] = makeSide(sd, sideInput(geo, sd), c.h_col); });
  gm.h_max = Math.max(...Object.values(gm.sides).map(s => s.h_c));
  gm.column_rect = () => { const h2 = gm.h_col / 2, top = gm.above, bot = -(gm.h_max + gm.below); return [[-h2, top], [h2, top], [h2, bot], [-h2, bot]]; };
  gm.outline = () => {
    const h2 = gm.h_col / 2, top = gm.above, bot = -(gm.h_max + gm.below);
    let pts = [[-h2, top], [h2, top]];
    if (gm.sides.R) { const r = gm.sides.R, lo = r.local_outline(); pts = pts.concat([[h2, 0]], lo.slice(1, -1).map(([a, b]) => r.g(a, b)), [[h2, -r.h_c]]); }
    pts = pts.concat([[h2, bot], [-h2, bot]]);
    if (gm.sides.L) { const l = gm.sides.L, lo = l.local_outline(); pts = pts.concat([[-h2, -l.h_c]], lo.slice(1, -1).reverse().map(([a, b]) => l.g(a, b)), [[-h2, 0]]); }
    return pts;
  };
  gm.ray_distance = (p, d) => rayPolygonDistance(p, d, gm.outline());
  gm.signature = () => { const s = [+gm.b.toFixed(6), +gm.h_col.toFixed(6), +gm.b_col.toFixed(6)]; Object.keys(gm.sides).sort().forEach(k => { const q = gm.sides[k]; s.push(k, q.l_c, q.h_c, q.h_e, q.x_slope, q.a_c, q.plate.xi_center, q.plate.length); }); return JSON.stringify(s); };
  return gm;
}
function distPointSeg(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
  if (L2 === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}
function pointInPolygon(p, poly, tol) {
  if (tol === undefined) tol = 1e-6;
  const nn = poly.length;
  for (let i = 0; i < nn; i++) if (distPointSeg(p, poly[i], poly[(i + 1) % nn]) <= tol) return true;
  let inside = false, j = nn - 1;
  for (let i = 0; i < nn; i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > p[1]) !== (yj > p[1])) { const xint = xi + (p[1] - yi) * (xj - xi) / (yj - yi); if (p[0] < xint) inside = !inside; }
    j = i;
  }
  return inside;
}
function rayPolygonDistance(p, d, poly) {
  const L = Math.hypot(d[0], d[1]), dx = d[0] / L, dy = d[1] / L;
  let best = Infinity;
  for (let i = 0; i < poly.length; i++) {
    const [ax, ay] = poly[i], [bx, by] = poly[(i + 1) % poly.length];
    const ex = bx - ax, ey = by - ay, den = dx * ey - dy * ex;
    if (Math.abs(den) < 1e-12) continue;
    const t = ((ax - p[0]) * ey - (ay - p[1]) * ex) / den, u = ((ax - p[0]) * dy - (ay - p[1]) * dx) / den;
    if (t > 1e-9 && u >= -1e-9 && u <= 1 + 1e-9) best = Math.min(best, t);
  }
  return best;
}
function segmentInside(a, b, poly, samples, tol) {
  for (let i = 0; i < samples; i++) { const t = i / (samples - 1); if (!pointInPolygon([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])], poly, tol)) return false; }
  return true;
}
Object.assign(WS, { sideInput, activeSides, buildGeometry, pointInPolygon, rayPolygonDistance, segmentInside });

/* ------------------------------------------------------------------ obciążenia i kombinacje */
const PSI = ND.psi;
const CATEGORIES = Object.assign({ G: 'Stałe (G)' }, Object.fromEntries(Object.entries(PSI).map(([k, v]) => [k, v[0]])), { A: 'Wyjątkowe (A)' });
const SOURCES = { beam_reaction: 'Reakcja belki prefabrykowanej', support_reaction: 'Reakcja podparcia elementu', point: 'Siła skupiona', other: 'Inne' };
const COMB_KINDS = { ULS: 'SGN — trwała/przejściowa', ULS_ACC: 'SGN — wyjątkowa', ULS_DIRECT: 'SGN — wartości obliczeniowe podane bezpośrednio', SLS_QP: 'SGU — quasi-stała', SLS_CHAR: 'SGU — charakterystyczna' };
const psi = cat => PSI[cat] ? [PSI[cat][1], PSI[cat][2], PSI[cat][3]] : [1, 1, 1];
function generateCombinations(loads) {
  const st = loads.settings;
  const chars = loads.actions.filter(a => a.nature === 'characteristic');
  const designs = loads.actions.filter(a => a.nature === 'design');
  const Gs = chars.filter(a => a.category === 'G'), Qs = chars.filter(a => PSI[a.category]), As = chars.filter(a => a.category === 'A');
  const gG = st.gamma_G_sup, gQ = st.gamma_Q, xi = st.xi;
  const combos = [];
  if (Gs.length || Qs.length) {
    const leads = Qs.length ? Qs : [null];
    const facs = (gf, lead) => { const f = {}; Gs.forEach(g => { f[g.name] = gf; }); Qs.forEach(q => { f[q.name] = q === lead ? gQ : gQ * psi(q.category)[0]; }); return f; };
    if (st.method === '6.10') leads.forEach(lead => combos.push({ name: `SGN ${lead ? lead.name : 'G'} (6.10)`, kind: 'ULS', factors: facs(gG, lead), note: 'Σγ_G·G + γ_Q·Q_1 + Σγ_Q·ψ_0·Q_i' }));
    else {
      const f = {}; Gs.forEach(g => { f[g.name] = gG; }); Qs.forEach(q => { f[q.name] = gQ * psi(q.category)[0]; });
      combos.push({ name: 'SGN (6.10a)', kind: 'ULS', factors: f, note: 'Σγ_G·G + Σγ_Q·ψ_0·Q_i' });
      leads.forEach(lead => combos.push({ name: `SGN ${lead ? lead.name : 'G'} (6.10b)`, kind: 'ULS', factors: facs(xi * gG, lead), note: 'Σξ·γ_G·G + γ_Q·Q_1 + Σγ_Q·ψ_0·Q_i' }));
    }
  }
  As.forEach(a => {
    const f = {}; Gs.forEach(g => { f[g.name] = 1; }); f[a.name] = 1;
    Qs.forEach(q => { f[q.name] = q === Qs[0] ? psi(q.category)[1] : psi(q.category)[2]; });
    combos.push({ name: `SGN-W ${a.name} (6.11b)`, kind: 'ULS_ACC', factors: f, note: 'ΣG + A_d + ψ_1,1·Q_1 + Σψ_2,i·Q_i' });
  });
  if (designs.length) { const f = {}; designs.forEach(d => { f[d.name] = 1; }); combos.push({ name: 'SGN — wartości obliczeniowe', kind: 'ULS_DIRECT', factors: f, note: 'Wartości obliczeniowe podane bezpośrednio (bez współczynników)' }); }
  if (st.include_sls && (Gs.length || Qs.length)) {
    const f = {}; Gs.forEach(g => { f[g.name] = 1; }); Qs.forEach(q => { f[q.name] = psi(q.category)[2]; });
    combos.push({ name: 'SGU quasi-stała (6.16b)', kind: 'SLS_QP', factors: f, note: 'ΣG + Σψ_2,i·Q_i' });
    if (Qs.length) { const f2 = {}; Gs.forEach(g => { f2[g.name] = 1; }); Qs.forEach((q, i) => { f2[q.name] = i === 0 ? 1 : psi(q.category)[0]; }); combos.push({ name: 'SGU charakterystyczna (6.14b)', kind: 'SLS_CHAR', factors: f2, note: 'ΣG + Q_1 + Σψ_0,i·Q_i' }); }
  }
  return combos;
}
function validateCombination(c, actions) {
  const msgs = [];
  Object.entries(c.factors).forEach(([name, f]) => {
    const a = actions[name];
    if (!a) { msgs.push(['error', `Kombinacja '${c.name}': nieznane oddziaływanie '${name}'.`]); return; }
    if (a.nature === 'design') {
      if (c.kind !== 'ULS_DIRECT') msgs.push(['error', `Kombinacja '${c.name}' (${c.kind}) zawiera wartość OBLICZENIOWĄ '${name}' — niedopuszczalne ponowne stosowanie współczynników częściowych.`]);
      else if (Math.abs(f - 1) > 1e-12) msgs.push(['error', `Kombinacja '${c.name}': wartość obliczeniowa '${name}' z mnożnikiem ${f} ≠ 1,0 — ryzyko podwójnego stosowania współczynników.`]);
    } else if (c.kind === 'ULS_DIRECT') msgs.push(['error', `Kombinacja '${c.name}' (wartości obliczeniowe) zawiera oddziaływanie charakterystyczne '${name}'.`]);
    if (f < 0) msgs.push(['error', `Kombinacja '${c.name}': ujemny mnożnik dla '${name}'.`]);
  });
  return msgs;
}
function evaluateCombinations(loads, geo) {
  const msgs = [], assumptions = [];
  const names = loads.actions.map(a => a.name);
  const dup = [...new Set(names.filter((x, i) => names.indexOf(x) !== i))];
  if (dup.length) msgs.push(['error', `Powtórzone nazwy oddziaływań: ${dup.sort().join(', ')}.`]);
  const actions = {}; loads.actions.forEach(a => { actions[a.name] = a; });
  const sides = activeSides(geo);
  loads.actions.forEach(a => {
    if (!['R', 'L'].includes(a.side)) msgs.push(['error', `Oddziaływanie '${a.name}': nieznana strona '${a.side}'.`]);
    else if (!sides.includes(a.side)) msgs.push(['warning', `Oddziaływanie '${a.name}' przypisane do strony ${a.side}, której nie ma w układzie jednostronnym — pominięte.`]);
    if (!['characteristic', 'design'].includes(a.nature)) msgs.push(['error', `Oddziaływanie '${a.name}': nieznany charakter '${a.nature}'.`]);
    if (a.nature === 'characteristic' && !CATEGORIES[a.category]) msgs.push(['error', `Oddziaływanie '${a.name}': nieznana kategoria '${a.category}'.`]);
  });
  let combos;
  const st = loads.settings;
  if (loads.combination_mode === 'manual') { combos = loads.combinations.slice(); assumptions.push('Kombinacje obciążeń zdefiniowane ręcznie przez użytkownika.'); }
  else {
    combos = generateCombinations(loads);
    assumptions.push(`Kombinacje SGN generowane automatycznie wg EN 1990 wzór ${st.method === '6.10' ? '(6.10)' : '(6.10a)/(6.10b)'}; γ_G,sup = ${st.gamma_G_sup}, γ_Q = ${st.gamma_Q}, ξ = ${st.xi}; ψ wg EN 1990 tabl. A1.1 (wartości zalecane — zgodność z NA do potwierdzenia). Oddziaływania stałe przyjęto jako niekorzystne.`);
  }
  const out = [];
  combos.forEach(c => {
    validateCombination(c, actions).forEach(m => msgs.push(m));
    const dc = { name: c.name, kind: c.kind, factors: Object.assign({}, c.factors), description: c.note || COMB_KINDS[c.kind] || c.kind, sides: {} };
    dc.is_uls = c.kind.startsWith('ULS'); dc.is_sls = c.kind.startsWith('SLS');
    sides.forEach(sd => {
      const sa = { side: sd, V: 0, H: 0, M: 0, e_y_moment: 0, H_min_applied: false };
      Object.entries(c.factors).forEach(([name, f]) => { const a = actions[name]; if (!a || a.side !== sd) return; sa.V += f * a.V; sa.H += f * a.H; sa.M += f * (a.M + a.V * a.e_x); sa.e_y_moment += f * a.V * a.e_y; });
      if (st.H_min_enabled && dc.is_uls && sa.V > 0) { const hm = st.H_min_ratio * sa.V; if (sa.H < hm) { sa.H = hm; sa.H_min_applied = true; } }
      sa.e_x = sa.V > 0 ? sa.M / sa.V : 0; sa.e_y = sa.V > 0 ? sa.e_y_moment / sa.V : 0;
      dc.sides[sd] = sa;
    });
    out.push(dc);
  });
  if (st.H_min_enabled) {
    const src = (st.H_min_source || '').trim();
    if (!src) msgs.push(['error', 'Włączono minimalną siłę poziomą H_min bez wskazania źródła/uzasadnienia — wymagane jawne wskazanie podstawy założenia.']);
    assumptions.push(`Założenie użytkownika: H_Ed ≥ ${st.H_min_ratio}·V_Ed w kombinacjach SGN. Źródło: ${src || 'BRAK'}. Nie jest to wymaganie EN 1992-1-1.`);
  }
  if (!out.some(d => d.is_uls)) msgs.push(['error', 'Brak kombinacji SGN — brak danych do wymiarowania.']);
  return { combos: out, msgs, assumptions };
}
Object.assign(WS, { PSI, CATEGORIES, SOURCES, COMB_KINDS, psi, generateCombinations, evaluateCombinations });

/* ------------------------------------------------------------------ algebra liniowa */
function gaussSolve(A, b) {           // A·x = b, eliminacja z częściowym wyborem elementu
  const nn = A.length, M = A.map((r, i) => r.concat([b[i]]));
  for (let k = 0; k < nn; k++) {
    let p = k; for (let i = k + 1; i < nn; i++) if (Math.abs(M[i][k]) > Math.abs(M[p][k])) p = i;
    if (Math.abs(M[p][k]) < 1e-300) throw new Error('Układ osobliwy');
    [M[k], M[p]] = [M[p], M[k]];
    for (let i = k + 1; i < nn; i++) { const f = M[i][k] / M[k][k]; if (f) for (let j = k; j <= nn; j++) M[i][j] -= f * M[k][j]; }
  }
  const x = new Array(nn).fill(0);
  for (let i = nn - 1; i >= 0; i--) { let s = M[i][nn]; for (let j = i + 1; j < nn; j++) s -= M[i][j] * x[j]; x[i] = s / M[i][i]; }
  return x;
}
function matRank(A) {               // rząd: eliminacja z pełnym wyborem, tol względna 1e-10
  const M = A.map(r => r.slice()); const rows = M.length, cols = rows ? M[0].length : 0;
  let mx = 0; M.forEach(r => r.forEach(v => { mx = Math.max(mx, Math.abs(v)); }));
  const tol = 1e-10 * Math.max(1, mx);
  let rank = 0; const used = new Array(cols).fill(false);
  for (let r = 0; r < rows && rank < cols; r++) {
    let best = 0, pr = -1, pc = -1;
    for (let i = rank; i < rows; i++) for (let j = 0; j < cols; j++) if (!used[j] && Math.abs(M[i][j]) > best) { best = Math.abs(M[i][j]); pr = i; pc = j; }
    if (best <= tol) break;
    [M[rank], M[pr]] = [M[pr], M[rank]]; used[pc] = true;
    for (let i = rank + 1; i < rows; i++) { const f = M[i][pc] / M[rank][pc]; if (f) for (let j = 0; j < cols; j++) M[i][j] -= f * M[rank][j]; }
    rank++;
  }
  return rank;
}
function lstsq(A, b) {              // najmniejsze kwadraty (równania normalne z małą regularyzacją)
  const m = A[0] ? A[0].length : 0;
  const N = Array.from({ length: m }, () => new Array(m).fill(0)), r = new Array(m).fill(0);
  for (let i = 0; i < A.length; i++) for (let j = 0; j < m; j++) { r[j] += A[i][j] * b[i]; for (let k = 0; k < m; k++) N[j][k] += A[i][j] * A[i][k]; }
  let tr = 0; for (let j = 0; j < m; j++) tr += N[j][j];
  for (let j = 0; j < m; j++) N[j][j] += 1e-12 * Math.max(tr, 1);
  return gaussSolve(N, r);
}

/* ------------------------------------------------------------------ solver kratownic (kwst.stm_solver) */
class StmModelError extends Error {}
function trussValidate(model) {
  const ids = model.nodes.map(x => x.id);
  if (new Set(ids).size !== ids.length) throw new StmModelError('Powtórzone identyfikatory węzłów.');
  const idx = {}; ids.forEach((id, i) => { idx[id] = i; });
  const mids = model.members.map(x => x.id);
  if (new Set(mids).size !== mids.length) throw new StmModelError('Powtórzone identyfikatory prętów.');
  model.members.forEach(m => {
    if (!(m.n1 in idx) || !(m.n2 in idx)) throw new StmModelError(`Pręt ${m.id}: nieistniejący węzeł.`);
    if (m.n1 === m.n2) throw new StmModelError(`Pręt ${m.id}: oba końce w tym samym węźle.`);
    const a = model.nodes[idx[m.n1]], b = model.nodes[idx[m.n2]];
    if (Math.hypot(b.x - a.x, b.y - a.y) < 1e-6) throw new StmModelError(`Pręt ${m.id}: zerowa długość.`);
  });
  model.supports.forEach(s => { if (!(s.node in idx)) throw new StmModelError(`Podpora w nieistniejącym węźle ${s.node}.`); });
  model.loads.forEach(l => { if (!(l.node in idx)) throw new StmModelError(`Obciążenie w nieistniejącym węźle ${l.node}.`); if (!isFinite(l.Fx) || !isFinite(l.Fy)) throw new StmModelError('Nieskończona wartość obciążenia.'); });
  return idx;
}
function trussSolve(model, relTol) {
  if (relTol === undefined) relTol = 1e-9;
  const idx = trussValidate(model);
  const nn = model.nodes.length, m = model.members.length;
  const rd = []; model.supports.forEach(s => { if (s.ux) rd.push([s.node, 0]); if (s.uy) rd.push([s.node, 1]); });
  const nEq = 2 * nn, nUnk = m + rd.length;
  const A = Array.from({ length: nEq }, () => new Array(nUnk).fill(0));
  model.members.forEach((mem, k) => {
    const i = idx[mem.n1], j = idx[mem.n2], a = model.nodes[i], b = model.nodes[j], L = Math.hypot(b.x - a.x, b.y - a.y);
    const cx = (b.x - a.x) / L, cy = (b.y - a.y) / L;
    A[2 * i][k] += cx; A[2 * i + 1][k] += cy; A[2 * j][k] -= cx; A[2 * j + 1][k] -= cy;
  });
  rd.forEach(([nid, dof], r) => { A[2 * idx[nid] + dof][m + r] = 1; });
  const P = new Array(nEq).fill(0);
  model.loads.forEach(l => { P[2 * idx[l.node]] += l.Fx; P[2 * idx[l.node] + 1] += l.Fy; });
  const scale = Math.max(1, ...P.map(Math.abs)), tol = relTol * scale * 1e3;
  const xs = model.nodes.map(q => q.x), ys = model.nodes.map(q => q.y);
  const lever = Math.max(1, Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
  const rank = nUnk ? matRank(A) : 0;
  const msgs = []; let f = new Array(nUnk).fill(0), status, method = 'none';
  const negP = P.map(v => -v);
  if (rank < nEq) {
    status = 'mechanism';
    if (nUnk) { try { f = lstsq(A, negP); } catch (e) { f = new Array(nUnk).fill(0); } }
    const res = A.map((row, i) => row.reduce((s, v, j) => s + v * f[j], 0) + P[i]);
    msgs.push(Math.max(...res.map(Math.abs)) > tol ? 'Model ZMIENNY geometrycznie (mechanizm) — obciążenie nie może zostać zrównoważone.'
      : 'Model ZMIENNY geometrycznie (mechanizm) — równowaga istnieje tylko dla bieżącego układu obciążeń; model niedopuszczalny do weryfikacji.');
    method = 'lstsq';
  } else if (rank === nUnk) {
    status = 'determinate'; f = nEq === nUnk ? gaussSolve(A, negP) : lstsq(A, negP); method = 'equilibrium';
  } else {
    status = 'indeterminate';
    msgs.push(`Model statycznie niewyznaczalny (stopień ${nUnk - rank}) — siły wyznaczono metodą sztywności; wynik zależy od przyjętych sztywności EA.`);
    f = trussStiffness(model, idx, rd, P); method = 'stiffness';
  }
  const res = A.map((row, i) => row.reduce((s, v, j) => s + v * f[j], 0) + P[i]);
  const nodeRes = {}; model.nodes.forEach((q, i) => { nodeRes[q.id] = Math.hypot(res[2 * i], res[2 * i + 1]); });
  const forces = {}; model.members.forEach((mem, k) => { forces[mem.id] = f[k]; });
  const reactions = {};
  rd.forEach(([nid, dof], r) => { const v = reactions[nid] || [0, 0]; v[dof] += f[m + r]; reactions[nid] = v; });
  let sfx = 0, sfy = 0, smz = 0;
  model.loads.forEach(l => { const q = model.nodes[idx[l.node]]; sfx += l.Fx; sfy += l.Fy; smz += q.x * l.Fy - q.y * l.Fx; });
  Object.entries(reactions).forEach(([nid, [rx, ry]]) => { const q = model.nodes[idx[nid]]; sfx += rx; sfy += ry; smz += q.x * ry - q.y * rx; });
  const maxRes = Object.values(nodeRes).length ? Math.max(...Object.values(nodeRes)) : 0;
  const sol = { forces, reactions, status, method, rank, n_equations: nEq, n_unknowns: nUnk, degree: nUnk - nEq, node_residuals: nodeRes,
    max_residual: maxRes, global_residual: [sfx, sfy, smz], tolerance: tol, messages: msgs, lever };
  sol.stable = status === 'determinate' || status === 'indeterminate';
  sol.equilibrium_ok = sol.stable && maxRes <= tol && Math.max(Math.abs(sfx), Math.abs(sfy)) <= tol && Math.abs(smz) <= tol * lever;
  if (status !== 'mechanism' && maxRes > tol) msgs.push(`Residuum równowagi ${maxRes.toExponential(3)} N przekracza tolerancję ${tol.toExponential(3)} N.`);
  return sol;
}
function trussStiffness(model, idx, rd, P) {
  const nn = model.nodes.length, m = model.members.length, K = Array.from({ length: 2 * nn }, () => new Array(2 * nn).fill(0)), geom = [];
  model.members.forEach(mem => {
    if (!(mem.EA > 0)) throw new StmModelError(`Model niewyznaczalny: pręt ${mem.id} wymaga dodatniej sztywności EA.`);
    const i = idx[mem.n1], j = idx[mem.n2], a = model.nodes[i], b = model.nodes[j], L = Math.hypot(b.x - a.x, b.y - a.y);
    const c = (b.x - a.x) / L, s = (b.y - a.y) / L, k = mem.EA / L, kl = [[c * c, c * s], [c * s, s * s]];
    [[i, i, 1], [j, j, 1], [i, j, -1], [j, i, -1]].forEach(([p, q, sg]) => { for (let u = 0; u < 2; u++) for (let v = 0; v < 2; v++) K[2 * p + u][2 * q + v] += sg * k * kl[u][v]; });
    geom.push([i, j, c, s, k]);
  });
  const fixed = new Set(rd.map(([nid, dof]) => 2 * idx[nid] + dof)), free = [];
  for (let d = 0; d < 2 * nn; d++) if (!fixed.has(d)) free.push(d);
  const u = new Array(2 * nn).fill(0);
  const uf = gaussSolve(free.map(a => free.map(b => K[a][b])), free.map(a => P[a]));
  free.forEach((d, k) => { u[d] = uf[k]; });
  const f = new Array(m + rd.length).fill(0);
  geom.forEach(([i, j, c, s, k], q) => { f[q] = k * ((u[2 * j] - u[2 * i]) * c + (u[2 * j + 1] - u[2 * i + 1]) * s); });
  rd.forEach(([nid, dof], r) => { const row = 2 * idx[nid] + dof; f[m + r] = K[row].reduce((acc, v, j) => acc + v * u[j], 0) - P[row]; });
  return f;
}
Object.assign(WS, { StmModelError, trussSolve, gaussSolve, matRank });
})(typeof window !== 'undefined' ? window : globalThis);
