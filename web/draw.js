/* KRÓTKI WSPORNIK ST – rysunki: scena prymitywów w układzie modelu (mm, oś y w górę) → SVG (ekran, raport) i DXF.
   Jedno źródło geometrii rysunku = wynik obliczeń (węzły, pręty, strefy, zbrojenie) — rysunek nie może pokazywać innego
   modelu niż obliczony (port kwst/visualization_engine.py). */
(function (G) {
'use strict';
const WS = G.WS;
const WD = G.WD = {};
const C = {
  conc: '#1b2230', concFill: '#eef1f5', colFill: '#e3e7ed', plate: '#5b6576', plateFill: '#b9c1cc', axis: '#8a94a6', dim: '#4a5466',
  load: '#c0262d', reac: '#6a3fb5', strut: '#1d5bb8', tie: '#b5651d', node: '#1b2230', nodeFill: '#ffffff', rebar: '#a8232a',
  rebarCol: '#7a8494', link: '#1d7f3c', cover: '#9aa3b0', handle: '#0e8fa8', angle: '#4a5466', etaLow: '#3a9d5d', etaMid: '#c9a227',
  etaHigh: '#e07b24', etaFail: '#c0262d', ink: '#1b2230', stale: '#7a8494',
};
WD.C = C;
const etaCol = e => e === null || e === undefined || !isFinite(e) ? (e === Infinity ? C.etaFail : C.strut) : e > 1 + 1e-9 ? C.etaFail : e > 0.85 ? C.etaHigh : e > 0.5 ? C.etaMid : C.etaLow;
WD.etaCol = etaCol;
const f1 = v => (v / 1e3).toFixed(1).replace('.', ',') + ' kN';
const P = (o) => o;
const lab = id => String(id).replace(/^([A-Z])([RL])$/, '$1_$2');
WD.lab = lab;

/* ------------------------------------------------------------------ prymitywy sceny */
function columnExtent(gm) {
  const top = Math.min(gm.above, Math.max(250, 0.5 * gm.h_max)), bot = -(gm.h_max + Math.min(gm.below, Math.max(300, 0.6 * gm.h_max)));
  return [top, bot];
}
function breakLine(x0, x1, y, amp) { const xm = (x0 + x1) / 2, w = x1 - x0; return [[x0 - 20, y], [xm - 0.06 * w, y], [xm - 0.02 * w, y + amp], [xm + 0.02 * w, y - amp], [xm + 0.06 * w, y], [x1 + 20, y]]; }
function geometry(pr, gm) {
  const h2 = gm.h_col / 2, [top, bot] = columnExtent(gm);
  pr.push(P({ t: 'poly', L: 'col', pts: [[-h2, top], [h2, top], [h2, bot], [-h2, bot]], c: C.conc, w: 1.2, fill: C.colFill, go: 'col', tip: 'Słup – kliknij, aby edytować wymiary słupa' }));
  const amp = 0.06 * gm.h_col;
  if (gm.above > top + 1e-6) pr.push(P({ t: 'pline', L: 'col', pts: breakLine(-h2, h2, top, amp), c: C.conc, w: 1 }));
  if (-(gm.h_max + gm.below) < bot - 1e-6) pr.push(P({ t: 'pline', L: 'col', pts: breakLine(-h2, h2, bot, amp), c: C.conc, w: 1 }));
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    pr.push(P({ t: 'poly', L: 'corbel', pts: sg.outline(), c: C.conc, w: 1.6, fill: C.concFill, go: 'geo', tip: `Wspornik ${WS.SIDE_NAME[sd]} – kliknij, aby edytować geometrię` }));
    const p = sg.plate, xs = [sg.g(p.xi_inner, 0)[0], sg.g(p.xi_outer, 0)[0]].sort((a, b) => a - b), t = p.kind !== 'direct' ? Math.max(p.thickness, 6) : 4;
    pr.push(P({ t: 'poly', L: 'plate', pts: [[xs[0], 0], [xs[1], 0], [xs[1], t], [xs[0], t]], c: C.plate, w: 1, fill: C.plateFill, go: 'plate', tip: 'Płyta oporowa / łożysko – kliknij, aby edytować' }));
  });
  pr.push(P({ t: 'line', L: 'axes', pts: [[0, top + 30], [0, bot - 30]], c: C.axis, w: 0.8, dash: '10 4 2 4' }));
  const xr = h2 + Math.max(...Object.values(gm.sides).map(s => s.l_c)) + 60, xl = gm.sides.L ? -xr : -h2 - 60;
  pr.push(P({ t: 'line', L: 'axes', pts: [[xl, 0], [xr, 0]], c: C.axis, w: 0.5, dash: '10 4 2 4', nob: true }));
}
function arrow(pr, L, tip, vec, col, text, ref, w, go) {
  const tail = [tip[0] - vec[0], tip[1] - vec[1]];
  pr.push(P({ t: 'arrow', L, pts: [tail, tip], c: col, w: w || 2, ref, go }));
  if (text && L === 'reactions') {      // reakcje: opis przy początku strzałki (nie nachodzi na opisy węzła)
    if (Math.abs(vec[0]) < 1e-9) pr.push(P({ t: 'text', L, pts: [tail], txt: text, c: col, fs: 11, a: 'start', dx: 7, dy: vec[1] > 0 ? 12 : -4, ref, go, w: 600, halo: true }));
    else pr.push(P({ t: 'text', L, pts: [tail], txt: text, c: col, fs: 11, a: vec[0] > 0 ? 'end' : 'start', dx: vec[0] > 0 ? -5 : 5, dy: 4, ref, go, w: 600, halo: true }));
    return;
  }
  if (text) {
    const mid = [(tail[0] + tip[0]) / 2, (tail[1] + tip[1]) / 2];
    if (Math.abs(vec[0]) < 1e-9) pr.push(P({ t: 'text', L, pts: [mid], txt: text, c: col, fs: 11, a: 'start', dx: 8, ref, go, w: 600 }));
    else pr.push(P({ t: 'text', L, pts: [mid], txt: text, c: col, fs: 11, a: 'middle', dy: -8, ref, go, w: 600 }));
  }
}
function loads(pr, gm, sr) {
  Object.entries(sr.sides).forEach(([sd, sm]) => {
    const sg = gm.sides[sd], p = sm.params, xl = sg.g(sg.a_c + (p.V ? p.M / p.V : 0), 0)[0], top = sg.plate.kind !== 'direct' ? sg.plate.thickness : 4, L = Math.max(120, 0.35 * sg.h_c);
    arrow(pr, 'loads', [xl, top], [0, -L], C.load, `V_Ed = ${f1(p.V)}`, 'load:V' + sd, 2.4, 'loads');
    if (Math.abs(p.H_raw) > 1e-6) {
      const dx = sg.s * (p.H_raw > 0 ? 1 : -1), tail = [xl, top + 12], tip = [xl + dx * L * 0.8, top + 12];
      pr.push(P({ t: 'arrow', L: 'loads', pts: [tail, tip], c: C.load, w: 2, ref: 'load:H' + sd, go: 'loads' }));
      pr.push(P({ t: 'text', L: 'loads', pts: [tip], txt: `H_Ed = ${f1(p.H_raw)}`, c: C.load, fs: 11, a: dx > 0 ? 'start' : 'end', dx: dx * 6, dy: -6, ref: 'load:H' + sd, go: 'loads', w: 600 }));
    }
  });
}
function loadsInput(pr, gm, combos) {
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    const x = sg.g(sg.a_c, 0)[0], L = Math.max(120, 0.35 * sg.h_c), top = sg.plate.kind !== 'direct' ? sg.plate.thickness : 4;
    let V = null; (combos || []).forEach(c => { if (c.is_uls && c.sides[sd]) V = Math.max(V || 0, c.sides[sd].V); });
    arrow(pr, 'loads', [x, top], [0, -L], C.load, V !== null ? `V_Ed,max = ${f1(V)}` : 'V', 'load:V' + sd, 2.4, 'loads');
  });
}
function etaByRef(R, combo) {
  const m = {};
  const G = new Set(['Krzyżulce', 'Węzły', 'Docisk', 'Cięgna', 'Rozłupywanie']);   // wytężenie elementów modelu (nie: zakotwienia, gięcie, wymagania konstrukcyjne)
  R.checks.forEach(c => { if (G.has(c.group) && c.element_ref && c.eta !== null && isFinite(c.eta) && ['', combo, 'obwiednia SGN'].includes(c.combination)) m[c.element_ref] = Math.max(m[c.element_ref] || 0, c.eta); });
  return m;
}
function stm(pr, gm, sr, R, o) {
  const em = etaByRef(R, sr.combination), crit = WS.critical(R), cref = crit ? crit.element_ref : '';
  const node = id => sr.truss.nodes.find(q => q.id === id);
  const stress = o.stress !== false;
  sr.struts.forEach(s => {
    const ref = 'member:' + s.id, eta = em[ref], a = node(s.n1), b = node(s.n2);
    pr.push(P({ t: 'poly', L: 'zones', pts: s.polygon, c: C.strut, w: 0.8, dash: '5 3', fill: stress ? etaCol(eta) : C.strut, alpha: stress ? 0.32 : 0.12, ref }));
    pr.push(P({ t: 'line', L: 'struts', pts: [[a.x, a.y], [b.x, b.y]], c: C.strut, w: 3.2, dash: '9 5', ref }));
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    if (o.forces !== false) pr.push(P({ t: 'text', L: 'forces', pts: [[mx, my]], txt: `${lab(s.id)}: C = ${f1(Math.abs(s.force))}`, c: C.strut, fs: 11, a: 'middle', dy: 16, ref, w: 600, halo: true }));
    if (stress && eta !== undefined) pr.push(P({ t: 'text', L: 'eta', pts: [[mx, my]], txt: `η = ${eta.toFixed(2).replace('.', ',')}`, c: etaCol(eta), fs: 11, a: 'middle', dy: -8, ref, w: 700, halo: true }));
    const ang0 = b.x < a.x ? 0 : 180 - s.theta_deg, Rr = 0.32 * s.length;
    pr.push(P({ t: 'arc', L: 'angles', ctr: [b.x, b.y], r: Rr, a0: ang0, da: s.theta_deg, c: C.angle, w: 1, ref }));
    const am = (ang0 + s.theta_deg / 2) * Math.PI / 180;
    pr.push(P({ t: 'text', L: 'angles', pts: [[b.x + Rr * 1.12 * Math.cos(am), b.y + Rr * 1.12 * Math.sin(am)]], txt: `θ = ${s.theta_deg.toFixed(1).replace('.', ',')}°`, c: C.angle, fs: 10, a: 'middle', ref, halo: true }));
    if (o.widths !== false) {
      const Ls = Math.hypot(b.x - a.x, b.y - a.y) || 1; let nx = (b.y - a.y) / Ls, ny = -(b.x - a.x) / Ls; if (nx < 0) { nx = -nx; ny = -ny; }
      [[0.16, s.w1], [0.84, s.w2]].forEach(([t, w]) => { const px = a.x + (b.x - a.x) * t, py = a.y + (b.y - a.y) * t; pr.push(P({ t: 'text', L: 'zones', pts: [[px + nx * (w / 2 + 18), py + ny * (w / 2 + 18)]], txt: `w = ${w.toFixed(0)}`, c: C.strut, fs: 9.5, a: 'start', ref, halo: true })); });
    }
    if (s.shape === 'butelkowy') pr.push(P({ t: 'text', L: 'zones', pts: [[mx, my]], txt: 'krzyżulec butelkowy', c: C.strut, fs: 9.5, a: 'middle', dy: 30, ref, it: true, halo: true }));
  });
  sr.ties.forEach(t => {
    const ref = 'member:' + t.id, eta = em[ref], a = node(t.n1), b = node(t.n2);
    pr.push(P({ t: 'poly', L: 'zones', pts: t.polygon, c: C.tie, w: 0.6, dash: '5 3', fill: C.tie, alpha: 0.1, ref }));
    pr.push(P({ t: 'line', L: 'ties', pts: [[a.x, a.y], [b.x, b.y]], c: stress && eta !== undefined ? etaCol(eta) : C.tie, w: 3.6, ref }));
    if (o.forces !== false) pr.push(P({ t: 'text', L: 'forces', pts: [[(a.x + b.x) / 2, a.y]], txt: `${lab(t.id)}: T = ${f1(t.force)}` + (stress && eta !== undefined ? `  (η = ${eta.toFixed(2).replace('.', ',')})` : ''), c: C.tie, fs: 11, a: 'middle', dy: -10, ref, w: 600, halo: true }));
  });
  const drawn = new Set(sr.struts.map(x => x.id).concat(sr.ties.map(x => x.id)));
  sr.truss.members.forEach(m => {
    if (drawn.has(m.id)) return;
    const ref = 'member:' + m.id, a = node(m.n1), b = node(m.n2), N = sr.solution.forces[m.id] || 0, isS = m.kind === 'strut', eta = em[ref];
    pr.push(P({ t: 'line', L: isS ? 'struts' : 'ties', pts: [[a.x, a.y], [b.x, b.y]], c: stress && eta !== undefined ? etaCol(eta) : isS ? C.strut : C.tie, w: 3.4, dash: isS ? '9 5' : null, ref }));
    pr.push(P({ t: 'text', L: 'forces', pts: [[(a.x + b.x) / 2, (a.y + b.y) / 2]], txt: `${m.id}: ${N < 0 ? 'C' : 'T'} = ${f1(Math.abs(N))}`, c: isS ? C.strut : C.tie, fs: 11, a: 'middle', dy: 16, ref, w: 600, halo: true }));
  });
  Object.entries(sr.nodes).forEach(([nid, nz]) => {
    const ref = 'node:' + nid, eta = em[ref];
    if (nz.polygon && nz.polygon.length) pr.push(P({ t: 'poly', L: 'zones', pts: nz.polygon, c: C.node, w: 1, dash: '4 3', fill: stress ? etaCol(eta) : C.node, alpha: stress ? 0.45 : 0.08, ref }));
  });
  sr.truss.nodes.forEach(q => {
    const nz = sr.nodes[q.id], ref = 'node:' + q.id, eta = em[ref];
    pr.push(P({ t: 'circle', L: 'nodes', ctr: [q.x, q.y], rp: 6.5, c: C.node, w: 1.6, fill: C.nodeFill, ref }));
    pr.push(P({ t: 'text', L: 'nodes', pts: [[q.x, q.y]], txt: nz && ['CCC', 'CCT', 'CTT'].includes(nz.type) ? `${lab(q.id)} (${nz.type})` : lab(q.id), c: C.node, fs: 11, a: 'start', dx: 9, dy: 15, ref, w: 700, halo: true }));
    if (stress && eta !== undefined && nz) pr.push(P({ t: 'text', L: 'eta', pts: [[q.x, q.y]], txt: `η = ${eta.toFixed(2).replace('.', ',')}`, c: etaCol(eta), fs: 10.5, a: 'start', dx: 9, dy: -9, ref, w: 700, halo: true }));
  });
  if (o.reactions !== false) Object.entries(sr.solution.reactions).forEach(([nid, [rx, ry]]) => {
    const q = node(nid), Lr = 100;
    if (Math.abs(rx) > 1) arrow(pr, 'reactions', [q.x, q.y - (nid === 'C' ? 30 : 0)], [Math.sign(rx) * Lr, 0], C.reac, `R_x = ${f1(Math.abs(rx))}`, 'node:' + nid, 1.6);
    if (Math.abs(ry) > 1) arrow(pr, 'reactions', [q.x, q.y], [0, Math.sign(ry) * Lr], C.reac, `R_y = ${f1(Math.abs(ry))}`, 'node:' + nid, 1.6);
  });
  if (cref && o.crit !== false) {
    const nz = sr.nodes[cref.replace('node:', '')];
    if (cref.startsWith('node:') && nz) pr.push(P({ t: 'circle', L: 'crit', ctr: nz.center, rp: 17, c: C.etaFail, w: 3, ref: cref }));
    const m = sr.struts.concat(sr.ties).find(x => 'member:' + x.id === cref);
    if (m) { const a = node(m.n1), b = node(m.n2); pr.push(P({ t: 'line', L: 'crit', pts: [[a.x, a.y], [b.x, b.y]], c: C.etaFail, w: 10, alpha: 0.35, ref: cref })); }
  }
}
function rebar(pr, gm, R) {
  const ml = R.main, cv = R.cover, mb = R.main_input, h2 = gm.h_col / 2, dbl = Object.keys(gm.sides).length === 2, colIn = gm.column_cover + gm.column_phi_link + gm.column_phi_long, mand = R.mandrels || {};
  const [ctop, cbot] = columnExtent(gm);
  [-h2 + gm.column_cover + gm.column_phi_link + gm.column_phi_long / 2, h2 - gm.column_cover - gm.column_phi_link - gm.column_phi_long / 2].forEach(x => pr.push(P({ t: 'line', L: 'rebar', pts: [[x, ctop], [x, cbot]], c: C.rebarCol, w: 1.3, dash: '8 4', go: 'col' })));
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    const c = cv.c_nom, loc = [[0, -c], [sg.l_c - c, -c], [sg.l_c - c, -sg.h_e + c]];
    if (sg.x_slope > 0) loc.push([sg.x_slope, -sg.h_c + c]); loc.push([0, -sg.h_c + c]);
    pr.push(P({ t: 'pline', L: 'cover', pts: loc.map(q => sg.g(q[0], q[1])), c: C.cover, w: 0.8, dash: '3 3', go: 'mat', tip: `otulina c_nom = ${c} mm` }));
  });
  const legF = mand.leg_front !== undefined ? mand.leg_front : 5 * ml.phi, legC = mand.leg_col !== undefined ? mand.leg_col : 5 * ml.phi;
  const rL = ((mand.load || 4 * ml.phi) + ml.phi) / 2, rC = ((mand.column || 4 * ml.phi) + ml.phi) / 2;
  ml.layer_depths.forEach(depth => {
    const y = -depth; let pts;
    const bendEnd = (x, sgn, leg, r) => { const k = 0.2929 * r; return [[x - sgn * r, y], [x - sgn * k, y - k], [x, y - r], [x, y - Math.max(leg, r + 1)]]; };
    if (dbl) {
      const xL = gm.sides.L.g(gm.sides.L.l_c - cv.c_nom - ml.phi / 2, 0)[0], xR = gm.sides.R.g(gm.sides.R.l_c - cv.c_nom - ml.phi / 2, 0)[0];
      pts = mb.anchor_load === 'bend_down' ? bendEnd(xL, -1, legF, rL).reverse().concat(bendEnd(xR, 1, legF, rL)) : [[xL, y], [xR, y]];
    } else {
      const sg = gm.sides.R, xe = sg.g(sg.l_c - cv.c_nom - ml.phi / 2, 0)[0], xc = -h2 + colIn + ml.phi / 2;
      const left = mb.anchor_column === 'bend_down' ? bendEnd(xc, -1, legC, rC).reverse() : [[xc, y]];
      const right = mb.anchor_load === 'bend_down' ? bendEnd(xe, 1, legF, rL) : [[xe, y]];
      pts = left.concat(right);
    }
    pr.push(P({ t: 'pline', L: 'rebar', pts, c: C.rebar, w: 3, go: 'main', ref: 'rebar:main', tip: `zbrojenie główne ${ml.desc()}` }));
    Object.values(gm.sides).forEach(sg => {
      const xe = sg.g(sg.l_c - cv.c_nom - ml.phi / 2, 0)[0];
      if (mb.anchor_load === 'welded_bar') pr.push(P({ t: 'circle', L: 'rebar', ctr: [sg.g(sg.l_c - cv.c_nom - ml.phi, 0)[0], y - ml.phi], r: (mb.welded_bar_phi || ml.phi) / 2, c: C.rebar, w: 1.2, fill: C.rebar, go: 'main' }));
      if (mb.anchor_load === 'loop') pr.push(P({ t: 'arc', L: 'rebar', ctr: [xe - sg.s * 30, y], r: 30, a0: sg.s > 0 ? -60 : 120, da: 120, c: C.rebar, w: 1.6, go: 'main' }));
    });
  });
  pr.push(P({ t: 'text', L: 'marks', pts: [[gm.sides.R.g(gm.sides.R.l_c * 0.45, 0)[0], -ml.layer_depths[0]]], txt: `(1) ${ml.desc()}${mb.anchor_load === 'loop' ? ' – pętle' : ''}`, c: C.rebar, fs: 11, a: 'middle', dy: -8, go: 'main', w: 700, halo: true }));
  let mk = 2 + (mb.anchor_load === 'welded_bar' ? 1 : 0);
  Object.entries(R.links || {}).forEach(([sd, ll]) => {
    const sg = gm.sides[sd];
    ll.h_depths.forEach(dpt => {
      const xm = WS.hLinkXiMax(sg, cv, dpt), x0 = dbl ? 0 : -sg.s * (h2 - colIn), x1 = sg.g(xm, 0)[0];
      pr.push(P({ t: 'line', L: 'links', pts: [[x0, -dpt], [x1, -dpt]], c: C.link, w: 1.6, go: 'links', tip: ll.desc_h() }));
    });
    if (ll.h_depths.length) { pr.push(P({ t: 'text', L: 'marks', pts: [[sg.g(sg.l_c * 0.55, 0)[0], -ll.h_depths[ll.h_depths.length - 1]]], txt: `(${mk}) ${ll.h_depths.length}×φ${ll.h_phi} poz.`, c: C.link, fs: 10.5, a: 'middle', dy: 14, go: 'links', w: 600, halo: true })); mk++; }
    ll.v_positions.forEach(xi => { const h = sg.depth_at(xi), x = sg.g(xi, 0)[0]; pr.push(P({ t: 'line', L: 'links', pts: [[x, -cv.c_nom], [x, -h + cv.c_nom]], c: C.link, w: 1.6, go: 'links', tip: ll.desc_v() })); });
    if (ll.v_positions.length) { pr.push(P({ t: 'text', L: 'marks', pts: [[sg.g(ll.v_positions[0], 0)[0], -sg.h_c]], txt: `(${mk}) ${ll.v_positions.length}×φ${ll.v_phi} pion.`, c: C.link, fs: 10.5, a: 'middle', dy: 26, go: 'links', w: 600 })); mk++; }
    for (let k = 0; k < ll.i_count; k++) { const off = 40 + 45 * k; pr.push(P({ t: 'line', L: 'links', pts: [sg.g(-off * 1.2, -sg.h_c - 120 + off), sg.g(off + 160, -sg.h_c + off + 160)], c: C.link, w: 1.4, go: 'links' })); }
  });
}
function dims(pr, gm) {
  const h2 = gm.h_col / 2;
  pr.push(P({ t: 'dim', L: 'dims', pts: [[-h2, gm.above > 0 ? Math.min(gm.above, Math.max(250, 0.5 * gm.h_max)) : 0], [h2, gm.above > 0 ? Math.min(gm.above, Math.max(250, 0.5 * gm.h_max)) : 0]], off: 40, txt: `h_col = ${gm.h_col.toFixed(0)}`, go: 'col' }));
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    const s = sg.s, face = sg.x_face, end = sg.g(sg.l_c, 0)[0], off = 70 + 0.08 * sg.h_c, pl = sg.plate, x0 = sg.g(pl.xi_inner, 0)[0], x1 = sg.g(pl.xi_outer, 0)[0], t = pl.kind !== 'direct' ? Math.max(pl.thickness, 6) : 4;
    pr.push(P({ t: 'dim', L: 'dims', pts: [[face, 0], [end, 0]], off: s * (off + 55), txt: `l_c = ${sg.l_c.toFixed(0)}`, go: 'geo' }));
    pr.push(P({ t: 'dim', L: 'dims', pts: [[face, 0], [sg.g(sg.a_c, 0)[0], 0]], off: s * off, txt: `a_c = ${sg.a_c.toFixed(0)}`, go: 'geo' }));
    pr.push(P({ t: 'dim', L: 'dims', pts: [[end, 0], [end, -sg.h_e]], off: s * 55, txt: `h_e = ${sg.h_e.toFixed(0)}`, go: 'geo' }));
    if (gm.sides.L) pr.push(P({ t: 'dim', L: 'dims', pts: [[face, 0], [face, -sg.h_c]], off: s * 40, txt: `h_c = ${sg.h_c.toFixed(0)}`, go: 'geo' }));
    else pr.push(P({ t: 'dim', L: 'dims', pts: [[-h2, 0], [-h2, -sg.h_c]], off: -45, txt: `h_c = ${sg.h_c.toFixed(0)}`, go: 'geo' }));
    if (sg.x_slope > 1e-6 && sg.x_slope < sg.l_c - 1e-6) pr.push(P({ t: 'dim', L: 'dims', pts: [[face, -sg.h_c], [sg.g(sg.x_slope, 0)[0], -sg.h_c]], off: -s * 40, txt: `x_s = ${sg.x_slope.toFixed(0)}`, go: 'geo' }));
    pr.push(P({ t: 'dim', L: 'dims', pts: [[Math.min(x0, x1), t], [Math.max(x0, x1), t]], off: 26, txt: `a_p = ${pl.length.toFixed(0)}`, go: 'plate' }));
  });
}
function handles(pr, gm, R, combo) {
  Object.entries(gm.sides).forEach(([sd, sg]) => {
    pr.push(P({ t: 'handle', L: 'handles', ctr: sg.g(sg.a_c, 0), h: 'a_c:' + sd, tip: 'a_c – przeciągnij poziomo (położenie obciążenia)' }));
    pr.push(P({ t: 'handle', L: 'handles', ctr: sg.g(sg.l_c, -sg.h_e / 2), h: 'l_c:' + sd, tip: 'l_c – przeciągnij poziomo (wysięg wspornika)' }));
    pr.push(P({ t: 'handle', L: 'handles', ctr: sg.g(sg.l_c, -sg.h_e), h: 'h_e:' + sd, tip: 'h_e – przeciągnij pionowo (wysokość na końcu)' }));
    pr.push(P({ t: 'handle', L: 'handles', ctr: sg.g(Math.max(sg.x_slope, 0) * 0.5, -sg.h_c), h: 'h_c:' + sd, tip: 'h_c – przeciągnij pionowo (wysokość przy licu)' }));
  });
}
/* sceny gotowe */
WD.sceneScheme = function (v, R, o) {
  o = o || {}; const pr = [];
  let gm = R && R.geometry; if (!gm) { try { gm = WS.buildGeometry(v.geometry); } catch (e) { return { pr: [], err: e.message }; } }
  geometry(pr, gm);
  const sr = R && R.stm && R.governing ? R.stm[o.combo && R.stm[o.combo] ? o.combo : R.governing] : null;
  const ok = sr && R.geometry && !WS.errorsOf(R).length;
  if (ok && o.rebar && R.main && R.cover) rebar(pr, gm, R);
  if (ok && sr.sides && Object.keys(sr.sides).length) loads(pr, gm, sr); else loadsInput(pr, gm, R && R.combinations);
  if (ok && o.stm) stm(pr, gm, sr, R, Object.assign({ stress: !!o.stress, widths: false, reactions: false, crit: false }, o.stmOpts || {}));
  if (o.dims !== false) dims(pr, gm);
  if (o.handles) handles(pr, gm, R, sr && sr.combination);
  return { pr, gm, sr };
};
WD.sceneStm = function (v, R, combo, o) {
  o = o || {}; const pr = [], gm = R.geometry; if (!gm) return { pr };
  const sr = R.stm[combo] || R.stm[R.governing];
  if (v.stm.mode !== 'manual') geometry(pr, gm);
  if (o.rebar && R.main && R.cover) rebar(pr, gm, R);
  if (sr) { if (sr.sides && Object.keys(sr.sides).length) loads(pr, gm, sr); stm(pr, gm, sr, R, o); }
  if (o.dims && v.stm.mode !== 'manual') dims(pr, gm);
  return { pr, gm, sr };
};
WD.sceneRebar = function (v, R, o) {
  o = o || {}; const pr = [], gm = R.geometry;
  geometry(pr, gm); if (R.main && R.cover) rebar(pr, gm, R); if (o.dims !== false) dims(pr, gm);
  return { pr, gm };
};
/* przekrój poprzeczny A–A przy licu słupa (płaszczyzna prostopadła do osi wspornika) */
WD.sceneSection = function (v, R, sd) {
  const pr = [], gm = R.geometry, sg = gm.sides[sd || 'R'], ml = R.main, cv = R.cover, ll = (R.links || {})[sd || 'R'], b = gm.b, hc = sg.h_c, z0 = -b / 2;
  pr.push(P({ t: 'poly', L: 'corbel', pts: [[z0, 0], [z0 + b, 0], [z0 + b, -hc], [z0, -hc]], c: C.conc, w: 1.6, fill: C.concFill, go: 'geo' }));
  const c = cv.c_nom;
  pr.push(P({ t: 'poly', L: 'cover', pts: [[z0 + c, -c], [z0 + b - c, -c], [z0 + b - c, -hc + c], [z0 + c, -hc + c]], c: C.cover, w: 0.8, dash: '3 3', go: 'mat' }));
  if (ll) {
    const zl = b / 2 - c - ll.h_phi / 2;
    ll.h_depths.forEach(d => { [-zl, zl].forEach(z => pr.push(P({ t: 'circle', L: 'links', ctr: [z, -d], r: ll.h_phi / 2, c: C.link, w: 1, fill: C.link, go: 'links' }))); pr.push(P({ t: 'line', L: 'links', pts: [[-zl, -d], [zl, -d]], c: C.link, w: 0.8, dash: '2 3', go: 'links' })); });
    if (ll.v_positions.length) { const r = ll.v_phi / 2; pr.push(P({ t: 'poly', L: 'links', pts: [[z0 + c + r, -c - r], [z0 + b - c - r, -c - r], [z0 + b - c - r, -hc + c + r], [z0 + c + r, -hc + c + r]], c: C.link, w: 1.6, go: 'links' })); }
  }
  ml.layer_depths.forEach(d => ml.z_positions.forEach(z => pr.push(P({ t: 'circle', L: 'rebar', ctr: [z, -d], r: ml.phi / 2, c: C.rebar, w: 1, fill: C.rebar, go: 'main' }))));
  pr.push(P({ t: 'dim', L: 'dims', pts: [[z0, 0], [z0 + b, 0]], off: 40, txt: `b = ${b.toFixed(0)}`, go: 'geo' }));
  pr.push(P({ t: 'dim', L: 'dims', pts: [[z0 + b, 0], [z0 + b, -hc]], off: -45, txt: `h_c = ${hc.toFixed(0)}`, go: 'geo' }));
  pr.push(P({ t: 'dim', L: 'dims', pts: [[z0 - 1, 0], [z0 - 1, -ml.c_t]], off: 30, txt: `c_t = ${ml.c_t.toFixed(0)}`, go: 'main' }));
  pr.push(P({ t: 'text', L: 'marks', pts: [[0, -ml.layer_depths[ml.layer_depths.length - 1]]], txt: `${ml.desc()}`, c: C.rebar, fs: 11, a: 'middle', dy: 22, w: 700, halo: true, go: 'main' }));
  return { pr, gm };
};

