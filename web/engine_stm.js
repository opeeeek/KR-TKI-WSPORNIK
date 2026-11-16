/* KRÓTKI WSPORNIK ST – silnik obliczeń (część 2): model STM wspornika (zał. J.3, rys. J.5), sprawdzenia krzyżulców,
   węzłów, cięgien, docisku, rozłupywania, zakotwień (rozdz. 8) i konstruowanie zbrojenia.
   Port 1:1 modułów kwst/stm_generator.py, strut_checks.py, node_checks.py, tie_checks.py, anchorage_engine.py,
   reinforcement_design.py. */
(function (G) {
'use strict';
const WS = G.WS;
const { n, kN, mm, mm2, MPa, barArea, ST, BASIS, make, SIDE_NAME, StmModelError, trussSolve, nodeLimits, strutLimit, pointInPolygon, segmentInside, ND } = WS;

/* ================================================================== model STM wspornika */
function buildSideParams(gm, sd, act, mats, ps, st, c_t, As_prov, a_H_user, d_user) {
  const sg = gm.sides[sd], notes = [];
  const V = act.V, H_raw = act.H; let H = H_raw;
  if (H_raw < 0 && st.neglect_favourable_H) { H = 0; notes.push('Siła H skierowana do słupa (korzystna) — pominięta w modelu (założenie bezpieczne).'); }
  let d = sg.h_c - c_t; if (d_user !== null && d_user !== undefined) d = d_user;
  const c_t_model = sg.h_c - d;
  const t_p = ['steel_plate', 'elastomer'].includes(sg.plate.kind) ? sg.plate.thickness : 0;
  const a_H = (a_H_user !== null && a_H_user !== undefined) ? a_H_user : c_t_model + t_p;
  const M = act.M;
  const xi_A = sg.a_c + (V > 0 ? M / V : 0) + ((st.include_aH && V > 0) ? H * a_H / V : 0);
  if (!st.include_aH && H !== 0) notes.push('Pominięto ramię a_H siły poziomej (decyzja użytkownika).');
  const e_rel = (sg.a_c + (V > 0 ? M / V : 0) + (V > 0 ? H * t_p / V : 0)) - sg.plate.xi_center;
  const a_ef = sg.plate.length - 2 * Math.abs(e_rel);
  const e_y = act.e_y, b_p_ef = sg.plate.width - 2 * Math.abs(e_y);
  const t_A = Math.min(b_p_ef, gm.b - 2 * Math.abs(e_y)), t_B = gm.b - 2 * Math.abs(e_y);
  if (Math.abs(e_y) > 1e-9) notes.push(`Mimośród poprzeczny e_y = ${e_y.toFixed(1)} mm: grubości efektywne t_A = ${t_A.toFixed(0)} mm, t_B = ${t_B.toFixed(0)} mm (b_ef = b − 2|e_y|) — założenie inżynierskie.`);
  const inc = !!(st.node_10pct && (st.node_10pct_justification || '').trim());
  const lim = nodeLimits(mats.concrete, ps, inc);
  const [sStr, sFml] = strutLimit(mats.concrete, ps, st.strut_limit);
  return { side: sd, s: sg.s, V, H_raw, H, M, e_y, a_c: sg.a_c, a_H, xi_A, c_t: c_t_model, d, h_c: sg.h_c, u: 2 * c_t_model,
    a_p: sg.plate.length, a_ef, e_rel, t_A, t_B, node_b_mode: st.node_b_position, sigma_strut: sStr, sigma_strut_formula: sFml,
    sigma_CCT: lim.CCT, sigma_CCC: lim.CCC, As_prov, fyd: mats.steel.fyd, tan_min: ps.v('J3_tan_min'), tan_max: ps.v('J3_tan_max'),
    x_lo: 1, x_hi_geom: Math.max(d - c_t_model, 1), notes, T_anch: null };
}
function sEval(p, x_c) {
  const z0 = p.d - x_c / 2, V = p.V;
  if (z0 <= 0) throw new StmModelError('Ramię z0 ≤ 0 — strefa ściskana przekracza wysokość użyteczną.');
  let xi_B, Fc, a_B;
  if (p.node_b_mode === 'face') {
    xi_B = 0; if (p.xi_A - xi_B <= 0) throw new StmModelError('Wypadkowa obciążenia w obrysie słupa (ξ_A ≤ ξ_B).');
    Fc = V * (p.xi_A - xi_B) / z0; a_B = x_c * V / Fc;
  } else {
    const disc = p.xi_A * p.xi_A + 2 * x_c * z0;
    if (p.xi_A <= -Math.sqrt(Math.max(disc, 0)) + 1e-9) throw new StmModelError('Wypadkowa obciążenia w obrysie słupa (ξ_A ≤ ξ_B).');
    Fc = V / (2 * z0) * (p.xi_A + Math.sqrt(disc)); a_B = x_c * V / Fc; xi_B = -a_B / 2;
    if (p.xi_A - xi_B <= 0) throw new StmModelError('Wypadkowa obciążenia w obrysie słupa (ξ_A ≤ ξ_B).');
  }
  const T = Fc + p.H, C = Math.hypot(Fc, V), theta = Math.atan2(V, Fc);
  const w_A = p.a_ef * Math.sin(theta) + p.u * Math.cos(theta), w_B = Math.hypot(x_c, a_B);
  const sb = (p.a_ef > 0 && p.t_A > 0) ? V / (p.a_ef * p.t_A) : Infinity;
  const sA = (w_A > 0 && p.t_A > 0) ? C / (w_A * p.t_A) : Infinity;
  const sB = p.t_B > 0 ? Fc / (x_c * p.t_B) : Infinity;
  const s = { x_c, z0, xi_A: p.xi_A, y_A: -p.c_t, xi_B, y_B: -(p.h_c - x_c / 2), a_B, Fc, T, C, theta, w_A, w_B, sigma_bearing: sb, sigma_A: sA, sigma_B: sB };
  s.tan_theta = Math.tan(theta); s.theta_deg = theta * 180 / Math.PI;
  s.eta = { strut_A: sA / p.sigma_strut, strut_B: sB / p.sigma_strut, node_A_bearing: sb / p.sigma_CCT, node_A_strut: sA / p.sigma_CCT, node_B: sB / p.sigma_CCC };
  if (p.As_prov !== null && p.As_prov !== undefined) {
    s.eta.tie = p.As_prov > 0 ? T / (p.As_prov * p.fyd) : Infinity;
    if (p.T_anch !== null && p.T_anch !== undefined && isFinite(p.T_anch)) s.eta.anchorage = p.T_anch > 0 ? T / p.T_anch : Infinity;
  }
  s.eta_concrete = () => Math.max(...Object.entries(s.eta).filter(([k]) => k !== 'tie' && k !== 'anchorage').map(([, v]) => v));
  s.eta_max = () => Math.max(...Object.values(s.eta));
  return s;
}
const tanAt = (p, x) => sEval(p, x).tan_theta;
function bisect(fn, lo, hi, it, side) {
  it = it || 80; let flo = fn(lo);
  for (let i = 0; i < it; i++) { const mid = 0.5 * (lo + hi), fm = fn(mid); if ((fm > 0) === (flo > 0)) { lo = mid; flo = fm; } else hi = mid; }
  return side === 'hi' ? hi : 0.5 * (lo + hi);
}
function golden(fn, a, b, it) {
  it = it || 60; const g = (Math.sqrt(5) - 1) / 2;
  let c = b - g * (b - a), d = a + g * (b - a), fc = fn(c), fd = fn(d);
  for (let i = 0; i < it; i++) {
    if (fc <= fd) { b = d; d = c; fd = fc; c = b - g * (b - a); fc = fn(c); }
    else { a = c; c = d; fc = fd; d = a + g * (b - a); fd = fn(d); }
  }
  return (a + b) / 2;
}
function feasibleInterval(p) {
  const lo = p.x_lo, hi = p.x_hi_geom;
  if (hi <= lo) return [lo, hi, 'Brak miejsca na strefę ściskaną węzła B (d − c_t ≤ 0).'];
  const tLo = tanAt(p, lo), tHi = tanAt(p, hi);
  let a = lo, b = hi;
  if (tHi > p.tan_max + 1e-12) return [lo, hi, `Bardzo krótki wspornik: tan θ = ${tHi.toFixed(2)} > ${p.tan_max} nawet przy maksymalnej strefie ściskanej — model J.3 niestosowalny wprost.`];
  if (tLo < p.tan_min - 1e-12) return [lo, hi, `Wysięg zbyt duży: tan θ = ${tLo.toFixed(2)} < ${p.tan_min} (a_c ≥ z0) — element nie jest krótkim wspornikiem wg J.3; należy projektować jako belkę wspornikową (6.1, 6.2).`];
  if (tLo > p.tan_max) a = bisect(x => tanAt(p, x) - p.tan_max, lo, hi);
  if (tHi < p.tan_min) b = bisect(x => tanAt(p, x) - p.tan_min, lo, hi);
  return [a, b, ''];
}
function chooseXc(p, st, design, x_c_user, z0_user) {
  const [lo, hi, reason] = feasibleInterval(p);
  const info = { x_min: lo, x_max: hi, mode: st.lever_arm };
  const feasible = !reason;
  if (st.lever_arm === 'user' && ((x_c_user !== null && x_c_user !== undefined) || (z0_user !== null && z0_user !== undefined))) {
    const x = (x_c_user !== null && x_c_user !== undefined) ? x_c_user : 2 * (p.d - z0_user);
    info.method = 'wartość użytkownika' + ((x_c_user === null || x_c_user === undefined) ? ' (z0)' : ' (x_c)');
    if (!(x >= lo - 1e-6 && x <= hi + 1e-6)) return [x, info, false, reason || `x_c = ${x.toFixed(1)} mm poza przedziałem dopuszczalnym [${lo.toFixed(1)}; ${hi.toFixed(1)}] mm (geometria / tan θ wg J.3(1)).`];
    return [x, info, feasible, reason];
  }
  if (!feasible) {
    const loG = p.x_lo, hiG = p.x_hi_geom;
    const obj = (p.As_prov !== null && p.As_prov !== undefined && !design) ? (x => sEval(p, x).eta_max()) : (x => sEval(p, x).eta_concrete());
    const xs = Array.from({ length: 48 }, (_, i) => loG + (hiG - loG) * i / 47);
    let k = 0; xs.forEach((x, i) => { if (obj(x) < obj(xs[k])) k = i; });
    let x = golden(obj, xs[Math.max(k - 1, 0)], xs[Math.min(k + 1, 47)]);
    if (obj(x) > obj(xs[k])) x = xs[k];
    info.method = 'model poza zakresem J.3 — pole naprężeń informacyjne (min. wykorzystanie)';
    return [x, info, false, reason];
  }
  if (st.lever_arm === 'node_limit') {
    const target = Math.min(p.sigma_CCC, p.sigma_strut), f = x => sEval(p, x).sigma_B - target;
    const x = f(lo) <= 0 ? lo : f(hi) > 0 ? hi : bisect(f, lo, hi, 80, 'hi');
    info.method = 'σ_B = min(σ_Rd,max CCC; σ_Rd,max krzyżulca)';
    return [x, info, true, ''];
  }
  const N = 64, xs = Array.from({ length: N }, (_, i) => lo + (hi - lo) * i / (N - 1));
  if (design || p.As_prov === null || p.As_prov === undefined) {
    const etas = xs.map(x => sEval(p, x).eta_concrete());
    const k = etas.findIndex(e => e <= 1);
    let x;
    if (k < 0) { x = golden(q => sEval(p, q).eta_concrete(), lo, hi); info.method = 'min. wykorzystanie betonu (brak pola spełniającego warunki)'; }
    else if (k === 0) { x = lo; info.method = 'min. siła w cięgnie przy η_beton ≤ 1'; }
    else { x = bisect(q => sEval(p, q).eta_concrete() - 1, xs[k - 1], xs[k], 80, 'hi'); if (sEval(p, x).eta_concrete() > 1) x = xs[k]; info.method = 'min. siła w cięgnie przy η_beton ≤ 1'; }
    return [x, info, true, ''];
  }
  const etas = xs.map(x => sEval(p, x).eta_max());
  let k = 0; etas.forEach((e, i) => { if (e < etas[k]) k = i; });
  let x = golden(q => sEval(p, q).eta_max(), xs[Math.max(k - 1, 0)], xs[Math.min(k + 1, N - 1)]);
  if (sEval(p, x).eta_max() > etas[k]) x = xs[k];
  info.method = 'minimalizacja maksymalnego wykorzystania (dolne oszacowanie nośności)';
  return [x, info, true, ''];
}
const rect = (x0, x1, y0, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
function strutPolygon(A, B, wA, wB) {
  const dx = B[0] - A[0], dy = B[1] - A[1], L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L;
  return [[A[0] + nx * wA / 2, A[1] + ny * wA / 2], [B[0] + nx * wB / 2, B[1] + ny * wB / 2], [B[0] - nx * wB / 2, B[1] - ny * wB / 2], [A[0] - nx * wA / 2, A[1] - ny * wA / 2]];
}
function splittingGeometry(gm, A, B) {
  const mx = (A[0] + B[0]) / 2, my = (A[1] + B[1]) / 2, dx = B[0] - A[0], dy = B[1] - A[1], L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L;
  if (!pointInPolygon([mx, my], gm.outline())) return 0;
  return gm.ray_distance([mx, my], [nx, ny]) + gm.ray_distance([mx, my], [-nx, -ny]);
}
function trussNode(t, id) { const q = t.nodes.find(x => x.id === id); if (!q) throw new Error(id); return q; }
function buildCorbelModel(gm, combo, mats, ps, st, c_t, As_prov, design, sideIn) {
  const msgs = []; sideIn = sideIn || {};
  const truss = { nodes: [], members: [], supports: [], loads: [] };
  const sides = {}, nodes = {}, struts = [], ties = [];
  const h2 = gm.h_col / 2, double = Object.keys(gm.sides).length === 2;
  const xC = double ? 0 : -(h2 - gm.column_cover - gm.column_phi_link - gm.column_phi_long / 2), yC = -c_t;
  const active = [];
  Object.keys(gm.sides).forEach(sd => {
    const act = combo.sides[sd]; if (!act) return;
    if (act.V < -1e-6) { msgs.push(['error', `Strona ${sd}: siła V < 0 (odrywanie) — model wspornika krótkiego J.3 nie obejmuje tego przypadku.`, 'side:' + sd]); return; }
    if (act.V <= 1e-6) { if (Math.abs(act.H) > 1e-6) msgs.push(['warning', `Strona ${sd}: brak siły pionowej, H ≠ 0 — siła pozioma przenoszona bezpośrednio przez cięgno (T = H).`, 'side:' + sd]); return; }
    const si = sideIn[sd] || {};
    const p = buildSideParams(gm, sd, act, mats, ps, st, c_t, As_prov, si.a_H_user, si.d_user);
    p.T_anch = (si.T_anch === undefined) ? null : si.T_anch;
    if (p.a_ef <= 0) { msgs.push(['error', `Strona ${sd}: wypadkowa obciążenia poza płytą oporową (e = ${p.e_rel.toFixed(1)} mm, a_p = ${p.a_p.toFixed(0)} mm).`, 'side:' + sd]); return; }
    if (p.t_A <= 0 || p.t_B <= 0) { msgs.push(['error', `Strona ${sd}: mimośród poprzeczny e_y zbyt duży (b_ef ≤ 0).`, 'side:' + sd]); return; }
    let x_c, info, feas, reason, state;
    try { [x_c, info, feas, reason] = chooseXc(p, st, design, si.x_c_user, si.z0_user); state = sEval(p, x_c); }
    catch (e) { if (e instanceof StmModelError) { msgs.push(['error', `Strona ${sd}: ${e.message}`, 'side:' + sd]); return; } throw e; }
    sides[sd] = { params: p, state, search: info, feasible: feas, infeasible_reason: reason };
    active.push(sd);
  });
  if (!active.length) {
    return { combination: combo.name, model_type: 'J.3', truss, solution: { forces: {}, reactions: {}, status: 'error', method: 'none', rank: 0, n_equations: 0, n_unknowns: 0, degree: 0, node_residuals: {}, max_residual: 0, global_residual: [0, 0, 0], tolerance: 0, messages: ['Brak aktywnych stron modelu.'], stable: false, equilibrium_ok: false },
      sides, nodes, struts, ties, comparison: {}, messages: msgs, containment: {} };
  }
  truss.nodes.push({ id: 'C', x: xC, y: yC }); truss.supports.push({ node: 'C', ux: true, uy: true });
  active.forEach(sd => {
    const { params: p, state: s } = sides[sd], sg = gm.sides[sd];
    const A = sg.g(s.xi_A, s.y_A), B = sg.g(s.xi_B, s.y_B);
    truss.nodes.push({ id: 'A' + sd, x: A[0], y: A[1] }, { id: 'B' + sd, x: B[0], y: B[1] });
    truss.members.push({ id: 'S' + sd, n1: 'A' + sd, n2: 'B' + sd, kind: 'strut' }, { id: 'T' + sd, n1: 'A' + sd, n2: 'C', kind: 'tie' });
    truss.supports.push({ node: 'B' + sd, ux: true, uy: true });
    truss.loads.push({ node: 'A' + sd, Fx: sg.s * p.H, Fy: -p.V });
  });
  const sol = trussSolve(truss);
  const comp = { max_rel_diff: 0, items: [], containment: {} };
  const outline = gm.outline();
  active.forEach(sd => {
    const { params: p, state: s } = sides[sd], sg = gm.sides[sd];
    const Tm = sol.forces['T' + sd], Cm = -sol.forces['S' + sd];
    [['T', s.T, Tm], ['C', s.C, Cm]].forEach(([nm, a, b]) => { const rel = Math.abs(a - b) / Math.max(Math.abs(a), 1); comp.items.push([nm + sd, a, b, rel]); comp.max_rel_diff = Math.max(comp.max_rel_diff, rel); });
    const A = sg.g(s.xi_A, s.y_A), B = sg.g(s.xi_B, s.y_B), nA = 'A' + sd, nB = 'B' + sd;
    const xa = [sg.g(s.xi_A - p.a_ef / 2, 0)[0], sg.g(s.xi_A + p.a_ef / 2, 0)[0]].sort((u, v) => u - v);
    nodes[nA] = { id: nA, type: 'CCT', center: A, polygon: rect(xa[0], xa[1], -p.u, 0), side: sd, faces: [
      { name: 'ścianka docisku (płyta)', F: p.V, length: p.a_ef, t: p.t_A, sigma: s.sigma_bearing },
      { name: 'ścianka krzyżulca', F: s.C, length: s.w_A, t: p.t_A, sigma: s.sigma_A }] };
    const xb = [sg.g(s.xi_B - s.a_B / 2, 0)[0], sg.g(s.xi_B + s.a_B / 2, 0)[0]].sort((u, v) => u - v);
    nodes[nB] = { id: nB, type: 'CCC', center: B, polygon: rect(xb[0], xb[1], -p.h_c, -p.h_c + s.x_c), side: sd, faces: [
      { name: 'ścianka pionowa (F_c)', F: s.Fc, length: s.x_c, t: p.t_B, sigma: s.sigma_B },
      { name: 'ścianka pozioma (V)', F: p.V, length: s.a_B, t: p.t_B, sigma: p.V / (s.a_B * p.t_B) },
      { name: 'ścianka krzyżulca', F: s.C, length: s.w_B, t: p.t_B, sigma: s.C / (s.w_B * p.t_B) }] };
    const L = Math.hypot(B[0] - A[0], B[1] - A[1]), bAv = splittingGeometry(gm, A, B);
    const shape = bAv > 1.2 * Math.max(s.w_A, s.w_B) ? 'butelkowy' : 'pryzmatyczny';
    const poly = strutPolygon(A, B, s.w_A, s.w_B);
    struts.push({ id: 'S' + sd, n1: nA, n2: nB, force: -s.C, w1: s.w_A, w2: s.w_B, t1: p.t_A, t2: p.t_B, polygon: poly, shape, b_avail: bAv, length: L, theta_deg: s.theta_deg, side: sd });
    const xt = [A[0], xC].sort((u, v) => u - v);
    ties.push({ id: 'T' + sd, n1: nA, n2: 'C', force: s.T, As_prov, u: p.u, polygon: rect(xt[0], xt[1], -p.u, 0), side: sd });
    const e1 = [poly[0], poly[1]], e2 = [poly[3], poly[2]];
    const edgeOk = (e, t0, t1) => { const [[ax, ay], [bx, by]] = e; return segmentInside([ax + t0 * (bx - ax), ay + t0 * (by - ay)], [ax + t1 * (bx - ax), ay + t1 * (by - ay)], outline, 41, 1.0); };
    const lower = sg.s > 0 ? e1 : e2, upper = sg.s > 0 ? e2 : e1;
    comp.containment['strut_lower_' + sd] = edgeOk(lower, 0.05, 0.95);
    comp.containment['strut_upper_' + sd] = edgeOk(upper, 0.25, 0.95);
    comp.containment['node_A_' + sd] = nodes[nA].polygon.every(q => pointInPolygon(q, outline, 1.0));
    comp.containment['node_B_' + sd] = nodes[nB].polygon.every(q => pointInPolygon(q, outline, 1.0));
  });
  nodes.C = { id: 'C', type: 'kotwienie (słup)', center: [xC, yC], polygon: [], side: '', faces: [] };
  const res = { combination: combo.name, model_type: double ? 'J.3 dwustronny' : 'J.3 jednostronny', truss, solution: sol, sides, nodes, struts, ties, comparison: comp, messages: msgs, containment: comp.containment };
  if (comp.max_rel_diff > 1e-6) res.messages.push(['error', `Niezgodność rozwiązania analitycznego i macierzowego (${comp.max_rel_diff.toExponential(2)}) — model odrzucony.`]);
  return res;
}
function buildManualModel(man) {
  return {
    nodes: man.nodes.map(q => ({ id: q.id, x: q.x, y: q.y })),
    members: man.members.map(m => ({ id: m.id, n1: m.n1, n2: m.n2, kind: m.kind, EA: m.kind === 'strut' ? 30000 * Math.max(m.width, 1) * Math.max(m.thickness, 1) : (m.As > 0 ? 200000 * m.As : null) })),
    supports: man.supports.map(s => ({ node: s.node, ux: s.ux, uy: s.uy })),
    loads: man.loads.map(l => ({ node: l.node, Fx: l.Fx, Fy: l.Fy })),
  };
}
function manualFromResult(res, b) {
  const sg = {}; res.struts.forEach(s => { sg[s.id] = s; }); const tg = {}; res.ties.forEach(t => { tg[t.id] = t; });
  return {
    nodes: res.truss.nodes.map(q => ({ id: q.id, x: +q.x.toFixed(3), y: +q.y.toFixed(3) })),
    members: res.truss.members.map(m => sg[m.id] ? { id: m.id, n1: m.n1, n2: m.n2, kind: 'strut', width: +Math.min(sg[m.id].w1, sg[m.id].w2).toFixed(1), thickness: +Math.min(sg[m.id].t1, sg[m.id].t2).toFixed(1), As: 0 }
      : { id: m.id, n1: m.n1, n2: m.n2, kind: 'tie', width: 0, thickness: b, As: +((tg[m.id] && tg[m.id].As_prov) || 0).toFixed(1) }),
    supports: res.truss.supports.map(s => ({ node: s.node, ux: s.ux, uy: s.uy, bearing_width: 100 })),
    loads: res.truss.loads.map(l => ({ node: l.node, Fx: l.Fx, Fy: l.Fy })),
  };
}
Object.assign(WS, { buildSideParams, sEval, chooseXc, feasibleInterval, buildCorbelModel, buildManualModel, manualFromResult, trussNode });

/* ================================================================== sprawdzenia krzyżulców (6.5.2, 6.5.3(3), J.3(1)) */
const stress = (F, w, t) => F / (w * t);
function strutChecks(sm, strut, mats, ps, st, combo) {
  const p = sm.params, s = sm.state, sd = p.side, c = mats.concrete, lim = p.sigma_strut;
  let clause, limTxt, note;
  if (st.strut_limit === '6.55') { clause = 'EN 1992-1-1 §6.5.2(1), wzór (6.55)'; limTxt = `σ_Rd,max = f_cd = ${MPa(c.fcd)}`; note = 'Przyjęto (6.55): brak rozciągania poprzecznego lub ściskanie poprzeczne — decyzja projektanta; dla krzyżulca butelkowego wspornika zwykle właściwy jest wzór (6.56).'; }
  else { clause = 'EN 1992-1-1 §6.5.2(2), wzory (6.56), (6.57N)'; limTxt = `σ_Rd,max = 0,6·ν'·f_cd = 0,6·${n(c.nu_prime, 3)}·${n(c.fcd)} = ${MPa(lim)}; ν' = 1 − ${n(c.fck, 0)}/250 = ${n(c.nu_prime, 3)}`; note = 'Krzyżulec w strefie z rozciąganiem poprzecznym (zarysowanej) — wzór (6.56).'; }
  const sym = { 'C_Ed': 'siła ściskająca w krzyżulcu', w: 'szerokość efektywna krzyżulca na granicy węzła', t: 'grubość efektywna krzyżulca (wymiar prostopadły do płaszczyzny modelu)', 'σ_Rd,max': 'nośność obliczeniowa krzyżulca', "ν'": 'współczynnik redukcyjny (6.57N)' };
  const sA = stress(s.C, s.w_A, p.t_A), sB = stress(s.C, s.w_B, p.t_B), tanT = s.tan_theta;
  return [
    make({ id: `STRUT_${sd}_A`, group: 'Krzyżulce', title: `Krzyżulec S${sd} (${SIDE_NAME[sd]}) — przekrój przy węźle A`, clause, basis: BASIS.NORMATIVE,
      formula: 'σ_Ed = C_Ed / (w_A·t_A) ≤ σ_Rd,max;  w_A = a_ef·sin θ + u·cos θ (rys. 6.27)', symbols: Object.assign({}, sym, { a_ef: 'efektywna długość płyty oporowej', u: 'wysokość strefy cięgna (u = 2·c_t)' }),
      substitution: `w_A = ${n(p.a_ef, 1)}·sin ${n(s.theta_deg, 2)}° + ${n(p.u, 1)}·cos ${n(s.theta_deg, 2)}° = ${mm(s.w_A, 1)}; σ_Ed = ${kN(s.C)}·10³ / (${n(s.w_A, 1)}·${n(p.t_A, 0)}) = ${MPa(sA)};  ${limTxt}`,
      E_d: sA, R_d: lim, kind: 'stress', combination: combo, element_ref: 'member:S' + sd, notes: [note], E_label: 'σ_Ed', R_label: 'σ_Rd,max' }),
    make({ id: `STRUT_${sd}_B`, group: 'Krzyżulce', title: `Krzyżulec S${sd} (${SIDE_NAME[sd]}) — przekrój przy węźle B`, clause, basis: BASIS.NORMATIVE,
      formula: 'σ_Ed = C_Ed / (w_B·t_B) ≤ σ_Rd,max;  w_B = √(x_c² + a_B²) (węzeł hydrostatyczny)', symbols: Object.assign({}, sym, { x_c: 'wysokość strefy ściskanej przy licu', a_B: 'szerokość poziomej ścianki węzła B' }),
      substitution: `w_B = √(${n(s.x_c, 1)}² + ${n(s.a_B, 1)}²) = ${mm(s.w_B, 1)}; σ_Ed = ${kN(s.C)}·10³ / (${n(s.w_B, 1)}·${n(p.t_B, 0)}) = ${MPa(sB)};  ${limTxt}`,
      E_d: sB, R_d: lim, kind: 'stress', combination: combo, element_ref: 'member:S' + sd, notes: [note], E_label: 'σ_Ed', R_label: 'σ_Rd,max' }),
    make({ id: `STRUT_${sd}_TANMIN`, group: 'Model', title: `Nachylenie krzyżulca S${sd}: tan θ ≥ 1,0`, clause: 'EN 1992-1-1 zał. J.3(1)', basis: BASIS.INFORMATIVE,
      formula: 'tan θ ≥ 1,0  (warunek: η = 1,0 / tan θ ≤ 1)', symbols: { 'θ': 'kąt nachylenia krzyżulca do osi cięgna' },
      substitution: `tan θ = z0 / (ξ_A − ξ_B) = ${n(s.z0, 1)} / ${n(s.xi_A - s.xi_B, 1)} = ${n(tanT, 3)}`, E_d: p.tan_min, R_d: tanT, kind: 'ratio', combination: combo, element_ref: 'member:S' + sd,
      notes: ['Niespełnienie oznacza, że model J.3 jest poza zakresem stosowania — wymagana alternatywna metoda (belka wspornikowa 6.1/6.2 lub analiza nieliniowa / MES), NIE wykonana przez program.'], recommendation: true, E_label: 'tan θ_min', R_label: 'tan θ' }),
    make({ id: `STRUT_${sd}_TANMAX`, group: 'Model', title: `Nachylenie krzyżulca S${sd}: tan θ ≤ 2,5`, clause: 'EN 1992-1-1 zał. J.3(1)', basis: BASIS.INFORMATIVE,
      formula: 'tan θ ≤ 2,5', symbols: { 'θ': 'kąt nachylenia krzyżulca do osi cięgna' }, substitution: `tan θ = ${n(tanT, 3)} (θ = ${n(s.theta_deg, 2)}°)`,
      E_d: tanT, R_d: p.tan_max, kind: 'ratio', combination: combo, element_ref: 'member:S' + sd,
      notes: ['Niespełnienie oznacza, że model J.3 jest poza zakresem stosowania — wymagana alternatywna metoda (belka wspornikowa 6.1/6.2 lub analiza nieliniowa / MES), NIE wykonana przez program.'], recommendation: true, E_label: 'tan θ', R_label: 'tan θ_max' }),
  ];
}
function splittingForce(C, a, b, H) {
  if (b <= a) return [0, 'brak rozchodzenia (b ≤ a)', 'T = 0'];
  if (b <= H / 2) return [0.25 * (b - a) / b * C, 'nieciągłość częściowa (b ≤ H/2), wzór (6.58)', 'T = ¼·(b − a)/b·F'];
  const h = H / 2;
  return [Math.max(0.25 * (1 - 0.7 * a / h) * C, 0), 'nieciągłość pełna (b > H/2), wzór (6.59), h = H/2', 'T = ¼·(1 − 0,7·a/h)·F'];
}
function splittingCheck(sm, strut, R_links, linksDesc, combo) {
  const s = sm.state, sd = sm.params.side;
  if (strut.shape !== 'butelkowy') return [make({ id: 'SPLIT_' + sd, group: 'Rozłupywanie', title: `Rozciąganie poprzeczne krzyżulca S${sd} (rozłupywanie)`, clause: 'EN 1992-1-1 §6.5.3(3), rys. 6.25', basis: BASIS.NORMATIVE,
    formula: 'T = f(a, b, H, F)', substitution: `Krzyżulec pryzmatyczny (b_dost = ${mm(strut.b_avail)} ≈ w) — brak rozchodzenia pola naprężeń.`, kind: 'force', combination: combo, element_ref: 'member:S' + sd, status: ST.NA }), 0];
  let best = [0, '', '', 0];
  [s.w_A, s.w_B].forEach(a => { const [T, rg, fml] = splittingForce(s.C, a, strut.b_avail, strut.length); if (T >= best[0]) best = [T, rg, fml, a]; });
  const [T, rg, fml, a] = best;
  return [make({ id: 'SPLIT_' + sd, group: 'Rozłupywanie', title: `Zbrojenie przeciw rozłupywaniu krzyżulca S${sd} (krzyżulec butelkowy)`, clause: 'EN 1992-1-1 §6.5.3(3), wzory (6.58)/(6.59), rys. 6.25', basis: BASIS.NORMATIVE,
    formula: `${fml};  T ≤ Σ A_sw·f_ywd·sin γ`, symbols: { F: 'siła w krzyżulcu C_Ed', a: 'szerokość krzyżulca w węźle (węższy koniec)', b: 'dostępna szerokość rozchodzenia (z geometrii obrysu)', H: 'długość krzyżulca między węzłami', 'γ': 'kąt między prętem poprzecznym a osią krzyżulca' },
    substitution: `${rg}: F = ${kN(s.C)}, a = ${mm(a, 1)}, b = ${mm(strut.b_avail, 1)}, H = ${mm(strut.length, 1)} → T = ${kN(T)};  nośność zbrojenia przecinającego krzyżulec: ${linksDesc} = ${kN(R_links)}`,
    E_d: T, R_d: R_links, kind: 'force', combination: combo, element_ref: 'member:S' + sd,
    notes: ['Zastosowanie 6.5.3(3) do krzyżulca wspornika: H przyjęto jako długość krzyżulca między węzłami, b — dostępną szerokość w połowie długości (interpretacja inżynierska).'], E_label: 'T_Ed', R_label: 'T_Rd' }), T];
}
Object.assign(WS, { strutChecks, splittingForce, splittingCheck });

/* ================================================================== węzły (6.5.4) i docisk (6.7) */
const NODE_DESC = { CCC: ['k₁', 'k1_node', '(6.60)', '6.5.4(4)a) — węzeł ściskany bez zakotwionych cięgien'], CCT: ['k₂', 'k2_node', '(6.61)', '6.5.4(4)b) — węzeł z cięgnem zakotwionym w jednym kierunku'], CTT: ['k₃', 'k3_node', '(6.62)', '6.5.4(4)c) — węzeł z cięgnami w więcej niż jednym kierunku'] };
const classifyNode = nt => nt <= 0 ? 'CCC' : nt === 1 ? 'CCT' : 'CTT';
function limitText(type, mats, ps, inc) {
  const [sy, key] = NODE_DESC[type], k = ps.v(key), c = mats.concrete, f = inc ? ps.v('node_increase') : 1, val = f * k * c.nu_prime * c.fcd;
  return [val, `σ_Rd,max = ${inc ? '1,10·' : ''}${sy}·ν'·f_cd = ${inc ? '1,10·' : ''}${n(k, 2)}·${n(c.nu_prime, 3)}·${n(c.fcd)} = ${MPa(val)}`];
}
function nodeChecks(sm, mats, ps, st, combo) {
  const p = sm.params, s = sm.state, sd = p.side, inc = !!(st.node_10pct && (st.node_10pct_justification || '').trim());
  const ni = inc ? ['Zastosowano zwiększenie o 10% wg 6.5.4(5) — uzasadnienie projektanta: ' + st.node_10pct_justification.trim()] : [];
  const [limA, txtA] = limitText('CCT', mats, ps, inc), [limB, txtB] = limitText('CCC', mats, ps, inc);
  const sb = stress(p.V, p.a_ef, p.t_A), sA = stress(s.C, s.w_A, p.t_A), sB = stress(s.Fc, s.x_c, p.t_B);
  return [
    make({ id: `NODE_A_${sd}_BEAR`, group: 'Węzły', title: `Węzeł A${sd} (CCT) — ścianka docisku pod płytą`, clause: 'EN 1992-1-1 §6.5.4(4)b), wzór (6.61), rys. 6.27', basis: BASIS.NORMATIVE,
      formula: "σ_Rd,1 = F_Ed / (a_ef·t_A) ≤ k₂·ν'·f_cd", symbols: { F_Ed: 'pionowa siła obliczeniowa', a_ef: 'efektywna długość płyty (a_p − 2|e|)', t_A: 'efektywna szerokość płyty (b_p − 2|e_y|)' },
      substitution: `a_ef = ${n(p.a_p, 0)} − 2·${n(Math.abs(p.e_rel), 1)} = ${mm(p.a_ef, 1)}; σ = ${kN(p.V)}·10³ / (${n(p.a_ef, 1)}·${n(p.t_A, 0)}) = ${MPa(sb)};  ${txtA}`,
      E_d: sb, R_d: limA, kind: 'stress', combination: combo, element_ref: 'node:A' + sd, notes: ni, E_label: 'σ_Ed', R_label: 'σ_Rd,max' }),
    make({ id: `NODE_A_${sd}_STRUT`, group: 'Węzły', title: `Węzeł A${sd} (CCT) — ścianka krzyżulca`, clause: 'EN 1992-1-1 §6.5.4(4)b), wzór (6.61), rys. 6.27', basis: BASIS.NORMATIVE,
      formula: "σ_Rd,2 = C_Ed / (a₂·t_A) ≤ k₂·ν'·f_cd;  a₂ = a_ef·sin θ + u·cos θ", symbols: { C_Ed: 'siła w krzyżulcu', 'a₂': 'szerokość ścianki krzyżulca w węźle', u: 'wysokość strefy cięgna' },
      substitution: `a₂ = ${mm(s.w_A, 1)}; σ = ${kN(s.C)}·10³ / (${n(s.w_A, 1)}·${n(p.t_A, 0)}) = ${MPa(sA)};  ${txtA}`,
      E_d: sA, R_d: limA, kind: 'stress', combination: combo, element_ref: 'node:A' + sd, notes: ni, E_label: 'σ_Ed', R_label: 'σ_Rd,max' }),
    make({ id: `NODE_B_${sd}`, group: 'Węzły', title: `Węzeł B${sd} (CCC) przy licu słupa — strefa ściskana`, clause: 'EN 1992-1-1 §6.5.4(4)a), wzór (6.60), §6.5.4(8)', basis: BASIS.NORMATIVE,
      formula: "σ_Ed = F_c / (x_c·t_B) = V_Ed / (a_B·t_B) = C_Ed / (w_B·t_B) ≤ k₁·ν'·f_cd  (węzeł hydrostatyczny)", symbols: { F_c: 'pozioma siła ściskająca przy licu', x_c: 'wysokość strefy ściskanej', a_B: 'szerokość poziomej ścianki węzła', t_B: 'grubość efektywna' },
      substitution: `σ = ${kN(s.Fc)}·10³ / (${n(s.x_c, 1)}·${n(p.t_B, 0)}) = ${MPa(sB)};  ${txtB};  x_c = ${mm(s.x_c, 1)} (dobór: ${sm.search.method || '—'})`,
      E_d: sB, R_d: limB, kind: 'stress', combination: combo, element_ref: 'node:B' + sd, notes: ni, E_label: 'σ_Ed', R_label: 'σ_Rd,max' }),
  ];
}
function nodeCCheck(T, combo, double) {
  const txt = double ? 'Cięgno ciągłe przez słup (wsporniki dwustronne) — różnica sił cięgien przekazywana na słup przyczepnością; strefa słupa wymaga osobnej weryfikacji.'
    : 'Węzeł zakotwienia cięgna w słupie (strefa słupa) — siła w cięgnie przekazywana na słup. Nośność strefy węzłowej słupa zależy od sił w słupie i jego zbrojenia — poza zakresem lokalnego modelu wspornika.';
  return make({ id: 'NODE_C', group: 'Węzły', title: 'Węzeł C — zakotwienie / przejście cięgna w słupie', clause: 'EN 1992-1-1 §6.5.4, J.3(4)', basis: BASIS.MODEL, formula: '—',
    substitution: txt + ` Siła: ${kN(T)}.`, E_d: T, R_d: null, kind: 'force', combination: combo, element_ref: 'node:C', status: ST.VERIFY });
}
function localBearingCheck(gm, sm, mats, ps, combo) {
  const p = sm.params, sd = p.side, sg = gm.sides[sd], c = mats.concrete;
  const a1 = p.a_ef, b1 = p.t_A, xc = sg.plate.xi_center + p.e_rel, hav = sg.depth_at(xc);
  let d2 = Math.min(3 * a1, a1 + hav, 2 * (sg.l_c - xc), 2 * xc), b2 = Math.min(3 * b1, b1 + hav, 2 * (gm.b / 2 - Math.abs(p.e_y)));
  d2 = Math.max(d2, a1); b2 = Math.max(b2, b1);
  const Ac0 = a1 * b1, Ac1 = d2 * b2, ratio = Math.sqrt(Ac1 / Ac0), FRdu = Math.min(Ac0 * c.fcd * ratio, ps.v('bearing_max') * c.fcd * Ac0);
  return make({ id: 'BEARING_' + sd, group: 'Docisk', title: `Docisk lokalny pod płytą oporową (${SIDE_NAME[sd]})`, clause: 'EN 1992-1-1 §6.7(2), wzór (6.63), rys. 6.29', basis: BASIS.NORMATIVE,
    formula: 'F_Rdu = A_c0·f_cd·√(A_c1/A_c0) ≤ 3,0·f_cd·A_c0', symbols: { A_c0: 'pole obciążone (a_ef × b_ef)', A_c1: 'maksymalne obliczeniowe pole rozdziału (podobne, współśrodkowe, ograniczone krawędziami i wysokością h)', h: 'wysokość wspornika w miejscu obciążenia' },
    substitution: `A_c0 = ${n(a1, 1)}·${n(b1, 1)} = ${n(Ac0, 0)} mm²; A_c1 = ${n(d2, 1)}·${n(b2, 1)} = ${n(Ac1, 0)} mm² (d₂ ≤ min(3d₁; d₁+h; 2·odl. od krawędzi), h = ${mm(hav)}); F_Rdu = ${n(Ac0, 0)}·${n(c.fcd)}·${n(ratio, 3)} = ${kN(FRdu)}`,
    E_d: p.V, R_d: FRdu, kind: 'force', combination: combo, element_ref: 'node:A' + sd,
    notes: ['Rozkład obciążenia przyjęto jako równomierny na powierzchni płyty (6.7(1)). Pole A_c1 ograniczono konserwatywnie odległością od lica słupa.'], E_label: 'F_Ed', R_label: 'F_Rdu' });
}
function manualMemberChecks(model, sol, man, mats, ps, st, combo) {
  const out = [], c = mats.concrete, [sLim, sFml] = strutLimit(c, ps, st.strut_limit);
  const mem = {}; man.members.forEach(m => { mem[m.id] = m; });
  const tiesAt = {}, nodeMax = {}; man.nodes.forEach(q => { tiesAt[q.id] = 0; nodeMax[q.id] = [0, '']; });
  man.members.forEach(m => {
    const N = sol.forces[m.id] || 0;
    if (m.kind === 'strut') {
      if (N > 1e-6) { out.push(make({ id: 'MAN_SIGN_' + m.id, group: 'Model', title: `Zgodność typu pręta ${m.id} (krzyżulec)`, clause: 'EN 1992-1-1 §5.6.4, §6.5.1', basis: BASIS.MODEL, formula: 'N ≤ 0 dla krzyżulca', substitution: `N = ${kN(N)} (rozciąganie) — pręt zadeklarowany jako krzyżulec przenosi rozciąganie.`, E_d: N, R_d: 0, kind: 'force', combination: combo, element_ref: 'member:' + m.id, status: ST.FAIL })); return; }
      const C = -N;
      if (!(m.width > 0) || !(m.thickness > 0)) { out.push(make({ id: 'MAN_STRUT_' + m.id, group: 'Krzyżulce', title: 'Krzyżulec ' + m.id, clause: 'EN 1992-1-1 §6.5.2', basis: BASIS.NORMATIVE, formula: '—', substitution: 'Brak szerokości/grubości krzyżulca.', kind: 'stress', combination: combo, element_ref: 'member:' + m.id, status: ST.FAIL, conclusion: 'Nie podano wymiarów krzyżulca.' })); return; }
      const sg = stress(C, m.width, m.thickness);
      out.push(make({ id: 'MAN_STRUT_' + m.id, group: 'Krzyżulce', title: 'Krzyżulec ' + m.id, clause: 'EN 1992-1-1 §6.5.2', basis: BASIS.NORMATIVE, formula: `σ = C/(w·t) ≤ ${sFml}`, symbols: { w: 'szerokość podana przez użytkownika', t: 'grubość' },
        substitution: `σ = ${kN(C)}·10³/(${n(m.width, 1)}·${n(m.thickness, 0)}) = ${MPa(sg)}; σ_Rd,max = ${MPa(sLim)}`, E_d: sg, R_d: sLim, kind: 'stress', combination: combo, element_ref: 'member:' + m.id, E_label: 'σ_Ed', R_label: 'σ_Rd,max' }));
      [m.n1, m.n2].forEach(nid => { if (nodeMax[nid] && sg > nodeMax[nid][0]) nodeMax[nid] = [sg, m.id]; });
    } else {
      if (m.n1 in tiesAt) tiesAt[m.n1]++; if (m.n2 in tiesAt) tiesAt[m.n2]++;
      if (N < -1e-6) { out.push(make({ id: 'MAN_SIGN_' + m.id, group: 'Model', title: `Zgodność typu pręta ${m.id} (cięgno)`, clause: 'EN 1992-1-1 §5.6.4, §6.5.1', basis: BASIS.MODEL, formula: 'N ≥ 0 dla cięgna', substitution: `N = ${kN(N)} (ściskanie) — pręt zadeklarowany jako cięgno jest ściskany.`, E_d: -N, R_d: 0, kind: 'force', combination: combo, element_ref: 'member:' + m.id, status: ST.FAIL })); return; }
      const TRd = m.As * mats.steel.fyd;
      out.push(make({ id: 'MAN_TIE_' + m.id, group: 'Cięgna', title: 'Cięgno ' + m.id, clause: 'EN 1992-1-1 §6.5.3(1)', basis: BASIS.NORMATIVE, formula: 'T_Ed ≤ T_Rd = A_s·f_yd', symbols: { A_s: 'pole zbrojenia cięgna' },
        substitution: `T_Rd = ${n(m.As, 0)}·${n(mats.steel.fyd, 1)} = ${kN(TRd)}`, E_d: N, R_d: TRd, kind: 'force', combination: combo, element_ref: 'member:' + m.id, E_label: 'T_Ed', R_label: 'T_Rd' }));
    }
  });
  const sup = {}; man.supports.forEach(s => { sup[s.node] = s; });
  const inc = !!(st.node_10pct && (st.node_10pct_justification || '').trim());
  man.nodes.forEach(q => {
    const type = classifyNode(tiesAt[q.id]), [lim, txt] = limitText(type, mats, ps, inc);
    let [sg, mid] = nodeMax[q.id];
    if (sup[q.id] && sol.reactions[q.id]) {
      const [rx, ry] = sol.reactions[q.id], R = Math.hypot(rx, ry), sp = sup[q.id];
      const ts = Object.values(mem).filter(m => (m.n1 === q.id || m.n2 === q.id) && m.kind === 'strut').map(m => m.thickness);
      const t = ts.length ? Math.min(...ts) : 0;
      if (sp.bearing_width > 0 && t > 0) { const sr = stress(R, sp.bearing_width, t); if (sr > sg) { sg = sr; mid = 'reakcja'; } }
    }
    if (sg <= 0) return;
    out.push(make({ id: 'MAN_NODE_' + q.id, group: 'Węzły', title: `Węzeł ${q.id} (${type})`, clause: 'EN 1992-1-1 §' + NODE_DESC[type][3], basis: BASIS.NORMATIVE, formula: 'max σ na ściankach węzła ≤ σ_Rd,max',
      substitution: `σ_max = ${MPa(sg)} (od: ${mid}); ${txt}`, E_d: sg, R_d: lim, kind: 'stress', combination: combo, element_ref: 'node:' + q.id, E_label: 'σ_Ed', R_label: 'σ_Rd,max' }));
  });
  return out;
}
Object.assign(WS, { nodeChecks, nodeCCheck, localBearingCheck, manualMemberChecks, classifyNode });

/* ================================================================== cięgna (6.5.3) */
function tieChecks(sm, As_prov, barsDesc, c_t_bars, mats, ps, combo) {
  const p = sm.params, s = sm.state, sd = p.side, fyd = mats.steel.fyd;
  const AsReq = Math.max(s.T, 0) / fyd, TRd = As_prov * fyd, tol = ps.v('tie_axis_tol') * p.d, dev = Math.abs(p.c_t - c_t_bars);
  return [
    make({ id: 'TIE_' + sd, group: 'Cięgna', title: `Cięgno główne T${sd} (${SIDE_NAME[sd]}) — nośność`, clause: 'EN 1992-1-1 §6.5.3(1); zał. J.3, rys. J.5', basis: BASIS.NORMATIVE,
      formula: 'T_Ed = F_c + H_Ed ≤ T_Rd = A_s,prov·f_yd;  A_s,req = T_Ed / f_yd', symbols: { T_Ed: 'siła w cięgnie z równowagi modelu', F_c: 'pozioma siła w węźle B', H_Ed: 'siła pozioma (od słupa +)', f_yd: 'obliczeniowa granica plastyczności stali' },
      substitution: `T_Ed = ${kN(s.Fc)} + ${kN(p.H)} = ${kN(s.T)}; A_s,req = ${kN(s.T)}·10³ / ${n(fyd, 1)} = ${mm2(AsReq)}; A_s,prov = ${mm2(As_prov)} (${barsDesc}); T_Rd = ${kN(TRd)}`,
      E_d: s.T, R_d: TRd, kind: 'force', combination: combo, element_ref: 'member:T' + sd,
      notes: [`Równoważnie z rys. J.5: F_td = F_Ed·a_c/z0 + H_Ed·(a_H + z0)/z0 — a_c liczone do węzła B (ξ_B = ${n(s.xi_B, 1)} mm).`], E_label: 'T_Ed', R_label: 'T_Rd' }),
    make({ id: 'TIE_AXIS_' + sd, group: 'Cięgna', title: `Położenie osi cięgna T${sd} względem środka ciężkości zbrojenia`, clause: 'EN 1992-1-1 §6.5.3, §6.5.4(7) — spójność modelu', basis: BASIS.MODEL,
      formula: '|c_t,model − c_t,zbr| ≤ tol·d', symbols: { 'c_t,model': 'odległość osi cięgna w modelu od górnej krawędzi', 'c_t,zbr': 'odległość środka ciężkości prętów od górnej krawędzi' },
      substitution: `|${n(p.c_t, 1)} − ${n(c_t_bars, 1)}| = ${mm(dev, 1)} ≤ ${n(ps.v('tie_axis_tol'), 2)}·${n(p.d, 0)} = ${mm(tol, 1)}`, E_d: dev, R_d: tol, kind: 'length', combination: combo, element_ref: 'member:T' + sd,
      E_label: 'Δ', R_label: 'tol', recommendation: true, notes: ['Ręczna korekta d zmienia położenie cięgna i geometrię węzła A — przy odchyłce większej od tolerancji model wymaga oceny projektanta.'] }),
  ];
}
WS.tieChecks = tieChecks;

/* ================================================================== zakotwienia i gięcie (rozdz. 8) */
const ANCHOR_LABEL = { straight: 'pręt prosty', bend_down: 'odgięcie 90° (rys. 8.1b)', hook: 'hak (rys. 8.1c)', loop: 'pętla pozioma (rys. 8.1d)', welded_bar: 'przyspawany pręt poprzeczny (rys. 8.1e)', mechanical: 'zakotwienie mechaniczne (wg ETA)', continuous: 'pręt ciągły przez słup' };
function bondStrength(mats, ps, phi, bond) {
  const eta1 = bond === 'good' ? 1 : ps.v('eta1_poor'), eta2 = phi <= 32 ? 1 : (132 - phi) / 100;
  return [ps.v('bond_coef') * eta1 * eta2 * mats.concrete.fctd_bond, eta1, eta2];
}
function weldedBarCapacity(a, mats, ps) {
  const phiT = a.phi_t || a.phi;
  if (!(phiT >= 14 && phiT <= 32)) return [0, `φ_t = ${phiT.toFixed(0)} mm poza zakresem 14–32 mm wzoru (8.8N) — nie uwzględniono F_btd.`];
  const c = mats.concrete, fyd = mats.steel.fyd, x = 2 * (a.c / phiT) + 1, y = 0.015 + 0.14 * Math.exp(-0.18 * x);
  const std = Math.min(c.fctd / y, 3 * c.fcd), lt = a.s_cc > 0 ? a.s_cc : phiT * 10, ltd = Math.min(1.16 * phiT * Math.sqrt(fyd / std), lt);
  const Fwd = ps.v('fwd_factor') * barArea(a.phi) * fyd, F = Math.min(ltd * phiT * std, Fwd);
  return [F, `(8.8N): x = 2·${n(a.c, 1)}/${n(phiT, 0)} + 1 = ${n(x, 3)}; y = ${n(y, 4)}; σ_td = ${n(std, 2)} MPa; l_td = ${n(ltd, 1)} mm; F_btd = min(${n(ltd * phiT * std / 1e3, 2)}; F_wd = ${n(Fwd / 1e3, 2)}) = ${n(F / 1e3, 2)} kN/pręt`];
}
function anchorageLengthInner(a, mats, ps, wmode) {
  const phi = a.phi, [fbd, eta1, eta2] = bondStrength(mats, ps, phi, a.bond);
  let sigma = a.As_prov > 0 ? Math.max(a.force, 0) / a.As_prov : Infinity;
  if (isFinite(sigma)) sigma = Math.min(sigma, mats.steel.fyd);
  const notes = []; let Fbtd = 0;
  if (wmode === '8.6') { const [F, txt] = weldedBarCapacity(a, mats, ps); Fbtd = F; const red = F / barArea(phi); notes.push(txt + `; σ_sd zredukowane o F_btd/A_s = ${n(red, 1)} MPa (8.6(2)).`); sigma = Math.max(sigma - red, 0); }
  const lbRqd = (phi / 4) * (sigma / fbd);
  const straight = ['straight', 'welded_bar', 'mechanical', 'continuous'].includes(a.anchor);
  let cd, cdTxt;
  if (a.anchor === 'loop') { cd = a.c; cdTxt = 'c_d = c (pętle, rys. 8.3c)'; }
  else if (straight) { cd = Math.min(a.a_clear / 2, a.c1, a.c); cdTxt = 'c_d = min(a/2; c₁; c) (pręty proste, rys. 8.3a)'; }
  else { cd = Math.min(a.a_clear / 2, a.c1); cdTxt = 'c_d = min(a/2; c₁) (odgięcia/haki, rys. 8.3b)'; }
  let a1, a2;
  if (straight) { a1 = 1; a2 = Math.min(1, Math.max(0.7, 1 - 0.15 * (cd - phi) / phi)); }
  else { a1 = cd > 3 * phi ? 0.7 : 1; a2 = Math.min(1, Math.max(0.7, 1 - 0.15 * (cd - 3 * phi) / phi)); }
  let a3;
  if (a.alpha3_mode === 'computed') { const As1 = barArea(phi), lam = (a.sum_Ast - 0.25 * As1) / As1; a3 = Math.min(1, Math.max(0.7, 1 - a.K * lam)); notes.push(`α₃: λ = (ΣA_st − 0,25·A_s)/A_s = ${n(lam, 3)}, K = ${n(a.K, 2)}.`); }
  else { a3 = 1; notes.push('α₃ = 1,0 — konserwatywnie pominięto skrępowanie zbrojeniem poprzecznym.'); }
  const a4 = (a.anchor === 'welded_bar' && wmode !== '8.6') ? 0.7 : 1, a5 = 1;
  notes.push('α₅ = 1,0 — pominięto korzystny docisk poprzeczny (założenie bezpieczne).');
  const prod = a2 * a3 * a5, lim = ps.v('alpha235_min');
  if (prod < lim) { a2 *= lim / prod; notes.push('Iloczyn α₂α₃α₅ ograniczono do 0,7 (8.5).'); }
  const lbMin = Math.max(ps.v('lbmin_ratio') * lbRqd, 10 * phi, 100);
  const lbd = Math.max(a1 * a2 * a3 * a4 * a5 * lbRqd, lbMin);
  notes.unshift(cdTxt + ` = ${n(cd, 1)} mm`);
  return { inp: a, fbd, eta1, eta2, sigma_sd: sigma, lb_rqd: lbRqd, cd, alphas: { 'α1': a1, 'α2': a2, 'α3': a3, 'α4': a4, 'α5': a5 }, lb_min: lbMin, lbd, notes, Fbtd, method: wmode === '8.6' ? '8.6' : '8.4' };
}
function anchorageLength(a, mats, ps) {
  if (a.anchor === 'welded_bar') { const r1 = anchorageLengthInner(a, mats, ps, 'alpha4'), r2 = anchorageLengthInner(a, mats, ps, '8.6'); return r2.lbd < r1.lbd ? r2 : r1; }
  return anchorageLengthInner(a, mats, ps, '');
}
function anchorageCheck(a, mats, ps, combo, extra) {
  if (a.anchor === 'mechanical') return [make({ id: a.id, group: 'Zakotwienie', title: a.title, clause: 'EN 1992-1-1 §8.4.1(2), §8.8; ETA urządzenia', basis: BASIS.NORMATIVE, formula: 'Nośność zakotwienia mechanicznego wg aprobaty (ETA) / badań',
    substitution: `Siła do zakotwienia: ${kN(a.force)}. Nośność głowicy/urządzenia nie jest obliczana przez program.`, E_d: a.force, R_d: null, kind: 'force', combination: combo, element_ref: a.element_ref, status: ST.VERIFY }), null];
  const r = anchorageLength(a, mats, ps), al = r.alphas;
  const sub = `f_bd = 2,25·${n(r.eta1, 2)}·${n(r.eta2, 2)}·${n(mats.concrete.fctd_bond, 3)} = ${MPa(r.fbd, 3)}; σ_sd = ${kN(a.force)}·10³/${n(a.As_prov, 0)}${r.method === '8.6' ? ' − F_btd/A_s' : ''} = ${MPa(r.sigma_sd, 1)}; l_b,rqd = (${n(a.phi, 0)}/4)·(${n(r.sigma_sd, 1)}/${n(r.fbd, 3)}) = ${mm(r.lb_rqd, 0)}; α₁…α₅ = ${n(al['α1'], 2)}·${n(al['α2'], 3)}·${n(al['α3'], 2)}·${n(al['α4'], 2)}·${n(al['α5'], 2)}; l_b,min = ${mm(r.lb_min, 0)}; l_bd = ${mm(r.lbd, 0)}; l_dost = ${mm(a.l_avail, 0)}`;
  const c = make({ id: a.id, group: 'Zakotwienie', title: a.title + ' — ' + (ANCHOR_LABEL[a.anchor] || a.anchor), clause: 'EN 1992-1-1 §8.4.2–8.4.4, wzory (8.2)–(8.6), tabl. 8.2' + (extra || ''), basis: BASIS.NORMATIVE,
    formula: 'l_bd = α₁·α₂·α₃·α₄·α₅·(φ/4)·(σ_sd/f_bd) ≥ l_b,min;  l_bd ≤ l_dost', symbols: { f_bd: 'graniczne naprężenie przyczepności (8.2)', 'η₁': 'warunki przyczepności (rys. 8.2)', 'σ_sd': 'naprężenie w pręcie na początku zakotwienia', c_d: 'otulina/odstęp wg rys. 8.3', l_dost: 'długość dostępna mierzona wg J.3(4) / rys. 8.1' },
    substitution: sub, E_d: r.lbd, R_d: a.l_avail, kind: 'length', combination: combo, element_ref: a.element_ref, notes: r.notes, E_label: 'l_bd', R_label: 'l_dost' });
  if (a.anchor === 'welded_bar') { c.notes.push("Jakość połączenia spawanego wymaga wykazania (8.6(1), EN ISO 17660) — F_wd przyjęto wg parametru 'fwd_factor'."); c.notes.push('Ścieżka obliczeń: ' + (r.method === '8.6' ? 'redukcja σ_sd o F_btd (8.6(2)), α₄ = 1,0' : 'α₄ = 0,7 (tabl. 8.2)')); }
  return [c, r];
}
const mandrelMinTable = (phi, ps) => (phi <= 16 ? ps.v('mandrel_small') : ps.v('mandrel_large')) * phi;
function mandrelChecks(id, title, phi, phiM, Fbt, ab, mats, ps, combo, ref) {
  const tmin = mandrelMinTable(phi, ps), c = mats.concrete, fcd = Math.min(c.fcd, c.alpha_cc * ps.v('fcd_mandrel_cap') / c.gamma_c);
  const req = Fbt * (1 / ab + 1 / (2 * phi)) / fcd;
  return [
    make({ id: id + '_T81', group: 'Zakotwienie', title: title + ' — min. średnica trzpienia (tabl. 8.1N)', clause: 'EN 1992-1-1 §8.3(2), tabl. 8.1N', basis: BASIS.NORMATIVE, formula: 'φ_m ≥ φ_m,min (4φ dla φ ≤ 16; 7φ dla φ > 16)',
      symbols: { 'φ_m': 'średnica trzpienia (wewnętrzna średnica gięcia)' }, substitution: `φ_m,min = ${mm(tmin)}; φ_m = ${mm(phiM)}`, E_d: tmin, R_d: phiM, kind: 'length', combination: combo, element_ref: ref, E_label: 'φ_m,min', R_label: 'φ_m' }),
    make({ id: id + '_81', group: 'Zakotwienie', title: title + ' — docisk betonu w odgięciu, wzór (8.1)', clause: 'EN 1992-1-1 §8.3(3), wzór (8.1)', basis: BASIS.NORMATIVE, formula: 'φ_m,min ≥ F_bt·((1/a_b) + 1/(2φ)) / f_cd',
      symbols: { F_bt: 'siła rozciągająca w pręcie na początku odgięcia (przyjęto pełną)', a_b: 'połowa rozstawu osiowego prętów (lub otulina + φ/2 przy krawędzi)', f_cd: '≤ wartość dla C55/67' },
      substitution: `F_bt = ${kN(Fbt, 2)}, a_b = ${mm(ab, 1)}: φ_m,min = ${n(Fbt, 0)}·(1/${n(ab, 1)} + 1/${n(2 * phi, 0)})/${n(fcd, 2)} = ${mm(req, 0)}; φ_m = ${mm(phiM)}`,
      E_d: req, R_d: phiM, kind: 'length', combination: combo, element_ref: ref, E_label: 'φ_m,req', R_label: 'φ_m' }),
  ];
}
Object.assign(WS, { ANCHOR_LABEL, bondStrength, weldedBarCapacity, anchorageLength, anchorageCheck, mandrelMinTable, mandrelChecks });

/* ================================================================== konstruowanie zbrojenia */
const LINK_DIAMETERS = [8, 10, 12, 14, 16];
function cMinDur(m) {
  const grp = ND.expGroup[m.exposure]; if (!grp) throw new Error('Nieobsługiwana klasa ekspozycji ' + m.exposure);
  const i = ND.structClasses.indexOf(m.structural_class); if (i < 0) throw new Error('Nieznana klasa konstrukcji ' + m.structural_class);
  return ND.t44N[grp][i];
}
function coverRequirements(m, ps, phiMain, phiH, phiV, hasV, hasH) {
  const cdur = cMinDur(m), add = ps.v('delta_c_dur_gamma') - ps.v('delta_c_dur_st') - ps.v('delta_c_dur_add'), dev = m.delta_c_dev;
  const extra = m.d_g > 32 ? 5 : 0, phiLink = Math.max(hasH ? phiH : 0, hasV ? phiV : 0);
  const reqLink = phiLink > 0 ? Math.max(phiLink + extra, cdur + add, 10) + dev : 0;
  const reqMain = Math.max(phiMain + extra, cdur + add, 10) + dev;
  let cnom, user;
  if (m.c_nom_user !== null && m.c_nom_user !== undefined) { cnom = m.c_nom_user; user = true; }
  else { cnom = Math.ceil(Math.max(reqLink, reqMain - (hasV ? phiV : 0), reqMain - phiLink) / 5 - 1e-9) * 5; user = false; }
  return { exposure: m.exposure, structural_class: m.structural_class, c_min_dur: cdur, delta_c_dev: dev, c_nom_req_link: reqLink, c_nom_req_main: reqMain,
    c_nom: cnom, c_top_main: cnom + (hasV ? phiV : 0), c_side_main: cnom + phiLink, phi_link_outer: phiLink, user };
}
const sMin = (phi, dg, ps) => Math.max(ps.v('spacing_k1') * phi, dg + ps.v('spacing_k2'), 20);
function mainLayout(b, cv, phi, nn, layers, gap, dg, ps) {
  const smin = sMin(phi, dg, ps), gapV = (gap !== null && gap !== undefined) ? gap : smin, issues = [];
  if (nn < 2) issues.push('Wymagane co najmniej 2 pręty w warstwie (konstrukcyjnie — pręty w narożach strzemion).');
  const width = b - 2 * cv.c_side_main, aClear = nn >= 2 ? (width - nn * phi) / (nn - 1) : Infinity;
  let fits = true;
  if (nn >= 2 && aClear < smin - 1e-9) { fits = false; issues.push(`Odstęp w świetle a = ${aClear.toFixed(1)} mm < s_min = ${smin.toFixed(1)} mm.`); }
  if (layers > 1 && gapV < smin - 1e-9) { fits = false; issues.push(`Odstęp warstw ${gapV.toFixed(1)} mm < s_min = ${smin.toFixed(1)} mm.`); }
  if (nn < 2) fits = false;
  const depths = Array.from({ length: layers }, (_, k) => cv.c_top_main + phi / 2 + k * (phi + gapV));
  const z0 = -b / 2 + cv.c_side_main + phi / 2;
  const zs = nn >= 2 ? Array.from({ length: nn }, (_, i) => z0 + i * (aClear + phi)) : [0];
  const ml = { phi, n: nn, layers, gap_v: gapV, s_min: smin, a_clear: aClear, c_t: depths.reduce((s, v) => s + v, 0) / layers, layer_depths: depths, z_positions: zs, As: nn * layers * barArea(phi), fits, issues };
  ml.total_bars = nn * layers; ml.s_cc = aClear + phi;
  ml.desc = () => `${ml.total_bars}φ${phi.toFixed(0)}${layers > 1 ? ` w ${layers} warstwach` : ''}`;
  return ml;
}
function linksLayout(gm, sd, ml, cv, li, d, xiA, dg, ps) {
  const sg = gm.sides[sd], issues = []; let fits = true;
  const zone = (li.h_zone !== null && li.h_zone !== undefined) ? li.h_zone : ps.v('h_link_zone') * d;
  let hd = [];
  if (li.h_count > 0) {
    const smh = sMin(li.h_phi, dg, ps), yFirst = ml.layer_depths[ml.layer_depths.length - 1] + (ml.phi + li.h_phi) / 2 + ml.s_min;
    let yEnd = Math.max(ml.c_t + zone, yFirst); const yLim = sg.h_c - cv.c_nom - li.h_phi / 2; if (yEnd > yLim) yEnd = yLim;
    if (li.h_count === 1) hd = [yFirst];
    else { hd = Array.from({ length: li.h_count }, (_, k) => yFirst + (yEnd - yFirst) * k / (li.h_count - 1)); const clr = (yEnd - yFirst) / (li.h_count - 1) - li.h_phi; if (clr < smh - 1e-9) { fits = false; issues.push(`Strzemiona poziome: odstęp w świetle ${clr.toFixed(1)} mm < s_min ${smh.toFixed(1)} mm (strefa ${yFirst.toFixed(0)}–${yEnd.toFixed(0)} mm).`); } }
    if (yFirst > yLim) { fits = false; issues.push('Strzemiona poziome nie mieszczą się poniżej zbrojenia głównego.'); }
  }
  let vp = [];
  if (li.v_count > 0) {
    const smv = sMin(li.v_phi, dg, ps), x0 = cv.c_nom + li.v_phi / 2 + 25, x1 = Math.min(xiA, sg.l_c - cv.c_nom - li.v_phi / 2);
    if (x1 <= x0) { fits = false; issues.push('Brak miejsca na strzemiona pionowe między licem słupa a obciążeniem.'); }
    else if (li.v_count === 1) vp = [(x0 + x1) / 2];
    else { vp = Array.from({ length: li.v_count }, (_, k) => x0 + (x1 - x0) * k / (li.v_count - 1)); const clr = (x1 - x0) / (li.v_count - 1) - li.v_phi; if (clr < smv - 1e-9) { fits = false; issues.push(`Strzemiona pionowe: odstęp w świetle ${clr.toFixed(1)} mm < s_min ${smv.toFixed(1)} mm.`); } }
  }
  const ll = { h_phi: li.h_phi, h_depths: hd, v_phi: li.v_phi, v_positions: vp, i_phi: li.i_phi, i_count: li.i_count, h_zone: zone, issues, fits };
  ll.As_h = 2 * hd.length * barArea(li.h_phi); ll.As_v = 2 * vp.length * barArea(li.v_phi); ll.As_i = 2 * li.i_count * barArea(li.i_phi);
  ll.desc_h = () => hd.length ? `${hd.length} strz. poz. 2-cięte φ${li.h_phi.toFixed(0)}` : 'brak strz. poziomych';
  ll.desc_v = () => vp.length ? `${vp.length} strz. pion. 2-cięte φ${li.v_phi.toFixed(0)}` : 'brak strz. pionowych';
  return ll;
}
function hLinkXiMax(sg, cv, dpt) {
  let xm = sg.l_c - cv.c_nom; const target = dpt + cv.c_nom;
  if (sg.h_e < sg.h_c && target > sg.h_e && sg.l_c > sg.x_slope) { const t = (sg.h_c - target) / (sg.h_c - sg.h_e); xm = Math.min(xm, sg.x_slope + t * (sg.l_c - sg.x_slope)); }
  return xm;
}
function linksCrossingStrut(ll, gm, sd, cv, xiA, yA, xiB, yB) {
  const sg = gm.sides[sd]; let nh = 0;
  ll.h_depths.forEach(dpt => {
    const y = -dpt; if (!(y >= Math.min(yA, yB) && y <= Math.max(yA, yB))) return;
    const xs = Math.abs(yA - yB) > 1e-9 ? xiB + (xiA - xiB) * (y - yB) / (yA - yB) : xiA;
    if (hLinkXiMax(sg, cv, dpt) >= xs) nh++;
  });
  const nv = ll.v_positions.filter(x => x >= Math.min(xiB, xiA) && x <= Math.max(xiB, xiA)).length;
  return [nh, nv];
}
function coverChecks(cv, phiMain, combo) {
  const out = [], sym = { 'c_min,b': 'otulina ze względu na przyczepność (tabl. 4.2)', 'c_min,dur': 'otulina ze względu na trwałość (tabl. 4.4N)', 'Δc_dev': 'odchyłka wykonawcza' };
  if (cv.phi_link_outer > 0) out.push(make({ id: 'COVER_LINK', group: 'Konstrukcyjne', title: 'Otulina nominalna strzemion', clause: 'EN 1992-1-1 §4.4.1.1–4.4.1.3, wzory (4.1), (4.2), tabl. 4.2, 4.4N', basis: BASIS.NORMATIVE,
    formula: 'c_nom = max{c_min,b; c_min,dur; 10 mm} + Δc_dev', symbols: sym,
    substitution: `ekspozycja ${cv.exposure}, klasa ${cv.structural_class}: c_min,dur = ${mm(cv.c_min_dur)}; c_min,b = φ_s = ${mm(cv.phi_link_outer)}; c_nom,req = ${mm(cv.c_nom_req_link)}; przyjęto c_nom = ${mm(cv.c_nom)}`,
    E_d: cv.c_nom_req_link, R_d: cv.c_nom, kind: 'length', combination: combo || '', element_ref: 'rebar:cover', E_label: 'c_nom,req', R_label: 'c_nom' }));
  out.push(make({ id: 'COVER_MAIN', group: 'Konstrukcyjne', title: 'Otulina prętów zbrojenia głównego', clause: 'EN 1992-1-1 §4.4.1.1–4.4.1.3, tabl. 4.2, 4.4N', basis: BASIS.NORMATIVE,
    formula: 'c_main = c_nom + φ_s ≥ max{φ; c_min,dur; 10 mm} + Δc_dev', symbols: sym,
    substitution: `c_min,b = φ = ${mm(phiMain)}; c_nom,req = ${mm(cv.c_nom_req_main)}; c_main,góra = ${mm(cv.c_top_main)}, c_main,bok = ${mm(cv.c_side_main)}`,
    E_d: cv.c_nom_req_main, R_d: Math.min(cv.c_top_main, cv.c_side_main), kind: 'length', combination: combo || '', element_ref: 'rebar:cover', E_label: 'c_req', R_label: 'c_prov' }));
  return out;
}
function spacingChecks(ml, ll, sd, combo) {
  const out = [];
  if (ml.n >= 2) out.push(make({ id: 'SPACING_MAIN', group: 'Konstrukcyjne', title: 'Odstęp w świetle prętów zbrojenia głównego', clause: 'EN 1992-1-1 §8.2(2)', basis: BASIS.NORMATIVE,
    formula: 'a ≥ s_min = max{k₁·φ; d_g + k₂; 20 mm}', symbols: { a: 'odstęp w świetle prętów w warstwie' }, substitution: `a = ${mm(ml.a_clear, 1)}; s_min = ${mm(ml.s_min, 1)}`,
    E_d: ml.s_min, R_d: ml.a_clear, kind: 'length', combination: combo || '', element_ref: 'rebar:main', E_label: 's_min', R_label: 'a' }));
  else out.push(make({ id: 'SPACING_MAIN', group: 'Konstrukcyjne', title: 'Liczba prętów w warstwie', clause: 'Zasady konstruowania', basis: BASIS.ENGINEERING, formula: 'n ≥ 2', substitution: `n = ${ml.n}`, E_d: 2, R_d: ml.n, kind: 'ratio', combination: combo || '', element_ref: 'rebar:main' }));
  if (ml.layers > 1) out.push(make({ id: 'SPACING_LAYERS', group: 'Konstrukcyjne', title: 'Odstęp w świetle warstw zbrojenia głównego', clause: 'EN 1992-1-1 §8.2(2), (3)', basis: BASIS.NORMATIVE, formula: 's_v ≥ s_min',
    substitution: `s_v = ${mm(ml.gap_v, 1)}; s_min = ${mm(ml.s_min, 1)}`, E_d: ml.s_min, R_d: ml.gap_v, kind: 'length', combination: combo || '', element_ref: 'rebar:main', E_label: 's_min', R_label: 's_v' }));
  if (ll) out.push(make({ id: 'SPACING_LINKS_' + sd, group: 'Konstrukcyjne', title: 'Rozmieszczenie strzemion (mieszczenie się, odstępy)', clause: 'EN 1992-1-1 §8.2(2)', basis: BASIS.NORMATIVE, formula: 'odstęp w świetle ≥ s_min; strzemiona w obrysie',
    substitution: ll.issues.length ? ll.issues.join('; ') : `${ll.desc_h()}; ${ll.desc_v()} — rozmieszczenie wykonalne.`, kind: 'none', combination: combo || '', element_ref: 'rebar:links', status: ll.fits ? ST.OK : ST.FAIL }));
  return out;
}
function vrdc(b, d, As, H, hc, mats, ps) {
  const c = mats.concrete, k = Math.min(1 + Math.sqrt(200 / d), 2), rho = Math.min(As / (b * d), 0.02), CRdc = ps.v('CRdc_num') / c.gamma_c, k1 = ps.v('k1_shear');
  const scp = Math.min(-H / (b * hc), ps.v('sigma_cp_max') * c.fcd), vmin = ps.v('vmin_coef') * Math.pow(k, 1.5) * Math.sqrt(c.fck);
  const v1 = CRdc * k * Math.cbrt(100 * rho * c.fck) + k1 * scp, v2 = vmin + k1 * scp;
  const V = Math.max(Math.max(v1, v2) * b * d, 0);
  return [V, `k = 1 + √(200/${n(d, 0)}) = ${n(k, 3)}; ρ_l = ${n(rho, 4)}; σ_cp = ${n(scp, 3)} MPa; V_Rd,c = max[${n(CRdc, 4)}·${n(k, 3)}·(100·${n(rho, 4)}·${n(c.fck, 0)})^(1/3) + ${n(k1, 2)}·${n(scp, 3)}; ${n(vmin, 3)} + ${n(k1, 2)}·${n(scp, 3)}]·${n(b, 0)}·${n(d, 0)} = ${kN(V)}`];
}
function j3LinkChecks(sd, a_c, h_c, V, VRdc, vtxt, ml, ll, mats, ps, combo) {
  const out = [], k1 = ps.v('J3_k1'), k2 = ps.v('J3_k2'), fywd = mats.steel.link_fyd;
  if (a_c < 0.5 * h_c) {
    const AsL = ll.As_h + ll.As_i, req = k1 * ml.As;
    out.push(make({ id: 'J32_' + sd, group: 'Zbrojenie poprzeczne', title: 'Strzemiona poziome/ukośne przy a_c < 0,5·h_c', clause: 'EN 1992-1-1 zał. J.3(2), rys. J.6a', basis: BASIS.INFORMATIVE,
      formula: 'A_s,lnk ≥ k₁·A_s,main', symbols: { 'k₁': 'współczynnik (NDP, zalecane 0,25)', 'A_s,main': 'pole zbrojenia głównego (przyjęte)' },
      substitution: `a_c = ${mm(a_c)} < 0,5·${n(h_c, 0)} = ${mm(0.5 * h_c)}; A_s,lnk,req = ${n(k1, 2)}·${n(ml.As, 0)} = ${mm2(req)}; A_s,lnk = ${mm2(AsL)} (${ll.desc_h()}${ll.i_count ? '; ' + ll.i_count + ' pr. ukośne' : ''})`,
      E_d: req, R_d: AsL, kind: 'area', combination: combo, element_ref: 'rebar:links', E_label: 'A_s,lnk,req', R_label: 'A_s,lnk' }));
  } else out.push(make({ id: 'J32_' + sd, group: 'Zbrojenie poprzeczne', title: 'Strzemiona poziome/ukośne (J.3(2))', clause: 'EN 1992-1-1 zał. J.3(2)', basis: BASIS.INFORMATIVE, formula: 'warunek a_c < 0,5·h_c',
    substitution: `a_c = ${mm(a_c)} ≥ 0,5·h_c = ${mm(0.5 * h_c)} — wymaganie J.3(2) nie dotyczy.`, kind: 'area', combination: combo, element_ref: 'rebar:links', status: ST.NA }));
  if (a_c > 0.5 * h_c && V > VRdc) {
    const req = k2 * V / fywd;
    out.push(make({ id: 'J33_' + sd, group: 'Zbrojenie poprzeczne', title: 'Strzemiona pionowe przy a_c > 0,5·h_c i F_Ed > V_Rd,c', clause: 'EN 1992-1-1 zał. J.3(3), rys. J.6b; §6.2.2', basis: BASIS.INFORMATIVE,
      formula: 'A_s,lnk ≥ k₂·F_Ed / f_yd', symbols: { 'k₂': 'współczynnik (NDP, zalecane 0,5)' },
      substitution: `${vtxt}; F_Ed = ${kN(V)} > V_Rd,c → A_s,lnk,req = ${n(k2, 2)}·${kN(V)}·10³/${n(fywd, 1)} = ${mm2(req)}; A_s,lnk = ${mm2(ll.As_v)} (${ll.desc_v()})`,
      E_d: req, R_d: ll.As_v, kind: 'area', combination: combo, element_ref: 'rebar:links', E_label: 'A_s,lnk,req', R_label: 'A_s,lnk' }));
  } else {
    const why = a_c <= 0.5 * h_c ? `a_c = ${mm(a_c)} ≤ 0,5·h_c` : `F_Ed = ${kN(V)} ≤ V_Rd,c = ${kN(VRdc)}`;
    out.push(make({ id: 'J33_' + sd, group: 'Zbrojenie poprzeczne', title: 'Strzemiona pionowe (J.3(3))', clause: 'EN 1992-1-1 zał. J.3(3); §6.2.2', basis: BASIS.INFORMATIVE, formula: 'a_c > 0,5·h_c i F_Ed > V_Rd,c',
      substitution: `${why} — wymaganie J.3(3) nie dotyczy. (${vtxt})`, kind: 'area', combination: combo, element_ref: 'rebar:links', status: ST.NA }));
  }
  return out;
}
function minMaxChecks(b, d, hc, As, mats, ps, sd) {
  const c = mats.concrete, AsMin = Math.max(ps.v('As_min_coef') * c.fctm / mats.steel.fyk * b * d, ps.v('As_min_abs') * b * d), AsMax = ps.v('As_max_coef') * b * hc;
  return [
    make({ id: 'AS_MIN_' + sd, group: 'Konstrukcyjne', title: 'Minimalne zbrojenie główne (analogia do belek)', clause: 'EN 1992-1-1 §9.2.1.1(1), wzór (9.1N) — zastosowanie przez analogię', basis: BASIS.ENGINEERING,
      formula: 'A_s,min = max{0,26·f_ctm/f_yk·b·d; 0,0013·b·d}', symbols: { b: 'szerokość wspornika', d: 'wysokość użyteczna' },
      substitution: `A_s,min = max{0,26·${n(c.fctm, 1)}/${n(mats.steel.fyk, 0)}·${n(b, 0)}·${n(d, 0)}; 0,0013·${n(b, 0)}·${n(d, 0)}} = ${mm2(AsMin)}; A_s,prov = ${mm2(As)}`,
      E_d: AsMin, R_d: As, kind: 'area', element_ref: 'rebar:main', recommendation: true, E_label: 'A_s,min', R_label: 'A_s,prov' }),
    make({ id: 'AS_MAX_' + sd, group: 'Konstrukcyjne', title: 'Maksymalne zbrojenie główne (analogia do belek)', clause: 'EN 1992-1-1 §9.2.1.1(3) — zastosowanie przez analogię', basis: BASIS.ENGINEERING,
      formula: 'A_s ≤ A_s,max = 0,04·A_c', substitution: `A_s,max = 0,04·${n(b, 0)}·${n(hc, 0)} = ${mm2(AsMax)}; A_s = ${mm2(As)}`, E_d: As, R_d: AsMax, kind: 'area', element_ref: 'rebar:main', recommendation: true, E_label: 'A_s', R_label: 'A_s,max' }),
  ];
}
function designMainBars(gm, mi, ri, ps, asReqFn, anchorOkFn, log) {
  const li = ri.links; let best = null;
  const opts = [ri.main.anchor_load].concat(['loop', 'welded_bar', 'bend_down'].filter(a => a !== ri.main.anchor_load));
  ri.allowed_diameters.slice().sort((a, b) => a - b).forEach(phi => {
    [1, 2].forEach(layers => {
      const cv = coverRequirements(mi, ps, phi, li.h_phi, li.v_phi, li.v_count > 0, li.h_count > 0);
      const probe = mainLayout(gm.b, cv, phi, 2, layers, ri.main.layer_gap, mi.d_g, ps);
      let AsReq;
      try { AsReq = asReqFn(probe.c_t); } catch (e) { log.push(`φ${phi.toFixed(0)}/${layers} warstwy: model niewykonalny (${e.message}).`); return; }
      if (!isFinite(AsReq) || AsReq <= 0) return;
      const nMin = Math.max(2, Math.ceil(AsReq / (layers * barArea(phi)) - 1e-9));
      const ml0 = mainLayout(gm.b, cv, phi, nMin, layers, ri.main.layer_gap, mi.d_g, ps);
      if (!ml0.fits) { log.push(`φ${phi.toFixed(0)}: ${nMin}×${layers} — nie mieści się (${ml0.issues.join('; ')}).`); return; }
      let found = null, reason = '', nn = nMin;
      while (!found) {
        const ml = mainLayout(gm.b, cv, phi, nn, layers, ri.main.layer_gap, mi.d_g, ps);
        if (!ml.fits) break;
        for (const anc of opts) { if (anc === 'loop' && nn % 2) continue; const [ok, why] = anchorOkFn(ml, anc); if (ok) { found = [ml, anc]; break; } reason = why; }
        nn++;
      }
      if (!found) { log.push(`φ${phi.toFixed(0)}/${layers} warstwy: brak wykonalnego zakotwienia/gięcia przy n ≥ ${nMin} (${reason}).`); return; }
      const [ml, ch] = found;
      log.push(`φ${phi.toFixed(0)}: ${ml.n}×${layers} (A_s = ${ml.As.toFixed(0)} ≥ ${AsReq.toFixed(0)} mm²), kotwienie: ${ch} — OK.`);
      const key = [ml.As, layers, ml.n * layers];
      const better = !best || key[0] < best.layout.As || (key[0] === best.layout.As && (key[1] < best.layers || (key[1] === best.layers && key[2] < best.n * best.layers)));
      if (better) best = { phi, n: ml.n, layers, As_req: AsReq, layout: ml, anchor_load: ch };
    });
  });
  return best;
}
function designLinks(needH, needV, splitT, sinT, cosT, fywd, li, roomH, roomV, log) {
  const out = Object.assign({}, li, { auto: true });
  let bestV = [0, li.v_phi];
  if (needV > 0) {
    const c = []; LINK_DIAMETERS.forEach(phi => { const k = Math.ceil(needV / (2 * barArea(phi)) - 1e-9); if (k >= 1 && k <= roomV) c.push([k * 2 * barArea(phi), k, phi]); });
    if (c.length) { c.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]); bestV = [c[0][1], c[0][2]]; }
    else { log.push('Strzemiona pionowe: brak układu mieszczącego się w strefie — wymagana zmiana geometrii.'); bestV = [roomV, LINK_DIAMETERS[LINK_DIAMETERS.length - 1]]; }
  }
  [out.v_count, out.v_phi] = bestV;
  const Rv = 2 * out.v_count * barArea(out.v_phi) * fywd * cosT;
  const need = Math.max(needH, Math.max(splitT - Rv, 0) / (fywd * Math.max(sinT, 1e-6)));
  const c = []; LINK_DIAMETERS.forEach(phi => { const k = Math.max(li.min_constructive_h, Math.ceil(need / (2 * barArea(phi)) - 1e-9)); if (k <= roomH) c.push([k * 2 * barArea(phi), k, phi]); });
  if (c.length) { c.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]); out.h_count = c[0][1]; out.h_phi = c[0][2]; }
  else { log.push('Strzemiona poziome: brak układu mieszczącego się w strefie — wymagana zmiana geometrii.'); out.h_count = roomH; out.h_phi = LINK_DIAMETERS[LINK_DIAMETERS.length - 1]; }
  log.push(`Dobór strzemion: poziome ${out.h_count}×φ${out.h_phi.toFixed(0)} (wymagane A = ${need.toFixed(0)} mm²), pionowe ${out.v_count}×φ${out.v_phi.toFixed(0)} (wymagane A = ${needV.toFixed(0)} mm²).`);
  return out;
}
function barSchedule(gm, ml, lls, cv, mb, mand, grade) {
  const marks = [], h2 = gm.h_col / 2, cColIn = gm.column_cover + gm.column_phi_link + gm.column_phi_long, sides = Object.keys(gm.sides), double = sides.length === 2;
  const ends = {}; sides.forEach(sd => { ends[sd] = gm.sides[sd].l_c - cv.c_nom; });
  const phiML = mand.load || 0, phiMC = mand.column || 0;
  const frontLeg = mand.leg_front !== undefined ? mand.leg_front : Math.max(5 * ml.phi, 100), colLeg = mand.leg_col !== undefined ? mand.leg_col : Math.max(5 * ml.phi, 100);
  let horiz, extra = 0, shape;
  if (double) { horiz = ends.R + ends.L + gm.h_col; shape = 'pręt prosty ciągły'; }
  else { horiz = ends.R + gm.h_col - cColIn; shape = 'pręt'; if (mb.anchor_column === 'bend_down') { extra += colLeg + (Math.PI / 4 - 1) * (phiMC + ml.phi); shape += ' z odgięciem w słupie'; } }
  if (mb.anchor_load === 'bend_down') { extra += (frontLeg + (Math.PI / 4 - 1) * (phiML + ml.phi)) * (double ? 2 : 1); shape += ', odgięty w dół na końcu'; }
  const bm = (mark, description, shp, phi, count, length) => ({ mark, description, shape: shp, phi, count, length, grade, total_length: count * length, mass: count * length / 1000 * WS.barMass(phi) });
  if (mb.anchor_load === 'loop') marks.push(bm('1', 'Zbrojenie główne — pętle poziome (U)', 'pętla U ' + shape, ml.phi, Math.floor(ml.n / 2) * ml.layers, 2 * (horiz + extra) + Math.PI * (phiML + ml.phi) / 2 - (phiML + ml.phi)));
  else marks.push(bm('1', 'Zbrojenie główne (cięgno)', shape, ml.phi, ml.n * ml.layers, horiz + extra));
  let mk = 2;
  if (mb.anchor_load === 'welded_bar') { marks.push(bm(String(mk), 'Pręt poprzeczny przyspawany (zakotwienie)', 'pręt prosty', mb.welded_bar_phi || ml.phi, ml.layers * (double ? 2 : 1), gm.b - 2 * cv.c_nom)); mk++; }
  sides.forEach(sd => {
    const ll = lls[sd]; if (!ll) return; const sg = gm.sides[sd], tag = sd === 'R' ? 'P' : 'L';
    if (ll.h_depths.length) { const lens = ll.h_depths.map(dp => 2 * ((hLinkXiMax(sg, cv, dp) + gm.h_col - cColIn) + (gm.b - 2 * cv.c_nom)) + 2 * Math.max(10 * ll.h_phi, 70)); marks.push(bm(String(mk), `Strzemiona poziome zamknięte (${tag})`, 'strzemię zamknięte poziome', ll.h_phi, ll.h_depths.length, lens.reduce((a, b) => a + b, 0) / lens.length)); mk++; }
    if (ll.v_positions.length) { const lens = ll.v_positions.map(xi => 2 * ((sg.depth_at(xi) - 2 * cv.c_nom) + (gm.b - 2 * cv.c_nom)) + 2 * Math.max(10 * ll.v_phi, 70)); marks.push(bm(String(mk), `Strzemiona pionowe zamknięte (${tag})`, 'strzemię zamknięte pionowe', ll.v_phi, ll.v_positions.length, lens.reduce((a, b) => a + b, 0) / lens.length)); mk++; }
    if (ll.i_count) { marks.push(bm(String(mk), `Pręty ukośne przy narożu wklęsłym (${tag})`, 'pręt prosty ukośny (orientacyjnie)', ll.i_phi, 2 * ll.i_count, Math.SQRT2 * sg.h_c + 2 * 40 * ll.i_phi)); mk++; }
  });
  return marks;
}
Object.assign(WS, { LINK_DIAMETERS, coverRequirements, sMin, mainLayout, linksLayout, hLinkXiMax, linksCrossingStrut, coverChecks, spacingChecks, vrdc, j3LinkChecks, minMaxChecks, designMainBars, designLinks, barSchedule });
})(typeof window !== 'undefined' ? window : globalThis);
