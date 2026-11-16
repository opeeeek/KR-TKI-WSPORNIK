/* KRÓTKI WSPORNIK ST – zakładki wyników: Model STM, Zbrojenie wspornika, Optymalizacja, Raport; okna NDP, porównania, elementu */
(function () {
'use strict';
const WS = window.WS, WD = window.WD, ND = WS.ND;
const WV = window.WV = {};
const U = () => window.WU;
const ST_NAME = { ok: 'OK', fail: 'NIE', warn: 'UWAGA', na: 'N/D' };
const kNs = v => U().fmt(v / 1e3, 1);
const paneW = el => Math.max(520, Math.min(1180, (el.clientWidth || 1100) - 40));
const tb = (head, rows, cls) => `<div class="tscroll"><table class="sched ${cls || ''}"><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr>${rows.map(r => `<tr>${r.map((c, i) => `<td${i && typeof c === 'string' && /^[−\d\s,.∞—%]+$/.test(c) ? ' class="n"' : ''}>${c}</td>`).join('')}</tr>`).join('')}</table></div>`;

/* ------------------------------------------------------------ okno elementu modelu (klik na rysunku) */
WV.elementPopup = function (ref, combo) {
  const u = U(), R = u.R, { esc, fmt, sym } = u, sr = R.stm[combo] || R.stm[R.governing];
  const id = ref.split(':')[1], cs = R.checks.filter(c => c.element_ref === ref);
  let info = '';
  if (ref.startsWith('node:')) {
    const nz = sr.nodes[id], q = sr.truss.nodes.find(n => n.id === id);
    info = `<table class="kv"><tr><td>Położenie x / y</td><td>${fmt(q.x, 1)} / ${fmt(q.y, 1)}</td><td>mm</td></tr>${nz ? `<tr><td>Typ węzła</td><td>${esc(nz.type)}</td><td></td></tr>` : ''}${sr.solution.reactions[id] ? `<tr><td>Reakcja R<sub>x</sub> / R<sub>y</sub></td><td>${kNs(sr.solution.reactions[id][0])} / ${kNs(sr.solution.reactions[id][1])}</td><td>kN</td></tr>` : ''}</table>` +
      (nz && nz.faces.length ? tb(['Ścianka', 'F [kN]', 'długość [mm]', 't [mm]', 'σ [MPa]'], nz.faces.map(f => [esc(f.name), kNs(f.F), fmt(f.length, 1), fmt(f.t, 0), fmt(f.sigma, 2)])) : '');
  } else {
    const s = sr.struts.find(x => x.id === id), t = sr.ties.find(x => x.id === id), N = sr.solution.forces[id];
    info = `<table class="kv"><tr><td>Siła osiowa N</td><td>${kNs(N)}</td><td>kN (${N < 0 ? 'ściskanie' : 'rozciąganie'})</td></tr>${s ? `<tr><td>Szerokości w<sub>1</sub> / w<sub>2</sub></td><td>${fmt(s.w1, 1)} / ${fmt(s.w2, 1)}</td><td>mm</td></tr><tr><td>Grubości t<sub>1</sub> / t<sub>2</sub></td><td>${fmt(s.t1, 0)} / ${fmt(s.t2, 0)}</td><td>mm</td></tr><tr><td>Długość / θ</td><td>${fmt(s.length, 0)} / ${fmt(s.theta_deg, 1)}°</td><td></td></tr><tr><td>Kształt</td><td>${esc(s.shape)}</td><td>b<sub>dost</sub> = ${fmt(s.b_avail, 0)} mm</td></tr>` : ''}${t ? `<tr><td>Zbrojenie cięgna A<sub>s</sub></td><td>${fmt(t.As_prov || 0, 0)}</td><td>mm²</td></tr><tr><td>Wysokość strefy cięgna u</td><td>${fmt(t.u, 0)}</td><td>mm</td></tr>` : ''}</table>`;
  }
  const m = u.openModal(`<h3>${ref.startsWith('node:') ? 'Węzeł' : 'Pręt'} ${sym(WD.lab(id))} – kombinacja ${esc(sr.combination)}</h3>${info}<h4 class="lsec">Sprawdzenia elementu</h4>${cs.length ? `<table class="ctab">${cs.map((c, i) => `<tr data-ei="${i}" class="xclick"><td>${sym(c.title)}</td><td class="val">${u.ckCond(c)}</td><td class="bar">${u.utilBar(c)}</td><td><span class="st ${c.status}">${ST_NAME[c.status]}</span></td></tr>`).join('')}</table><p class="hint">Kliknij wiersz – jak obliczono.</p>` : '<p class="hint">Brak sprawdzeń przypisanych do elementu.</p>'}<div class="dbtn"><button class="btn pri" data-close>Zamknij</button></div>`, 'norm');
  u.$$('[data-ei]', m).forEach(tr => tr.addEventListener('click', () => u.explainPopup(cs[+tr.dataset.ei])));
};

/* ------------------------------------------------------------ zakładka Model STM */
let stmCombo = '', stmOpt = { stress: true, forces: true, widths: true, reactions: true, rebar: false, dims: false };
WV.renderStm = function (el) {
  const u = U(), R = u.R, v = u.V(), { esc, fmt, sym } = u;
  const combos = Object.keys(R.stm); if (!combos.includes(stmCombo)) stmCombo = R.governing;
  const sr = R.stm[stmCombo]; if (!sr) { el.innerHTML = '<div class="msg wrn">Brak modelu.</div>'; return; }
  const W = paneW(el), scene = WD.sceneStm(v, R, stmCombo, stmOpt);
  const chip = (k, l) => `<label class="chk" style="display:inline-flex"><input type="checkbox" data-so="${k}" ${stmOpt[k] ? 'checked' : ''}><span>${l}</span></label>`;
  let h = `<div class="dsumx"></div><div class="rebbar"><b>Model STM</b><select id="stmCmb" style="width:auto;min-width:200px">${combos.map(c => `<option ${c === stmCombo ? 'selected' : ''} value="${esc(c)}">${esc(c)}${c === R.governing ? ' – decydująca' : ''}</option>`).join('')}</select>
    ${chip('stress', 'pola naprężeń (η)')}${chip('forces', 'siły')}${chip('widths', 'szerokości')}${chip('reactions', 'reakcje')}${chip('rebar', 'zbrojenie')}${chip('dims', 'wymiary')}<span style="flex:1"></span><button class="btn sm" id="stmDxf">Eksport DXF modelu</button></div>
    <div class="box"><div class="schemewrap stmwrap">${WD.svg(scene, W, { H: Math.min(640, Math.max(480, W * 0.55)) })}</div>${stmOpt.stress ? WD.etaLegend() : ''}<p class="hint">Kliknij węzeł, krzyżulec lub cięgno – siły, wymiary stref i sprawdzenia elementu. ${sr.model_type ? 'Model: ' + esc(sr.model_type) + '.' : ''}</p></div><div class="stmgrid">`;
  // dobór x_c i stan modelu
  Object.entries(sr.sides || {}).forEach(([sd, sm]) => {
    const p = sm.params, s = sm.state, se = sm.search || {};
    h += `<div class="box"><h4>Wspornik ${WS.SIDE_NAME[sd]} – parametry modelu J.3</h4><table class="kv">
      <tr><td>V<sub>Ed</sub> / H<sub>Ed</sub> / M<sub>Ed</sub></td><td>${kNs(p.V)} / ${kNs(p.H)} / ${fmt(p.M / 1e6, 1)}</td><td>kN, kNm</td></tr>
      <tr><td>ξ<sub>A</sub> (położenie węzła A)</td><td>${fmt(p.xi_A, 1)}</td><td>mm</td></tr><tr><td>d / c<sub>t</sub> / u</td><td>${fmt(p.d, 0)} / ${fmt(p.c_t, 0)} / ${fmt(p.u, 0)}</td><td>mm</td></tr>
      <tr><td>a<sub>ef</sub> / t<sub>A</sub> / t<sub>B</sub></td><td>${fmt(p.a_ef, 0)} / ${fmt(p.t_A, 0)} / ${fmt(p.t_B, 0)}</td><td>mm</td></tr><tr><td>a<sub>H</sub></td><td>${fmt(p.a_H, 0)}</td><td>mm</td></tr>
      <tr><td>Dobór x<sub>c</sub></td><td style="text-align:left;font-weight:400" colspan="2">${esc(se.method || '')}; przedział [${fmt(se.x_min, 0)}; ${fmt(se.x_max, 0)}] mm</td></tr>
      <tr><td>x<sub>c</sub> / z<sub>0</sub> / a<sub>B</sub></td><td>${fmt(s.x_c, 1)} / ${fmt(s.z0, 1)} / ${fmt(s.a_B, 1)}</td><td>mm</td></tr>
      <tr><td>F<sub>c</sub> / T / C</td><td>${kNs(s.Fc)} / ${kNs(s.T)} / ${kNs(s.C)}</td><td>kN</td></tr>
      <tr><td>θ / tan θ</td><td>${fmt(s.theta_deg, 2)}° / ${fmt(s.tan_theta, 3)}</td><td>(1,0–2,5)</td></tr>
      <tr><td>w<sub>A</sub> / w<sub>B</sub></td><td>${fmt(s.w_A, 1)} / ${fmt(s.w_B, 1)}</td><td>mm</td></tr></table>${sm.feasible ? '' : `<div class="msg wrn">${esc(sm.infeasible_reason)}</div>`}${(p.notes || []).map(n => `<p class="hint">${esc(n)}</p>`).join('')}</div>`;
  });
  const sol = sr.solution;
  h += `<div class="box"><h4>Siły w prętach i reakcje</h4>${tb(['Pręt', 'typ', 'N [kN]'], sr.truss.members.map(m => [sym(WD.lab(m.id)), m.kind === 'strut' ? 'krzyżulec' : 'cięgno', kNs(sol.forces[m.id] || 0)]))}${tb(['Węzeł', 'x [mm]', 'y [mm]', 'R<sub>x</sub> [kN]', 'R<sub>y</sub> [kN]'], sr.truss.nodes.map(q => [sym(WD.lab(q.id)), fmt(q.x, 1), fmt(q.y, 1), sol.reactions[q.id] ? kNs(sol.reactions[q.id][0]) : '', sol.reactions[q.id] ? kNs(sol.reactions[q.id][1]) : '']))}</div>`;
  h += `<div class="box"><h4>Kontrola modelu</h4><table class="kv"><tr><td>Status rozwiązania</td><td>${esc(sol.status)}</td><td>${esc(sol.method)}</td></tr><tr><td>rank(A) / równań / niewiadomych</td><td>${sol.rank} / ${sol.n_equations} / ${sol.n_unknowns}</td><td></td></tr>
    <tr><td>max residuum węzłowe</td><td>${sol.max_residual.toExponential(2)}</td><td>N (tol ${sol.tolerance.toExponential(1)})</td></tr><tr><td>ΣF<sub>x</sub>, ΣF<sub>y</sub>, ΣM</td><td>${sol.global_residual.map(x => x.toExponential(1)).join('; ')}</td><td>N, N·mm</td></tr>
    <tr><td>Różnica rozw. zamkniętego i macierzowego</td><td>${(sr.comparison.max_rel_diff || 0).toExponential(1)}</td><td></td></tr></table>${(sol.messages || []).map(m => `<p class="hint">${esc(m)}</p>`).join('')}
    <h4 style="margin-top:10px">Walidacja automatyczna</h4><table class="kv">${(R.validation || []).map(it => `<tr><td>${esc(it.name)}</td><td style="color:var(--${it.ok ? 'ok' : 'fail'})">${it.ok ? '✔' : '✖'}</td><td>${esc(it.detail)}</td></tr>`).join('')}</table></div>`;
  h += `<div class="box"><h4>Założenia modelu</h4><ul class="alist">${(R.assumptions || []).map(a => `<li>${esc(a)}</li>`).join('')}</ul></div></div>`;
  el.innerHTML = h;
  u.renderDsum();
  u.$('#stmCmb', el).onchange = e => { stmCombo = e.target.value; WV.renderStm(el); };
  u.$$('[data-so]', el).forEach(c => c.addEventListener('change', () => { stmOpt[c.dataset.so] = c.checked; WV.renderStm(el); }));
  u.$('.stmwrap', el).addEventListener('click', e => { const t = e.target.closest('[data-ref]'); if (t && /^(node|member):/.test(t.dataset.ref)) WV.elementPopup(t.dataset.ref, stmCombo); });
  u.$('#stmDxf', el).onclick = () => WV.exportDXF('stm');
};

/* ------------------------------------------------------------ zakładka Zbrojenie wspornika */
WV.renderRebar = function (el) {
  const u = U(), R = u.R, v = u.V(), { esc, fmt, sym } = u;
  if (!R.main) { el.innerHTML = `<div class="msg wrn">Zbrojenie nie zostało ustalone${v.stm.mode === 'manual' ? ' (tryb ręczny modelu STM)' : ''}.</div>`; return; }
  const W = paneW(el), sides = Object.keys(R.geometry.sides);
  const elev = WD.svg(WD.sceneRebar(v, R), Math.min(W * 0.66, 820), { H: 620 });
  const secs = sides.map(sd => `<div><div class="hint" style="text-align:center"><b>Przekrój ${sd === 'R' ? 'A–A' : 'B–B'}</b> – przy licu słupa${sides.length > 1 ? ` (${WS.SIDE_NAME[sd]})` : ''}</div>${WD.svg(WD.sceneSection(v, R, sd), 330, { H: 420 })}</div>`).join('');
  const ml = R.main, cv = R.cover, mb = R.main_input;
  let h = `<div class="dsumx"></div><div class="rebbar"><b>Zbrojenie wspornika</b><span style="flex:1"></span><button class="btn sm pri" id="rbDxf">Eksport DXF (rysunek zbrojenia)</button><button class="btn sm" id="rbAreas">Tablica pól przekroju prętów</button></div>
    <div class="box"><div class="fig rbfig">${elev}<div class="secs">${secs}</div></div></div><div class="stmgrid">`;
  const tie = R.checks.filter(c => /^TIE_[RL]$/.test(c.id));
  h += `<div class="box"><h4>Zbrojenie główne (cięgno)</h4><table class="kv"><tr><td>Pręty</td><td>${esc(ml.desc())}</td><td>A<sub>s</sub> = ${fmt(ml.As, 0)} mm²</td></tr>${tie.map(c => `<tr><td>A<sub>s,req</sub> = T<sub>Ed</sub>/f<sub>yd</sub> (${c.id.slice(-1)})</td><td>${fmt(c.E_d / R.materials.steel.fyd, 0)}</td><td>mm² (η = ${fmt(c.eta * 100, 0)}%)</td></tr>`).join('')}
    <tr><td>Odstęp w świetle a / s<sub>min</sub></td><td>${fmt(ml.a_clear, 1)} / ${fmt(ml.s_min, 1)}</td><td>mm</td></tr><tr><td>Oś cięgna c<sub>t</sub></td><td>${fmt(ml.c_t, 1)}</td><td>mm</td></tr>
    <tr><td>Zakotwienie przy obciążeniu</td><td colspan="2" style="text-align:left;font-weight:400">${esc(WS.ANCHOR_LABEL[mb.anchor_load] || mb.anchor_load)}</td></tr><tr><td>Zakotwienie w słupie</td><td colspan="2" style="text-align:left;font-weight:400">${esc(WS.ANCHOR_LABEL[mb.anchor_column] || mb.anchor_column)}</td></tr>
    <tr><td>Otulina c<sub>nom</sub> (strzemiona) / pręty główne</td><td>${cv.c_nom} / ${fmt(cv.c_top_main, 0)}</td><td>mm</td></tr>${Object.entries(R.mandrels || {}).filter(([k]) => /load|column/.test(k)).map(([k, x]) => `<tr><td>Średnica trzpienia φ<sub>m</sub> (${k === 'load' ? 'przy obciążeniu' : 'w słupie'})</td><td>${fmt(x, 0)}</td><td>mm</td></tr>`).join('')}</table></div>`;
  h += `<div class="box"><h4>Strzemiona</h4><table class="kv">${Object.entries(R.links).map(([sd, ll]) => `${sides.length > 1 ? `<tr><td colspan="3"><b>${WS.SIDE_NAME[sd]}</b></td></tr>` : ''}<tr><td>Poziome</td><td>${esc(ll.desc_h())}</td><td>A = ${fmt(ll.As_h, 0)} mm²</td></tr><tr><td>Głębokości od góry</td><td colspan="2" style="text-align:left;font-weight:400">${ll.h_depths.map(d => fmt(d, 0)).join('; ') || '—'} mm</td></tr><tr><td>Pionowe</td><td>${esc(ll.desc_v())}</td><td>A = ${fmt(ll.As_v, 0)} mm²</td></tr>${ll.i_count ? `<tr><td>Ukośne w narożu</td><td>${ll.i_count}×2 φ${ll.i_phi}</td><td></td></tr>` : ''}`).join('')}</table></div>`;
  const anch = Object.entries(R.anchorage || {});
  if (anch.length) h += `<div class="box"><h4>Zakotwienia (8.4, 8.6)</h4>${tb(['Miejsce', 'f<sub>bd</sub> [MPa]', 'σ<sub>sd</sub> [MPa]', 'l<sub>b,rqd</sub>', 'α₁…α₅', 'l<sub>bd</sub>', 'l<sub>dost</sub>', 'status'], anch.map(([k, r]) => {
    const c = R.checks.find(x => x.id === r.inp.id); const al = r.alphas;
    return [esc(r.inp.title.replace(/^Zakotwienie zbrojenia głównego /, '').replace(/^Przekazanie /, '')), fmt(r.fbd, 2), fmt(r.sigma_sd, 1), fmt(r.lb_rqd, 0), [al['α1'], al['α2'], al['α3'], al['α4'], al['α5']].map(x => fmt(x, 2)).join('·'), fmt(r.lbd, 0), fmt(r.inp.l_avail, 0), c ? `<span class="st ${c.status}">${ST_NAME[c.status]}</span>` : ''];
  }))}<p class="hint">Długości w mm, mierzone wzdłuż osi pręta (rys. 8.1a); ścieżka obliczeń 8.4 lub 8.6 – w Podsumowaniu („Jak obliczono”).</p></div>`;
  const sch = R.schedule || [];
  if (sch.length) {
    const tot = sch.reduce((a, b) => a + b.mass, 0), byPhi = {};
    sch.forEach(b => { byPhi[b.phi] = (byPhi[b.phi] || 0) + b.mass; });
    h += `<div class="box" style="grid-column:1/-1"><h4>Zestawienie stali (${esc(v.materials.steel_name)})</h4><div class="tscroll"><table class="sched"><tr><th>Poz.</th><th>Opis</th><th>Kształt</th><th>φ [mm]</th><th>Liczba</th><th>Długość [mm]</th><th>Długość łączna [m]</th><th>Masa [kg]</th></tr>${sch.map(b => `<tr><td>${esc(b.mark)}</td><td>${esc(b.description)}</td><td>${esc(b.shape)}</td><td class="n">${fmt(b.phi, 0)}</td><td class="n">${b.count}</td><td class="n">${fmt(b.length, 0)}</td><td class="n">${fmt(b.total_length / 1000, 2)}</td><td class="n">${fmt(b.mass, 2)}</td></tr>`).join('')}
      ${Object.entries(byPhi).sort((a, b) => a[0] - b[0]).map(([p, m]) => `<tr><td colspan="7" style="text-align:right">razem φ${fmt(+p, 0)}</td><td class="n">${fmt(m, 2)}</td></tr>`).join('')}<tr class="tot"><td colspan="7" style="text-align:right">Razem stal</td><td class="n">${fmt(tot, 2)}</td></tr></table></div><p class="hint">Długości orientacyjne (bez dokładnej geometrii gięcia, zakłady i naddatki pominięte) – do zestawienia wykonawczego wymagana weryfikacja.</p></div>`;
  }
  if ((R.design_log || []).length) h += `<div class="box" style="grid-column:1/-1"><details class="exh"><summary>Przebieg doboru automatycznego (${R.design_log.length})</summary><div><ul class="alist">${R.design_log.map(l => `<li>${esc(l)}</li>`).join('')}</ul></div></details></div>`;
  el.innerHTML = h + '</div>'; u.renderDsum();
  u.$('#rbDxf', el).onclick = () => WV.exportDXF('reb');
  u.$('#rbAreas', el).onclick = () => WV.areasPopup();
  u.$('.rbfig', el).addEventListener('click', e => { const t = e.target.closest('[data-go]'); if (!t) return; const g = { main: 'main', links: 'links', mat: 'mat', geo: 'geo', col: 'col', plate: 'plate' }[t.dataset.go]; if (g) { u.selectTab('data'); setTimeout(() => { const d = u.$(`#inputs details[data-id="${g}"]`); if (d) { d.open = true; d.scrollIntoView({ block: 'start' }); u.flash(d); } }, 80); } });
};
WV.areasPopup = function () {
  const u = U(), { fmt } = u, ds = [6, 8, 10, 12, 14, 16, 20, 25, 28, 32], ns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  u.openModal(`<h3>Pola przekroju prętów A<sub>s</sub> [mm²] i masa [kg/m]</h3><div class="tscroll"><table class="sched"><tr><th>φ</th>${ns.map(n => `<th>${n}</th>`).join('')}<th>kg/m</th></tr>${ds.map(d => `<tr><td><b>φ${d}</b></td>${ns.map(n => `<td class="n">${fmt(n * WS.barArea(d), 0)}</td>`).join('')}<td class="n">${fmt(WS.barMass(d), 3)}</td></tr>`).join('')}</table></div><div class="dbtn"><button class="btn pri" data-close>Zamknij</button></div>`);
};

/* ------------------------------------------------------------ eksport DXF */
WV.exportDXF = async function (what) {
  const u = U(), R = u.R, v = u.V();
  if (!R || WS.errorsOf(R).length || !R.geometry) { u.toast('Usuń błędy danych przed eksportem rysunku.'); return; }
  const scenes = [];
  const add = (sc, title) => { const bb = WD.bounds(sc.pr); scenes.push({ sc, title, bb }); };
  if (R.main && what !== 'stm') { add(WD.sceneRebar(v, R), 'ZBROJENIE WSPORNIKA'); Object.keys(R.geometry.sides).forEach(sd => add(WD.sceneSection(v, R, sd), 'PRZEKROJ ' + (sd === 'R' ? 'A-A' : 'B-B'))); }
  add(WD.sceneStm(v, R, R.governing, { stress: true, forces: true, widths: true, reactions: true }), 'MODEL STM - ' + R.governing);
  let x = 0; const list = scenes.map(s => { const dx = x - s.bb[0]; x += (s.bb[2] - s.bb[0]) + 400; return { scene: Object.assign(s.sc, { top: s.bb[3] }), dx, dy: 0, title: s.title, th: 20 }; });
  const txt = WD.dxf(list);
  await u.saveAny(u.safeName(what === 'stm' ? ' – model STM.dxf' : ' – zbrojenie.dxf'), txt, 'application/dxf', 'dxf', 'Zapisano rysunek');
};

/* ------------------------------------------------------------ zakładka Optymalizacja */
let optRes = null, optRun = null;
const optDef = () => ({ objective: 'steel', hc: [400, 700, 50], lc: null, b: null, concretes: ['C25/30', 'C30/37', 'C35/45', 'C40/50'], diameters: [12, 14, 16, 20, 25], steel_price: 5.5, max_variants: 300 });
WV.renderOpt = function (el) {
  const u = U(), S = u.getS(), { esc, fmt } = u, v = u.V();
  const o = S.meta.opt = Object.assign(optDef(), S.meta.opt || {});
  const rngIn = (k, lab) => { const r = o[k]; return `<div class="row"><label>${lab}</label><span class="rng"><label class="chk" style="display:inline-flex"><input type="checkbox" data-ron="${k}" ${r ? 'checked' : ''}></label>${['od', 'do', 'krok'].map((t, i) => `<input class="txt sm" data-rk="${k}.${i}" value="${r ? r[i] : ''}" placeholder="${t}" ${r ? '' : 'disabled'}>`).join('')}</span><span class="unit">mm</span></div>`; };
  let h = `<div class="dsumx"></div><div class="optgrid"><div class="box"><h4>Optymalizacja wspornika</h4><p class="hint">Przeszukiwanie siatki wariantów (deterministyczne). Każdy wariant przechodzi pełną analizę z automatycznym doborem zbrojenia – dopuszczalny jest tylko wariant bez błędów, bez niespełnionych sprawdzeń i w zakresie modelu J.3. Wymiary bieżące: h<sub>c</sub> = ${v.geometry.right.h_c} mm, l<sub>c</sub> = ${v.geometry.right.l_c} mm, b = ${v.geometry.b} mm, ${esc(v.materials.concrete)}.</p>
    <div class="fields" style="padding-left:0">
    <div class="row"><label>Kryterium</label><select id="opObj">${Object.entries(WS.OBJECTIVES).map(([k, l]) => `<option value="${k}" ${k === o.objective ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select><span></span></div>
    ${rngIn('hc', 'Wysokość przy licu h<sub>c</sub>')}${rngIn('lc', 'Wysięg l<sub>c</sub>')}${rngIn('b', 'Szerokość b')}
    <div class="row wide"><label>Klasy betonu</label><div>${WS.CONCRETE_CLASSES.filter(c => +c.slice(1).split('/')[0] <= 60).map(c => `<label class="chk" style="display:inline-flex;margin-right:8px"><input type="checkbox" data-oc="${c}" ${o.concretes.includes(c) ? 'checked' : ''}><span>${c}</span></label>`).join('')}</div></div>
    <div class="row wide"><label>Średnice prętów głównych</label><div>${[12, 14, 16, 20, 25, 28, 32].map(d => `<label class="chk" style="display:inline-flex;margin-right:8px"><input type="checkbox" data-od="${d}" ${o.diameters.includes(d) ? 'checked' : ''}><span>φ${d}</span></label>`).join('')}</div></div>
    <div class="row"><label>Cena stali</label><input class="txt" id="opSp" value="${String(o.steel_price).replace('.', ',')}"><span class="unit">zł/kg</span></div>
    <div class="row"><label>Maks. liczba wariantów</label><input class="txt" id="opMax" value="${o.max_variants}"><span class="unit"></span></div></div>
    <div class="dbtn" style="justify-content:flex-start"><button class="btn pri" id="opGo">${optRun ? 'Przerwij' : '▶ Uruchom optymalizację'}</button><span id="opProg" class="hint" style="margin:0"></span></div></div>
    <div class="box" id="opRes">${optResHTML()}</div></div>`;
  el.innerHTML = h; u.renderDsum();
  const save = () => { u.setDirty(); };
  u.$('#opObj', el).onchange = e => { o.objective = e.target.value; save(); };
  u.$$('[data-ron]', el).forEach(c => c.addEventListener('change', () => { const k = c.dataset.ron, base = { hc: v.geometry.right.h_c, lc: v.geometry.right.l_c, b: v.geometry.b }[k]; o[k] = c.checked ? [Math.max(100, base - 100), base + 200, 50] : null; save(); WV.renderOpt(el); }));
  u.$$('[data-rk]', el).forEach(i => i.addEventListener('input', () => { const [k, j] = i.dataset.rk.split('.'); const x = parseFloat(i.value.replace(',', '.')); i.classList.toggle('bad', !isFinite(x)); if (isFinite(x) && o[k]) { o[k][+j] = x; save(); } }));
  u.$$('[data-oc]', el).forEach(c => c.addEventListener('change', () => { const a = o.concretes, k = c.dataset.oc; if (c.checked && !a.includes(k)) a.push(k); if (!c.checked) a.splice(a.indexOf(k), 1); save(); }));
  u.$$('[data-od]', el).forEach(c => c.addEventListener('change', () => { const a = o.diameters, k = +c.dataset.od; if (c.checked && !a.includes(k)) a.push(k); if (!c.checked) a.splice(a.indexOf(k), 1); a.sort((x, y) => x - y); save(); }));
  u.$('#opSp', el).oninput = e => { const x = parseFloat(e.target.value.replace(',', '.')); if (isFinite(x)) { o.steel_price = x; save(); } };
  u.$('#opMax', el).oninput = e => { const x = parseInt(e.target.value, 10); if (x > 0) { o.max_variants = Math.min(2000, x); save(); } };
  u.$('#opGo', el).onclick = () => { if (optRun) { optRun.stop = true; return; } runOpt(el, o); };
  bindOptRes(el);
};
function optResHTML() {
  const u = U(), { esc, fmt } = u;
  if (!optRes) return '<h4>Wyniki</h4><p class="hint">Ustaw zakresy i uruchom optymalizację. Najlepszy wariant można przyjąć do projektu jako nowy wariant albo zastąpić bieżący.</p>';
  const ok = optRes.filter(o => o.feasible);
  return `<h4>Wyniki – ${optRes.length} wariantów, dopuszczalnych ${ok.length}</h4><div class="tscroll"><table class="sched opttab"><tr><th></th><th>h<sub>c</sub></th><th>h<sub>e</sub></th><th>l<sub>c</sub></th><th>b</th><th>beton</th><th>zbrojenie główne</th><th>stal [kg]</th><th>beton [m³]</th><th>koszt stali [zł]</th><th>η<sub>max</sub></th><th>wynik</th><th></th></tr>${optRes.slice(0, 60).map((o, i) => `<tr class="${o.feasible ? '' : 'nok'}"><td>${o.feasible ? '✔' : '✖'}</td><td class="n">${fmt(o.h_c, 0)}</td><td class="n">${fmt(o.h_e, 0)}</td><td class="n">${fmt(o.l_c, 0)}</td><td class="n">${fmt(o.b, 0)}</td><td>${esc(o.concrete)}</td><td>${esc(o.main)}</td><td class="n">${fmt(o.steel_kg, 1)}</td><td class="n">${fmt(o.concrete_m3, 3)}</td><td class="n">${fmt(o.steel_kg * (U().getS().meta.opt.steel_price || 0), 0)}</td><td class="n">${isFinite(o.eta_max) ? fmt(o.eta_max * 100, 0) + '%' : '∞'}</td><td title="${esc(o.reason)}">${esc(o.verdict)}</td><td>${o.feasible ? `<button class="btn sm" data-oa="${i}">Przyjmij</button>` : ''}</td></tr>`).join('')}</table></div>`;
}
function bindOptRes(el) {
  const u = U();
  u.$$('[data-oa]', el).forEach(b => b.addEventListener('click', async () => {
    const o = optRes[+b.dataset.oa], v = u.clone(o.variant); v.name = `Optymalny (${WS.OBJECTIVES[u.getS().meta.opt.objective].replace(/^Minimaln\w+ |^Najmniejsze /, '')})`;
    const asNew = await u.ask('Przyjąć wariant jako <b>nowy wariant projektu</b> (zalecane)? „Anuluj” – bez zmian.', 'Dodaj jako nowy wariant');
    if (asNew) { u.addVariant(v); u.toast('Dodano wariant optymalny.'); u.selectTab('sum'); }
  }));
}
function runOpt(el, o) {
  const u = U(), base = u.clone(u.V()), s = { objective: o.objective, h_c: o.hc, l_c: o.lc, b: o.b, concretes: o.concretes, diameters: o.diameters, steel_price: o.steel_price, max_variants: o.max_variants };
  const { list, total } = WS.optGrid(base, s); const out = []; let k = 0;
  optRun = { stop: false }; optRes = null; WV.renderOpt(el);
  const prog = () => { const p = u.$('#opProg'); if (p) p.textContent = `${k} / ${list.length}${total > list.length ? ` (ograniczono z ${total})` : ''}…`; };
  const step = () => {
    if (optRun.stop || k >= list.length) {
      optRes = WS.optSort(out); const stopped = optRun.stop; optRun = null;
      const p = u.$('#p-opt'); if (p && p.classList.contains('on')) WV.renderOpt(p); u.toast(stopped ? 'Optymalizacja przerwana.' : 'Optymalizacja zakończona.'); return;
    }
    const t0 = Date.now();
    while (k < list.length && Date.now() - t0 < 60) { const r = WS.optEvaluate(list[k], s); r.objective = WS.optObjective(r, s.objective); out.push(r); k++; }
    prog(); setTimeout(step, 0);
  };
  step();
}

/* ------------------------------------------------------------ okno parametrów NDP */
WV.ndpPopup = function () {
  const u = U(), v = u.V(), { esc } = u, ed = ND.editions[v.normative.edition], nm = v.normative;
  if (!ed || !ed.implemented) { u.openModal(`<h3>Parametry normowe</h3><p>Edycja „${esc(ed ? ed.title : nm.edition)}” nie jest zaimplementowana – obliczenia są zablokowane.</p><div class="dbtn"><button class="btn pri" data-close>Zamknij</button></div>`); return; }
  const rows = ed.params.map(p => {
    const val = nm.overrides[p.key] !== undefined ? nm.overrides[p.key] : p.value, over = nm.overrides[p.key] !== undefined;
    return `<tr class="${over ? 'over' : ''}"><td>${u.sym(p.symbol)}</td><td>${p.editable && typeof p.value === 'number' ? `<input class="txt sm" data-pv="${p.key}" value="${String(val).replace('.', ',')}" style="width:74px">` : esc(Array.isArray(val) ? JSON.stringify(val) : val)}</td><td>${esc(p.unit)}</td><td>${esc(p.clause)}</td><td>${esc(ND.categoryLabel[p.category] || p.category)}</td><td>${esc(over ? 'nadpisana przez użytkownika' : p.status)}${p.blocking ? `<br><label class="chk" style="display:inline-flex"><input type="checkbox" data-pc="${p.key}" ${(nm.confirmed_params || []).includes(p.key) ? 'checked' : ''}><span>potwierdzam</span></label>` : ''}</td><td class="nt">${esc(p.description)}${p.na_note ? '<br><i>' + esc(p.na_note) + '</i>' : ''}</td></tr>`;
  }).join('');
  const m = u.openModal(`<h3>Parametry normowe – ${esc(ed.title)}</h3><p>Każdy współczynnik ma wskazane źródło i status. Parametry „do potwierdzenia z treścią normy” nie są stosowane automatycznie, dopóki ich nie potwierdzisz. Zmiana wartości jest odnotowywana w raporcie jako „nadpisana przez użytkownika”.</p>
    <label class="chk"><input type="checkbox" id="ndpOk" ${nm.ndp_confirmed ? 'checked' : ''}><span><b>Potwierdzam zgodność przyjętych parametrów NDP z Załącznikiem Krajowym</b> (bez potwierdzenia wynik jest warunkowy)</span></label>
    <div class="tscroll" style="max-height:52vh"><table class="sched ndptab"><tr><th>Symbol</th><th>Wartość</th><th>Jedn.</th><th>Źródło</th><th>Kategoria</th><th>Status</th><th>Opis</th></tr>${rows}</table></div>
    <div class="dbtn"><button class="btn" id="ndpRst">Przywróć wartości zalecane</button><button class="btn pri" id="ndpClose">Zamknij i przelicz</button></div>`, 'wide');
  u.$$('[data-pv]', m).forEach(i => i.addEventListener('change', () => {
    const p = ed.params.find(q => q.key === i.dataset.pv), x = parseFloat(i.value.replace(',', '.'));
    if (!isFinite(x)) { i.classList.add('bad'); return; } i.classList.remove('bad');
    if (Math.abs(x - p.value) < 1e-12) { delete nm.overrides[p.key]; delete nm.override_notes[p.key]; } else { nm.overrides[p.key] = x; nm.override_notes[p.key] = 'zmiana w oknie Parametry NDP'; }
    i.closest('tr').classList.toggle('over', nm.overrides[p.key] !== undefined);
  }));
  u.$$('[data-pc]', m).forEach(c => c.addEventListener('change', () => { const a = nm.confirmed_params = nm.confirmed_params || [], k = c.dataset.pc; if (c.checked && !a.includes(k)) a.push(k); if (!c.checked && a.includes(k)) a.splice(a.indexOf(k), 1); }));
  u.$('#ndpOk', m).onchange = e => { nm.ndp_confirmed = e.target.checked; };
  u.$('#ndpRst', m).onclick = () => { nm.overrides = {}; nm.override_notes = {}; WV.ndpPopup(); };
  u.$('#ndpClose', m).onclick = () => { m.style.display = 'none'; u.changed(true); };
};

/* ------------------------------------------------------------ porównanie wariantów */
WV.comparePopup = function () {
  const u = U(), S = u.getS(), { esc, fmt } = u;
  const rows = S.variants.map((v, i) => {
    let r; try { r = WS.analyze(u.clone(v)); } catch (e) { r = null; }
    const cr = r ? WS.critical(r) : null, kg = r ? r.schedule.reduce((a, b) => a + b.mass, 0) : 0;
    return `<tr class="${i === S.active ? 'gov' : ''}"><td><b>${i + 1}</b> ${esc(v.name)}</td><td>${v.geometry.b}×${v.geometry.right.h_c}/${v.geometry.right.h_e}, l<sub>c</sub> = ${v.geometry.right.l_c}, a<sub>c</sub> = ${v.geometry.right.a_c}</td><td>${esc(v.materials.concrete)}</td><td>${r && r.main ? esc(r.main.desc()) : '—'}</td><td class="n">${fmt(kg, 1)}</td><td class="n">${cr && isFinite(cr.eta) ? fmt(cr.eta * 100, 0) + '%' : '—'}</td><td>${r ? `<span class="st ${{ PASS_SCOPE: 'ok', CONDITIONAL: 'warn' }[r.verdict.code] || 'fail'}">${esc(r.verdict.title)}</span>` : ''}</td><td><button class="btn sm" data-cv="${i}">Przejdź</button></td></tr>`;
  }).join('');
  const m = u.openModal(`<h3>Porównanie wariantów</h3><div class="tscroll"><table class="sched"><tr><th>Wariant</th><th>Geometria [mm]</th><th>Beton</th><th>Zbrojenie główne</th><th>Stal [kg]</th><th>η<sub>max</sub></th><th>Wynik</th><th></th></tr>${rows}</table></div><div class="dbtn"><button class="btn pri" data-close>Zamknij</button></div>`, 'wide');
  u.$$('[data-cv]', m).forEach(b => b.addEventListener('click', () => { m.style.display = 'none'; const i = +b.dataset.cv; if (i !== S.active) { S.active = i; u.applyVariant(S.variants[i]); } }));
};

/* ------------------------------------------------------------ zakładka Raport */
const wrapPrint = html => `<table class="pwrap"><thead><tr><td><div class="psp"></div></td></tr></thead><tfoot><tr><td><div class="psp"></div></td></tr></tfoot><tbody><tr><td class="pbody">${html}</td></tr></tbody></table>`;
const repMode = () => (U().getS().meta.repMode === 'short' ? 'short' : 'full');
WV.repBuild = () => window.WR.build(U().R, U().getS(), repMode());
WV.renderReport = function (el) {
  const u = U(), R = u.R, md = repMode();
  const tools = `<div class="rtools"><span class="segsw">${[['full', 'Raport pełny'], ['short', 'Raport skrócony']].map(([k, l]) => `<button class="${md === k ? 'on' : ''}" data-rm="${k}">${l}</button>`).join('')}</span><span style="flex:1"></span>
    <button class="btn" id="rpHtml">Zapisz raport HTML…</button><button class="btn" id="rpOdt">Zapisz .odt (edytowalny)…</button><button class="btn" id="rpDxf">Eksport DXF…</button><button class="btn" id="rpJson">Wyniki JSON</button><button class="btn" id="rpCsv">Sprawdzenia CSV</button>${u.ART ? '' : '<button class="btn pri" id="rpPrint">Drukuj / zapisz PDF</button>'}</div>`;
  let body;
  try { body = WV.repBuild(); } catch (e) { console.error(e); body = `<div class="msg err">Błąd tworzenia raportu: ${u.esc(e.message)}</div>`; }
  el.innerHTML = tools + `<div id="report">${wrapPrint(body)}</div>`;
  u.$$('[data-rm]', el).forEach(b => b.addEventListener('click', () => { u.getS().meta.repMode = b.dataset.rm; u.setDirty(); WV.renderReport(el); }));
  u.$('#rpHtml', el).onclick = () => WV.exportHTML();
  u.$('#rpOdt', el).onclick = () => WV.exportODT();
  u.$('#rpDxf', el).onclick = () => WV.exportDXF('reb');
  u.$('#rpJson', el).onclick = () => WV.exportJSON();
  u.$('#rpCsv', el).onclick = () => WV.exportCSV();
  const pb = u.$('#rpPrint', el); if (pb) pb.onclick = () => window.print();
  if (!R) return;
};
function reportDoc(body) {
  const u = U(), css = document.getElementById('appcss').textContent;
  return `<!doctype html><html lang="pl" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Raport – ${u.esc(u.getS().info.name)}</title><style>${css}\nhtml,body{height:auto}body{overflow:auto;padding:20px 16px;background:#fff}.rtools{margin-bottom:14px}@media print{body{padding:0}.rtools{display:none}}</style></head><body><div class="rtools"><button class="btn pri" onclick="window.print()">Drukuj / zapisz PDF</button></div><div id="report">${wrapPrint(body)}</div></body></html>`;
}
WV.exportHTML = async function () {
  const u = U(); if (!u.R) return;
  await u.saveAny(u.safeName(repMode() === 'short' ? ' – raport skrócony.html' : ' – raport.html'), reportDoc(WV.repBuild()), 'text/html', 'html', 'Zapisano raport');
};
WV.exportODT = async function () {
  const u = U(); if (!u.R) return;
  u.toast('Tworzenie pliku .odt…', 1500);
  let bytes; try { bytes = await window.WR.odt(WV.repBuild(), (u.getS().info.name || 'Wspornik') + ' – raport obliczeń'); } catch (e) { console.error(e); u.toast('Błąd tworzenia .odt: ' + e.message); return; }
  await u.saveAny(u.safeName(' – raport.odt'), bytes, 'application/vnd.oasis.opendocument.text', 'odt', 'Zapisano raport', true);
};
WV.exportJSON = async function () {
  const u = U(), R = u.R; if (!R) return;
  const out = { format: 'KROTKI_WSPORNIK_ST_WYNIKI', program_version: u.VER, variant: u.V(), verdict: R.verdict, fingerprint: R.fingerprint, input_hash: R.input_hash, edition: R.edition_id,
    checks: R.checks.map(c => ({ id: c.id, group: c.group, title: c.title, clause: c.clause, basis: c.basis, E_d: c.E_d, R_d: c.R_d, eta: c.eta === Infinity ? 'inf' : c.eta, status: WS.ST_LABEL[c.status], combination: c.combination, element: c.element_ref, formula: c.formula, substitution: c.substitution, notes: c.notes })),
    messages: R.messages, params_used: R.params_used, validation: R.validation, schedule: R.schedule };
  await u.saveAny(u.safeName(' – wyniki.json'), JSON.stringify(out, null, 2), 'application/json', 'json', 'Zapisano wyniki');
};
WV.exportCSV = async function () {
  const u = U(), R = u.R; if (!R) return;
  const q = s => '"' + String(s === null || s === undefined ? '' : s).replace(/"/g, '""') + '"', num = v => v === null || v === undefined ? '' : !isFinite(v) ? 'inf' : String(+v.toPrecision(10)).replace('.', ',');
  const lines = [['id', 'grupa', 'sprawdzenie', 'podstawa', 'charakter', 'E_d', 'R_d', 'jednostka bazowa', 'eta', 'status', 'kombinacja', 'element'].map(q).join(';')]
    .concat(R.checks.map(c => [q(c.id), q(c.group), q(c.title), q(c.clause), q(c.basis), num(c.E_d), num(c.R_d), q({ force: 'N', stress: 'MPa', length: 'mm', area: 'mm2', moment: 'Nmm', ratio: '-', none: '' }[c.kind]), num(c.eta), q(WS.ST_LABEL[c.status]), q(c.combination), q(c.element_ref)].join(';')));
  await u.saveAny(u.safeName(' – sprawdzenia.csv'), '﻿' + lines.join('\r\n'), 'text/csv', 'csv', 'Zapisano sprawdzenia');
};
})();