/* ------------------------------------------------------------------ SVG */
const escX = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
const symX = s => escX(s).replace(/_\{([^}]*)\}/g, '<tspan baseline-shift="sub" font-size="75%">$1</tspan>').replace(/_([0-9A-Za-ząćęłńóśźżθ,]+)/g, '<tspan baseline-shift="sub" font-size="75%">$1</tspan>');
function bounds(pr, extra) {
  const bb = [Infinity, Infinity, -Infinity, -Infinity], add = (x, y) => { bb[0] = Math.min(bb[0], x); bb[1] = Math.min(bb[1], y); bb[2] = Math.max(bb[2], x); bb[3] = Math.max(bb[3], y); };
  pr.forEach(p => {
    if (p.nob) return;
    if (p.t === 'dim') { const [a, b] = p.pts, L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, nx = -(b[1] - a[1]) / L, ny = (b[0] - a[0]) / L; [a, b].forEach(q => { add(q[0], q[1]); add(q[0] + nx * p.off * 1.25, q[1] + ny * p.off * 1.25); }); return; }
    if (p.ctr) { const r = p.r || 0; add(p.ctr[0] - r, p.ctr[1] - r); add(p.ctr[0] + r, p.ctr[1] + r); return; }
    (p.pts || []).forEach(q => add(q[0], q[1]));
  });
  return bb;
}
WD.svg = function (scene, W, o) {
  o = o || {};
  const pr = scene.pr; if (!pr.length) return '';
  let bb = bounds(pr), m = o.margin || 46, Hmax = o.H || 640;
  const bw = Math.max(bb[2] - bb[0], 1), bh = Math.max(bb[3] - bb[1], 1);
  let k = Math.min((W - 2 * m) / bw, (Hmax - 2 * m) / bh), H = Math.round(bh * k + 2 * m), W2 = o.fit ? Math.round(bw * k + 2 * m) : W;
  let ox = (W2 - bw * k) / 2;
  if (o.view) ({ k, bb, m, ox, W: W2, H } = o.view);     // stała skala (np. podczas przeciągania uchwytu)
  const X = x => +(ox + (x - bb[0]) * k).toFixed(1), Y = y => +(m + (bb[3] - y) * k).toFixed(1);
  const attrs = p => `${p.ref ? ` data-ref="${escX(p.ref)}"` : ''}${p.go ? ` data-go="${escX(p.go)}"` : ''}${p.ref || p.go ? ' class="hot"' : ''}`;
  const title = p => p.tip ? `<title>${escX(p.tip)}</title>` : '';
  const st = p => `stroke="${p.c || C.ink}" stroke-width="${p.w || 1}"${p.dash ? ` stroke-dasharray="${p.dash}"` : ''}`;
  let s = `<svg xmlns="http://www.w3.org/2000/svg" class="${o.cls || 'wsvg'}" width="${W2}" height="${H}" viewBox="0 0 ${W2} ${H}" font-family="Segoe UI, Arial, sans-serif">`;
  const texts = [], hdls = [];
  pr.forEach(p => {
    const a = attrs(p);
    if (p.t === 'poly' || p.t === 'pline') {
      const pts = p.pts.map(q => `${X(q[0])},${Y(q[1])}`).join(' ');
      const fill = p.t === 'poly' && p.fill ? `fill="${p.fill}"${p.alpha !== undefined ? ` fill-opacity="${p.alpha}"` : ''}` : 'fill="none"';
      s += `<${p.t === 'poly' ? 'polygon' : 'polyline'} points="${pts}" ${fill} ${st(p)} stroke-linejoin="round"${a}>${title(p)}</${p.t === 'poly' ? 'polygon' : 'polyline'}>`;
    } else if (p.t === 'line') {
      const [q1, q2] = p.pts; s += `<line x1="${X(q1[0])}" y1="${Y(q1[1])}" x2="${X(q2[0])}" y2="${Y(q2[1])}" ${st(p)}${p.alpha !== undefined ? ` stroke-opacity="${p.alpha}"` : ''} stroke-linecap="round"${a}>${title(p)}</line>`;
    } else if (p.t === 'circle') {
      const r = p.rp || Math.max(p.r * k, 1.6);
      s += `<circle cx="${X(p.ctr[0])}" cy="${Y(p.ctr[1])}" r="${r.toFixed(1)}" fill="${p.fill || 'none'}" ${st(p)}${a}>${title(p)}</circle>`;
    } else if (p.t === 'handle') {
      hdls.push(p);
    } else if (p.t === 'handle_') {
      s += `<circle class="hdl" data-h="${p.h}" cx="${X(p.ctr[0])}" cy="${Y(p.ctr[1])}" r="6.5" fill="${C.handle}" fill-opacity="0.85" stroke="#ffffff" stroke-width="1.5"><title>${escX(p.tip || '')}</title></circle>`;
    } else if (p.t === 'arc') {
      const r = p.r * k, a0 = p.a0 * Math.PI / 180, a1 = (p.a0 + p.da) * Math.PI / 180, cx = X(p.ctr[0]), cy = Y(p.ctr[1]);
      const x0 = cx + r * Math.cos(a0), y0 = cy - r * Math.sin(a0), x1 = cx + r * Math.cos(a1), y1 = cy - r * Math.sin(a1);
      s += `<path d="M${x0.toFixed(1)},${y0.toFixed(1)} A${r.toFixed(1)},${r.toFixed(1)} 0 ${Math.abs(p.da) > 180 ? 1 : 0} ${p.da > 0 ? 0 : 1} ${x1.toFixed(1)},${y1.toFixed(1)}" fill="none" ${st(p)}${a}/>`;
    } else if (p.t === 'arrow') {
      const [t0, t1] = p.pts, x0 = X(t0[0]), y0 = Y(t0[1]), x1 = X(t1[0]), y1 = Y(t1[1]), L = Math.hypot(x1 - x0, y1 - y0) || 1, ux = (x1 - x0) / L, uy = (y1 - y0) / L, hs = 10;
      s += `<g${a}>${title(p)}<line x1="${x0}" y1="${y0}" x2="${(x1 - ux * hs * 0.8).toFixed(1)}" y2="${(y1 - uy * hs * 0.8).toFixed(1)}" stroke="${p.c}" stroke-width="${p.w || 2}"/><polygon points="${x1},${y1} ${(x1 - ux * hs - uy * hs * 0.42).toFixed(1)},${(y1 - uy * hs + ux * hs * 0.42).toFixed(1)} ${(x1 - ux * hs + uy * hs * 0.42).toFixed(1)},${(y1 - uy * hs - ux * hs * 0.42).toFixed(1)}" fill="${p.c}"/></g>`;
    } else if (p.t === 'dim') {
      const [a1, a2] = p.pts, L = Math.hypot(a2[0] - a1[0], a2[1] - a1[1]) || 1, nx = -(a2[1] - a1[1]) / L, ny = (a2[0] - a1[0]) / L;
      const q1 = [a1[0] + nx * p.off, a1[1] + ny * p.off], q2 = [a2[0] + nx * p.off, a2[1] + ny * p.off], col = C.dim;
      const ex = (q, b) => { const e = 5 / k * Math.sign(p.off || 1); return `<line x1="${X(b[0])}" y1="${Y(b[1])}" x2="${X(q[0] + nx * e)}" y2="${Y(q[1] + ny * e)}" stroke="${col}" stroke-width="0.6"/>`; };
      const tick = q => { const x = X(q[0]), y = Y(q[1]); return `<line x1="${x - 4}" y1="${y + 4}" x2="${x + 4}" y2="${y - 4}" stroke="${col}" stroke-width="1.1"/>`; };
      const mx = (X(q1[0]) + X(q2[0])) / 2, my = (Y(q1[1]) + Y(q2[1])) / 2, vert = Math.abs(a2[0] - a1[0]) < Math.abs(a2[1] - a1[1]);
      const sx = Math.sign(p.off || 1) * (vert ? (nx > 0 ? 1 : -1) : 0), sy = vert ? 0 : -Math.sign(p.off || 1) * (ny > 0 ? 1 : -1);
      const tx = mx + (vert ? sx * 5 : 0), ty = my + (vert ? 0 : sy * 5);
      s += `<g${a}>${title(p)}${ex(q1, a1)}${ex(q2, a2)}<line x1="${X(q1[0])}" y1="${Y(q1[1])}" x2="${X(q2[0])}" y2="${Y(q2[1])}" stroke="${col}" stroke-width="0.8"/>${tick(q1)}${tick(q2)}`;
      s += vert ? `<text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" font-size="10.5" fill="${col}" text-anchor="middle" transform="rotate(-90 ${tx.toFixed(1)} ${ty.toFixed(1)})" dy="${sx > 0 ? 9 : -3}">${symX(p.txt)}</text></g>`
        : `<text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" font-size="10.5" fill="${col}" text-anchor="middle" dy="${sy > 0 ? 9 : -2}">${symX(p.txt)}</text></g>`;
    } else if (p.t === 'text') texts.push(p);
  });
  texts.forEach(p => {
    const x = X(p.pts[0][0]) + (p.dx || 0), y = Y(p.pts[0][1]) + (p.dy || 0), a = attrs(p);
    const body = `x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="${p.fs || 11}" text-anchor="${p.a || 'middle'}"${p.w ? ` font-weight="${p.w}"` : ''}${p.it ? ' font-style="italic"' : ''}`;
    if (p.halo) s += `<text ${body} fill="none" stroke="#ffffff" stroke-width="3.2" stroke-linejoin="round" stroke-opacity="0.85" aria-hidden="true" pointer-events="none">${symX(p.txt)}</text>`;
    s += `<text ${body} fill="${p.c || C.ink}"${a}>${title(p)}${symX(p.txt)}</text>`;
  });
  hdls.forEach(p => { s += `<circle class="hdl" data-h="${p.h}" cx="${X(p.ctr[0])}" cy="${Y(p.ctr[1])}" r="6.5" fill="${C.handle}" fill-opacity="0.85" stroke="#ffffff" stroke-width="1.5"><title>${escX(p.tip || '')}</title></circle>`; });
  s += '</svg>';
  scene.view = { k, bb, m, ox, W: W2, H };
  return s;
};
/* odwrotne przekształcenie: piksel → mm (do przeciągania uchwytów) */
WD.toModel = (scene, px, py) => { const v = scene.view; return [v.bb[0] + (px - v.ox) / v.k, v.bb[3] - (py - v.m) / v.k]; };
WD.etaLegend = () => `<div class="etaleg"><span><i style="background:${C.etaLow}"></i>η ≤ 0,50</span><span><i style="background:${C.etaMid}"></i>0,50–0,85</span><span><i style="background:${C.etaHigh}"></i>0,85–1,00</span><span><i style="background:${C.etaFail}"></i>η > 1,00</span><span><i class="ln" style="border-color:${C.strut}"></i>krzyżulec</span><span><i class="ln s" style="border-color:${C.tie}"></i>cięgno</span></div>`;

/* ------------------------------------------------------------------ DXF (AutoCAD R12, ASCII, model w mm) */
const encD = t => String(t).replace(/[⌀ØøΦφ]/g, '%%c').replace(/°/g, '%%d').replace(/±/g, '%%p').replace(/_\{([^}]*)\}/g, '$1').replace(/_/g, '')
  .replace(/[^\x20-\x7e]/g, ch => '\\U+' + ch.codePointAt(0).toString(16).toUpperCase().padStart(4, '0'));
const DXF_LAYERS = { col: ['SLUP', 8], corbel: ['BETON', 7], plate: ['PLYTA', 9], axes: ['OSIE', 8], loads: ['OBCIAZENIA', 1], dims: ['WYMIARY', 8], rebar: ['ZBR_GLOWNE', 1], links: ['STRZEMIONA', 3],
  cover: ['OTULINA', 8], marks: ['OPISY', 7], zones: ['STM_STREFY', 5], struts: ['STM_KRZYZULCE', 5], ties: ['STM_CIEGNA', 30], nodes: ['STM_WEZLY', 7], forces: ['STM_SILY', 5], eta: ['STM_ETA', 2],
  angles: ['STM_KATY', 8], reactions: ['REAKCJE', 6], crit: ['KRYTYCZNY', 1], text: ['OPISY', 7], frame: ['RAMKA', 7] };
WD.dxf = function (scenes) {
  const o = [], add = (...a) => { for (let i = 0; i < a.length; i += 2) o.push(String(a[i]), String(a[i + 1])); }, nn = v => { const r = Math.round(v * 1000) / 1000; return Object.is(r, -0) ? '0' : String(r); };
  const used = new Set(); const lay = L => { const d = DXF_LAYERS[L] || ['INNE', 7]; used.add(d[0] + '|' + d[1]); return d[0]; };
  const ent = [];
  const E = (...a) => ent.push(a);
  scenes.forEach(({ scene, dx, dy, title, th }) => {
    const T = q => [q[0] + dx, q[1] + dy];
    const h = th || 18;
    if (title) E('TEXT', lay('text'), T([0, 0])[0] + (scene.bb ? 0 : 0), dy + (scene.top || 0) + 3 * h, h * 1.4, title, 0);
    scene.pr.forEach(p => {
      const L = lay(p.L);
      if (p.t === 'poly' || p.t === 'pline') { const pts = p.pts.map(T); for (let i = 0; i < pts.length - 1; i++) E('LINE', L, pts[i], pts[i + 1]); if (p.t === 'poly') E('LINE', L, pts[pts.length - 1], pts[0]); }
      else if (p.t === 'line') E('LINE', L, T(p.pts[0]), T(p.pts[1]));
      else if (p.t === 'arrow') { const a = T(p.pts[0]), b = T(p.pts[1]), Lh = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, ux = (b[0] - a[0]) / Lh, uy = (b[1] - a[1]) / Lh, hs = Math.min(40, Lh * 0.25);
        E('LINE', L, a, b); E('LINE', L, b, [b[0] - ux * hs - uy * hs * 0.35, b[1] - uy * hs + ux * hs * 0.35]); E('LINE', L, b, [b[0] - ux * hs + uy * hs * 0.35, b[1] - uy * hs - ux * hs * 0.35]); }
      else if (p.t === 'circle') E('CIRCLE', L, T(p.ctr), p.r || 8);
      else if (p.t === 'arc') E('ARC', L, T(p.ctr), p.r, p.a0, p.a0 + p.da);
      else if (p.t === 'text') E('TEXT', L, T(p.pts[0]), h * (p.fs || 11) / 11, p.txt, 0, p.a === 'start' ? 0 : p.a === 'end' ? 2 : 1);
      else if (p.t === 'dim') {
        const [a1, a2] = p.pts.map(T), Ld = Math.hypot(a2[0] - a1[0], a2[1] - a1[1]) || 1, nx = -(a2[1] - a1[1]) / Ld, ny = (a2[0] - a1[0]) / Ld;
        const q1 = [a1[0] + nx * p.off, a1[1] + ny * p.off], q2 = [a2[0] + nx * p.off, a2[1] + ny * p.off];
        E('LINE', L, a1, q1); E('LINE', L, a2, q2); E('LINE', L, q1, q2);
        [q1, q2].forEach(q => E('LINE', L, [q[0] - 8, q[1] - 8], [q[0] + 8, q[1] + 8]));
        const vert = Math.abs(a2[0] - a1[0]) < Math.abs(a2[1] - a1[1]), mid = [(q1[0] + q2[0]) / 2 + (vert ? -6 : 0), (q1[1] + q2[1]) / 2 + (vert ? 0 : 6)];
        E('TEXT', L, mid, h * 0.9, p.txt, vert ? 90 : 0, 1);
      }
    });
  });
  add(0, 'SECTION', 2, 'HEADER', 9, '$ACADVER', 1, 'AC1009', 9, '$INSUNITS', 70, 4, 0, 'ENDSEC');
  add(0, 'SECTION', 2, 'TABLES', 0, 'TABLE', 2, 'LTYPE', 70, 1, 0, 'LTYPE', 2, 'CONTINUOUS', 70, 0, 3, 'Solid line', 72, 65, 73, 0, 40, 0, 0, 'ENDTAB');
  add(0, 'TABLE', 2, 'LAYER', 70, used.size); used.forEach(u => { const [nm, col] = u.split('|'); add(0, 'LAYER', 2, nm, 70, 0, 62, col, 6, 'CONTINUOUS'); }); add(0, 'ENDTAB');
  add(0, 'TABLE', 2, 'STYLE', 70, 1, 0, 'STYLE', 2, 'STANDARD', 70, 0, 40, 0, 41, 1, 50, 0, 71, 0, 42, 2.5, 3, 'txt', 4, '', 0, 'ENDTAB', 0, 'ENDSEC');
  add(0, 'SECTION', 2, 'ENTITIES');
  ent.forEach(e => {
    const [ty, L] = e;
    if (ty === 'LINE') add(0, 'LINE', 8, L, 10, nn(e[2][0]), 20, nn(e[2][1]), 30, 0, 11, nn(e[3][0]), 21, nn(e[3][1]), 31, 0);
    else if (ty === 'CIRCLE') add(0, 'CIRCLE', 8, L, 10, nn(e[2][0]), 20, nn(e[2][1]), 30, 0, 40, nn(e[3]));
    else if (ty === 'ARC') add(0, 'ARC', 8, L, 10, nn(e[2][0]), 20, nn(e[2][1]), 30, 0, 40, nn(e[3]), 50, nn(e[4]), 51, nn(e[5]));
    else if (ty === 'TEXT') {
      const pos = Array.isArray(e[2]) ? e[2] : [e[2], e[3]], hh = Array.isArray(e[2]) ? e[3] : e[4], tx = Array.isArray(e[2]) ? e[4] : e[5], rot = Array.isArray(e[2]) ? e[5] : e[6], j = Array.isArray(e[2]) ? e[6] : 0;
      add(0, 'TEXT', 8, L, 10, nn(pos[0]), 20, nn(pos[1]), 30, 0, 40, nn(hh), 1, encD(tx)); if (rot) add(50, nn(rot)); if (j) add(72, j, 11, nn(pos[0]), 21, nn(pos[1]), 31, 0);
    }
  });
  add(0, 'ENDSEC', 0, 'EOF');
  return o.join('\r\n') + '\r\n';
};
WD.bounds = bounds;
})(typeof window !== 'undefined' ? window : globalThis);
