/* KRÓTKI WSPORNIK ST – raport obliczeń (notka): dane, parametry normowe, model STM, sprawdzenia z wzorami i podstawieniami,
   zbrojenie, walidacja, założenia i ograniczenia, wniosek. Wniosek pozytywny tylko przy werdykcie PASS_SCOPE. */
(function () {
'use strict';
const WR = window.WR = {};
WR.build = function (R, S, mode) {
  const U = window.WU, WS = window.WS, WD = window.WD, ND = WS.ND, { fmt, sym, esc } = U, v = S.variants[S.active], full = mode !== 'short';
  if (!R) return '<p>Brak wyników.</p>';
  const kN = x => fmt(x / 1e3, 1), f = (x, d) => fmt(x, d === undefined ? 2 : d);
  let hn = 0, o = '';
  const H2 = t => `<h2>${++hn}. ${t}</h2>`;
  const kv = pairs => pairs.filter(q => q && q[1] !== '' && q[1] !== undefined && q[1] !== null).map(([k, x]) => `<div class="eq">${k}: ${x}</div>`).join('');
  const tbl = (head, rows) => `<table class="sched rtab"><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</table>`;
  const vd = R.verdict, errs = WS.errorsOf(R), info = S.info, now = new Date();
  const ST = { ok: ['ok', '✔ SPEŁNIONO'], fail: ['fail', '✖ NIE SPEŁNIONO'], warn: ['warn', '! WYMAGA OSOBNEJ WERYFIKACJI'], na: ['info', '– NIE DOTYCZY'] };
  const vcls = { PASS_SCOPE: 'ok', CONDITIONAL: 'warn' }[vd.code] || 'fail';
  /* nagłówek */
  o += `<h1>Krótki wspornik żelbetowy – obliczenia metodą Strut-and-Tie</h1><div class="note" style="font-style:normal">${esc(info.element || '')}${info.object ? ' · ' + esc(info.object) : ''} · wariant: ${esc(v.name)}</div>`;
  o += tbl(['Projekt', 'Numer', 'Projektant', 'Sprawdzający', 'Data', 'Program'], [[esc(info.name || ''), esc(info.number || ''), esc(info.designer || ''), esc(info.checker || ''), now.toLocaleDateString('pl-PL'), `Krótki wspornik ST ${esc(U.VER)}`]]);
  o += `<div class="verdict ${vcls}" style="margin-top:10px">Wynik: ${esc(vd.title)}. <span style="font-weight:400">${esc(vd.text)}</span></div>`;
  o += `<p class="note">Podstawa: ${esc(R.edition_title || v.normative.edition)}; parametry NDP: ${v.normative.ndp_confirmed ? 'potwierdzone przez projektanta' : '<b>niepotwierdzone – wynik warunkowy</b>'}. Obciążenia charakterystyczne kombinowane wg PN-EN 1990; wartości obliczeniowe nie są ponownie mnożone przez współczynniki częściowe.</p>`;
  /* 1. dane wejściowe */
  o += H2('Dane wejściowe');
  const g = v.geometry, sides = WS.activeSides(g);
  o += `<h3>Geometria</h3>` + kv([['Układ', g.layout === 'double' ? 'wsporniki dwustronne' + (g.left_mirror ? ' (lewy = odbicie prawego)' : '') : 'wspornik jednostronny'], ['Wykonanie', g.construction === 'precast' ? 'oparcie elementu prefabrykowanego (10.9.5)' : 'monolityczne'],
    ['Szerokość wspornika', `b = ${g.b} mm`], ['Słup', `h<sub>col</sub> × b<sub>col</sub> = ${g.column.h_col} × ${g.column.b_col} mm, otulina ${g.column.cover} mm, pręty φ${g.column.phi_long}, strzemiona φ${g.column.phi_link}${g.column.N_Ed ? `, N<sub>Ed</sub> = ${kN(g.column.N_Ed)} kN (informacyjnie)` : ''}`]]);
  sides.forEach(sd => { const s = WS.sideInput(g, sd), p = s.plate; o += kv([[`Wspornik ${WS.SIDE_NAME[sd]}`, `l<sub>c</sub> = ${s.l_c} mm, h<sub>c</sub> = ${s.h_c} mm, h<sub>e</sub> = ${s.h_e} mm, x<sub>s</sub> = ${s.x_slope} mm, a<sub>c</sub> = ${s.a_c} mm`], [`Oparcie (${WS.SIDE_NAME[sd]})`, `${{ steel_plate: 'płyta stalowa', elastomer: 'łożysko elastomerowe', direct: 'oparcie bezpośrednie' }[p.kind]} a<sub>p</sub> × b<sub>p</sub> × t<sub>p</sub> = ${p.length} × ${p.width} × ${p.thickness} mm, przesunięcie ${p.offset} mm`]]); });
  if (R.geometry) o += `<div class="fig">${WD.svg(WD.sceneScheme(v, R, { stm: false, rebar: false, handles: false }), 640, { H: 520 })}</div>`;
  if (R.materials) {
    const c = R.materials.concrete, st = R.materials.steel;
    o += `<h3>Materiały</h3>` + kv([['Beton ' + esc(c.cls), `f<sub>ck</sub> = ${f(c.fck, 0)} MPa, f<sub>ctm</sub> = ${f(c.fctm)} MPa, f<sub>ctk,0,05</sub> = ${f(c.fctk005)} MPa, E<sub>cm</sub> = ${f(c.Ecm / 1000, 0)} GPa`],
      ['', `f<sub>cd</sub> = α<sub>cc</sub>·f<sub>ck</sub>/γ<sub>c</sub> = ${f(c.alpha_cc)}·${f(c.fck, 0)}/${f(c.gamma_c)} = <b>${f(c.fcd)} MPa</b>; f<sub>ctd</sub> = ${f(c.fctd)} MPa; ν′ = 1 − f<sub>ck</sub>/250 = ${f(c.nu_prime, 3)}; ν = ${f(c.nu_shear, 3)}`],
      ['Stal ' + esc(st.name), `f<sub>yk</sub> = ${f(st.fyk, 0)} MPa, klasa ${esc(st.ductility)}, f<sub>yd</sub> = f<sub>yk</sub>/γ<sub>s</sub> = ${f(st.fyk, 0)}/${f(st.gamma_s)} = <b>${f(st.fyd, 1)} MPa</b>; strzemiona f<sub>ywd</sub> = ${f(st.link_fyd, 1)} MPa; E<sub>s</sub> = ${f(st.Es / 1000, 0)} GPa`],
      ['Sytuacja obliczeniowa', R.materials.situation === 'accidental' ? 'wyjątkowa' : 'trwała / przejściowa'], ['Kruszywo', `d<sub>g</sub> = ${v.materials.d_g} mm`]]);
  }
  if (R.cover) o += `<h3>Otulina (4.4.1)</h3>` + kv([['Ekspozycja / klasa konstrukcji', `${esc(R.cover.exposure)} / ${esc(R.cover.structural_class)}`], ['', `c<sub>min,dur</sub> = ${R.cover.c_min_dur} mm, Δc<sub>dev</sub> = ${R.cover.delta_c_dev} mm, c<sub>nom,req</sub> (strzemiona) = ${f(R.cover.c_nom_req_link, 0)} mm, (pręty główne) = ${f(R.cover.c_nom_req_main, 0)} mm`], ['Przyjęto', `c<sub>nom</sub> = <b>${R.cover.c_nom} mm</b>${R.cover.user ? ' (wartość użytkownika)' : ''}; pręty główne: góra ${f(R.cover.c_top_main, 0)} mm, bok ${f(R.cover.c_side_main, 0)} mm`]]);
  o += `<h3>Oddziaływania</h3>` + tbl(['Nazwa', 'Strona', 'Kategoria', 'Charakter', 'V [kN]', 'H [kN]', 'M [kNm]', 'e<sub>y</sub> [mm]', 'Uwagi'], v.loads.actions.map(a => [esc(a.name), a.side === 'L' ? 'lewy' : 'prawy', esc(WS.CATEGORIES[a.category] || a.category), a.nature === 'design' ? 'obliczeniowe' : 'charakterystyczne', kN(a.V), kN(a.H), f(a.M / 1e6, 1), f(a.e_y, 0), esc(a.note || '')]));
  if (R.combinations.length) o += `<h3>Kombinacje (wartości obliczeniowe)</h3>` + tbl(['Kombinacja', 'Rodzaj'].concat(sides.flatMap(sd => [`V<sub>${sd}</sub> [kN]`, `H<sub>${sd}</sub> [kN]`, `M<sub>${sd}</sub> [kNm]`])), R.combinations.map(c => [esc(c.name) + (c.name === R.governing ? ' ◆' : ''), esc(WS.COMB_KINDS[c.kind] || c.kind)].concat(sides.flatMap(sd => { const q = c.sides[sd] || { V: 0, H: 0, M: 0 }; return [kN(q.V), kN(q.H), f(q.M / 1e6, 1)]; })))) + `<p class="note">◆ – kombinacja decydująca (największe wykorzystanie w modelu STM).</p>`;
  /* 2. parametry normowe */
  o += H2('Parametry normowe');
  if (full && R.params_used.length) o += tbl(['Symbol', 'Wartość', 'Jedn.', 'Źródło', 'Kategoria', 'Status'], R.params_used.map(p => [sym(p.symbol), esc(Array.isArray(p.value) ? JSON.stringify(p.value) : p.value), esc(p.unit), esc(p.clause), esc(p.category), esc(p.status) + (p.blocking ? (p.confirmed ? ' · potwierdzony' : ' · <b>niepotwierdzony – nie stosowany</b>') : '')]));
  else o += `<p>Zastosowano ${R.params_used.length} parametrów edycji ${esc(R.edition_id)}; ${R.params_used.filter(p => /nadpisana/.test(p.status)).length} nadpisanych przez użytkownika. Pełna tabela – raport pełny.</p>`;
  if (errs.length) {
    o += H2('Błędy krytyczne – obliczenia zablokowane') + errs.map(e => `<div class="eq fail">✖ ${esc(e.text)}</div>`).join('');
    o += `<div class="verdict fail">WNIOSEK: ${esc(vd.title)}. Raport nie zawiera wniosku pozytywnego.</div>`;
    return o + footer();
  }
  /* 3. model STM */
  const gov = R.stm[R.governing];
  o += H2('Model kratownicowy (STM)');
  o += `<p>${esc(R.model_type)}; kombinacja decydująca: <b>${esc(R.governing)}</b>.</p><h3>Założenia</h3><ul>${R.assumptions.map(a => `<li>${esc(a)}</li>`).join('')}</ul>`;
  if (gov) o += `<div class="fig">${WD.svg(WD.sceneStm(v, R, R.governing, { stress: true, forces: true, widths: true, reactions: true }), 700, { H: 560 })}</div>`;
  if (gov && gov.sides) Object.entries(gov.sides).forEach(([sd, sm]) => {
    const p = sm.params, s = sm.state, se = sm.search || {};
    o += `<h3>Wspornik ${WS.SIDE_NAME[sd]} – geometria modelu i siły (${esc(R.governing)})</h3>` +
      `<div class="eq">V<sub>Ed</sub> = ${kN(p.V)} kN; H<sub>Ed</sub> = ${kN(p.H)} kN${p.H !== p.H_raw ? ` (H<sub>Ed,in</sub> = ${kN(p.H_raw)} kN pominięte jako korzystne)` : ''}; M<sub>Ed</sub> = ${f(p.M / 1e6, 1)} kNm</div>` +
      `<div class="eq">d = h<sub>c</sub> − c<sub>t</sub> = ${f(p.h_c, 0)} − ${f(p.c_t, 1)} = ${f(p.d, 1)} mm; u = 2·c<sub>t</sub> = ${f(p.u, 1)} mm; a<sub>H</sub> = ${f(p.a_H, 1)} mm</div>` +
      `<div class="eq">ξ<sub>A</sub> = a<sub>c</sub> + M/V + H·a<sub>H</sub>/V = ${f(p.a_c, 0)} + ${f(p.V ? p.M / p.V : 0, 1)} + ${f(p.V ? p.H * p.a_H / p.V : 0, 1)} = <b>${f(p.xi_A, 1)} mm</b></div>` +
      `<div class="eq">a<sub>ef</sub> = a<sub>p</sub> − 2|e| = ${f(p.a_p, 0)} − 2·${f(Math.abs(p.e_rel), 1)} = ${f(p.a_ef, 1)} mm; t<sub>A</sub> = ${f(p.t_A, 0)} mm; t<sub>B</sub> = ${f(p.t_B, 0)} mm</div>` +
      `<div class="eq">Dobór x<sub>c</sub>: ${esc(se.method || '')}; przedział dopuszczalny [${f(se.x_min, 1)}; ${f(se.x_max, 1)}] mm → x<sub>c</sub> = <b>${f(s.x_c, 1)} mm</b></div>` +
      `<div class="eq">z<sub>0</sub> = d − x<sub>c</sub>/2 = ${f(p.d, 1)} − ${f(s.x_c / 2, 1)} = <b>${f(s.z0, 1)} mm</b>; a<sub>B</sub> = x<sub>c</sub>·V/F<sub>c</sub> = ${f(s.a_B, 1)} mm; ξ<sub>B</sub> = ${f(s.xi_B, 1)} mm</div>` +
      `<div class="eq">F<sub>c</sub> = ${kN(s.Fc)} kN; T = F<sub>c</sub> + H = <b>${kN(s.T)} kN</b>; C = √(F<sub>c</sub>² + V²) = <b>${kN(s.C)} kN</b>; tan θ = z<sub>0</sub>/(ξ<sub>A</sub> − ξ<sub>B</sub>) = ${f(s.tan_theta, 3)} (θ = ${f(s.theta_deg, 2)}°)</div>` +
      `<div class="eq">w<sub>A</sub> = a<sub>ef</sub>·sin θ + u·cos θ = ${f(s.w_A, 1)} mm; w<sub>B</sub> = √(x<sub>c</sub>² + a<sub>B</sub>²) = ${f(s.w_B, 1)} mm</div>` + (sm.feasible ? '' : `<div class="eq warn">! ${esc(sm.infeasible_reason)}</div>`);
  });
  if (gov && full) {
    const sol = gov.solution;
    o += `<h3>Rozwiązanie macierzowe kratownicy (kontrola)</h3>` + tbl(['Węzeł', 'x [mm]', 'y [mm]', 'R<sub>x</sub> [kN]', 'R<sub>y</sub> [kN]'], gov.truss.nodes.map(q => [sym(WD.lab(q.id)), f(q.x, 1), f(q.y, 1), sol.reactions[q.id] ? kN(sol.reactions[q.id][0]) : '', sol.reactions[q.id] ? kN(sol.reactions[q.id][1]) : ''])) +
      tbl(['Pręt', 'węzły', 'typ', 'N [kN]'], gov.truss.members.map(m => [sym(WD.lab(m.id)), `${sym(WD.lab(m.n1))}–${sym(WD.lab(m.n2))}`, m.kind === 'strut' ? 'krzyżulec' : 'cięgno', kN(sol.forces[m.id] || 0)])) +
      `<div class="eq">status: ${esc(sol.status)}; rank(A) = ${sol.rank} (równań ${sol.n_equations}, niewiadomych ${sol.n_unknowns}); max residuum ${sol.max_residual.toExponential(2)} N; ΣF<sub>x</sub> = ${sol.global_residual[0].toExponential(1)} N, ΣF<sub>y</sub> = ${sol.global_residual[1].toExponential(1)} N, ΣM = ${sol.global_residual[2].toExponential(1)} N·mm; różnica rozwiązania zamkniętego i macierzowego ${(gov.comparison.max_rel_diff || 0).toExponential(1)}</div>`;
  }
  /* 4. sprawdzenia */
  o += H2('Sprawdzenia');
  const unit = c => WS.UNIT_OF[c.kind] || '', sc = c => ({ force: 1e3, moment: 1e6 }[c.kind] || 1), val = (c, x) => x === null ? '—' : U.ckVal(c, x);
  if (full) {
    let grp = '', k = 0;
    R.checks.forEach(c => {
      if (c.group !== grp) { grp = c.group; o += `<h3>${hn}.${++k}. ${esc(grp)}</h3>`; }
      const st = ST[c.status];
      o += `<h4>${esc(c.title)}<span class="r">[${esc(c.clause)}]</span></h4>`;
      if (c.formula && c.formula !== '—') o += `<div class="eq">${sym(c.formula)}</div>`;
      if (c.substitution) o += `<div class="eq">${sym(c.substitution)}</div>`;
      if (c.E_d !== null && c.R_d !== null) o += `<div class="eq">${sym(c.E_label)} = ${val(c, c.E_d)} ${unit(c)} ≤ ${sym(c.R_label)} = ${val(c, c.R_d)} ${unit(c)}; η = ${c.eta !== null && isFinite(c.eta) && c.id !== 'MODEL_EQUILIBRIUM' ? fmt(c.eta, 3) : c.eta === Infinity ? '∞' : '—'} <span class="${st[0]}">${st[1]}</span></div>`;
      else o += `<div class="eq"><span class="${st[0]}">${st[1]}</span> – ${esc(c.conclusion)}</div>`;
      (c.notes || []).filter(Boolean).forEach(n => { o += `<p class="note">${esc(n)}</p>`; });
      if (c.basis !== WS.BASIS.NORMATIVE) o += `<p class="note">Charakter: ${esc(c.basis)}${c.combination ? '; kombinacja: ' + esc(c.combination) : ''}.</p>`;
    });
  } else {
    o += tbl(['Grupa', 'Sprawdzenie', 'Podstawa', 'E<sub>d</sub> ≤ R<sub>d</sub>', 'η', 'Status'], R.checks.map(c => [esc(c.group), sym(c.title), esc(c.clause), c.E_d !== null && c.R_d !== null ? `${val(c, c.E_d)} ≤ ${val(c, c.R_d)} ${unit(c)}` : '', c.eta !== null && isFinite(c.eta) && c.id !== 'MODEL_EQUILIBRIUM' ? fmt(c.eta * 100, 0) + '%' : '', `<span class="${ST[c.status][0]}">${ST[c.status][1]}</span>`]));
  }
  void sc;
  /* 5. zbrojenie */
  if (R.main) {
    o += H2('Zbrojenie wspornika');
    o += `<div class="fig">${WD.svg(WD.sceneRebar(v, R), 560, { H: 500 })}${Object.keys(R.geometry.sides).map(sd => WD.svg(WD.sceneSection(v, R, sd), 280, { H: 380 })).join('')}</div>`;
    const ml = R.main, mb = R.main_input;
    o += kv([['Zbrojenie główne', `<b>${esc(ml.desc())}</b>, A<sub>s</sub> = ${f(ml.As, 0)} mm², oś cięgna c<sub>t</sub> = ${f(ml.c_t, 1)} mm, odstęp w świetle ${f(ml.a_clear, 1)} mm (s<sub>min</sub> = ${f(ml.s_min, 1)} mm)`],
      ['Zakotwienie', `przy obciążeniu: ${esc(WS.ANCHOR_LABEL[mb.anchor_load])}; w słupie: ${esc(WS.ANCHOR_LABEL[mb.anchor_column])}`]].concat(Object.entries(R.links).map(([sd, ll]) => [`Strzemiona${Object.keys(R.links).length > 1 ? ' (' + WS.SIDE_NAME[sd] + ')' : ''}`, `${esc(ll.desc_h())}; ${esc(ll.desc_v())}${ll.i_count ? `; ${ll.i_count} pr. ukośne φ${ll.i_phi}` : ''}`])));
    if (R.schedule.length) {
      const tot = R.schedule.reduce((a, b) => a + b.mass, 0);
      o += `<h3>Zestawienie stali</h3>` + tbl(['Poz.', 'Opis', 'φ [mm]', 'Liczba', 'Długość [mm]', 'Masa [kg]'], R.schedule.map(b => [esc(b.mark), esc(b.description), f(b.phi, 0), b.count, f(b.length, 0), f(b.mass, 2)]).concat([['', '<b>Razem</b>', '', '', '', `<b>${f(tot, 2)}</b>`]])) + `<p class="note">Długości orientacyjne – zestawienie wykonawcze wymaga weryfikacji.</p>`;
    }
    if (full && R.design_log.length) o += `<h3>Przebieg doboru automatycznego</h3><ul>${R.design_log.map(l => `<li>${esc(l)}</li>`).join('')}</ul>`;
  }
  /* 6. walidacja i ograniczenia */
  o += H2('Walidacja automatyczna');
  o += R.validation.map(it => `<div class="eq"><span class="${it.ok ? 'ok' : 'fail'}">${it.ok ? '✔' : '✖'}</span> ${esc(it.name)} – ${esc(it.detail)}</div>`).join('');
  if (full) o += `<h3>Status weryfikacji modułów</h3>` + tbl(['Moduł', 'Status', 'Zakres weryfikacji'], Object.entries(WS.MODULE_STATUS).map(([k, [s, d]]) => [esc(k), esc(s), esc(d)]));
  const warns = R.messages.filter(m => m.level === 'warning');
  if (warns.length) o += `<h3>Ostrzeżenia</h3>` + [...new Set(warns.map(m => m.text))].map(t => `<div class="eq warn">! ${esc(t)}</div>`).join('');
  o += H2('Ograniczenia zakresu') + `<ul>${R.limitations.map(l => `<li>${esc(l)}</li>`).join('')}</ul>`;
  const ver = R.checks.filter(c => c.status === 'warn');
  if (ver.length) o += `<h3>Pozycje wymagające osobnej weryfikacji</h3><ul>${ver.map(c => `<li>${esc(c.title)} – ${esc(c.clause)}</li>`).join('')}</ul>`;
  o += H2('Wniosek') + `<div class="verdict ${vcls}">${esc(vd.title)}. <span style="font-weight:400">${esc(vd.text)}</span></div>`;
  if (!vd.positive) o += `<p class="note">Wniosek pozytywny nie może zostać sformułowany (${esc(vd.code)}).</p>`;
  return o + footer();
  function footer() { return `<p class="note" style="margin-top:18px">Odcisk wyników: ${esc(R.fingerprint)} · skrót danych: ${esc(R.input_hash)} · edycja: ${esc(R.edition_id)} · ${now.toLocaleString('pl-PL')}. Program jest narzędziem pomocniczym – wyniki wymagają weryfikacji przez osobę z uprawnieniami budowlanymi.</p>`; }
};
// eksport raportu do OpenDocument Text (.odt) – mechanizm przejęty z programu BelkaŻB
WR.odt = async function (html, title) {
  const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const host = document.createElement('div'); host.style.cssText = 'position:fixed;left:-10000px;top:0;width:1000px;'; host.innerHTML = html; document.body.appendChild(host);
  const pics = [];
  const svgPng = async svg => {
    const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : null;
    const w = vb ? vb.width : (+svg.getAttribute('width') || svg.getBoundingClientRect().width || 800), h = vb ? vb.height : (+svg.getAttribute('height') || svg.getBoundingClientRect().height || 400);
    const cl = svg.cloneNode(true); cl.setAttribute('xmlns', 'http://www.w3.org/2000/svg'); cl.setAttribute('width', w); cl.setAttribute('height', h);
    cl.querySelectorAll('[style*="var("]').forEach(el => el.removeAttribute('style'));
    const src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(cl).replace(/var\(--[^,)]+,\s*([^)]+)\)/g, '$1').replace(/var\(--[^)]+\)/g, '#1b2230'));
    const img = new Image(); await new Promise(res => { img.onload = res; img.onerror = res; img.src = src; });
    const k = 2, cv = document.createElement('canvas'); cv.width = Math.round(w * k); cv.height = Math.round(h * k);
    const cx = cv.getContext('2d'); cx.fillStyle = '#ffffff'; cx.fillRect(0, 0, cv.width, cv.height); try { cx.drawImage(img, 0, 0, cv.width, cv.height); } catch (e) { /* */ }
    const b64 = cv.toDataURL('image/png').split(',')[1], bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    const name = `Pictures/r${pics.length + 1}.png`; pics.push({ name, data: u });
    const wcm = Math.min(17, w / 96 * 2.54 * 0.85), hcm = wcm * h / w;
    return `<draw:frame draw:name="r${pics.length}" text:anchor-type="as-char" svg:width="${wcm.toFixed(2)}cm" svg:height="${hcm.toFixed(2)}cm"><draw:image xlink:href="${name}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>`;
  };
  const inline = async el => {
    let o = '';
    for (const n of el.childNodes) {
      if (n.nodeType === 3) { o += esc(n.nodeValue.replace(/\s+/g, ' ')); continue; }
      if (n.nodeType !== 1) continue;
      const t = n.tagName.toLowerCase();
      if (t === 'svg') { o += await svgPng(n); continue; }
      if (t === 'br') { o += '<text:line-break/>'; continue; }
      if (t === 'sub') { o += `<text:span text:style-name="Tsub">${await inline(n)}</text:span>`; continue; }
      if (t === 'sup') { o += `<text:span text:style-name="Tsup">${await inline(n)}</text:span>`; continue; }
      if (t === 'b' || t === 'strong' || t === 'th') { o += `<text:span text:style-name="Tb">${await inline(n)}</text:span>`; continue; }
      if (n.classList && (n.classList.contains('ok') || n.classList.contains('fail') || n.classList.contains('warn'))) { o += `<text:span text:style-name="${n.classList.contains('ok') ? 'Tok' : n.classList.contains('fail') ? 'Tfail' : 'Twarn'}">${await inline(n)}</text:span>`; continue; }
      if (n.classList && n.classList.contains('r')) { o += `<text:tab/>${await inline(n)}`; continue; }
      o += await inline(n);
    }
    return o;
  };
  let body = `<text:p text:style-name="Title">${esc(title || 'Raport obliczeń')}</text:p>`;
  const block = async el => {
    for (const n of el.childNodes) {
      if (n.nodeType === 3) { if (n.nodeValue.trim()) body += `<text:p text:style-name="Body">${esc(n.nodeValue.trim())}</text:p>`; continue; }      // tekst wpisany wprost (raport własny)
      if (n.nodeType !== 1) continue;
      const t = n.tagName.toLowerCase();
      if (t === 'br') continue;
      if (/^h[1-4]$/.test(t)) { body += `<text:h text:style-name="H${t[1]}" text:outline-level="${+t[1] > 1 ? +t[1] - 1 : 1}">${await inline(n)}</text:h>`; continue; }
      if (t === 'table') {
        if (n.classList.contains('pwrap')) { const tb = n.querySelector('td.pbody'); if (tb) await block(tb); continue; }
        const rows = [...n.querySelectorAll('tr')]; if (!rows.length) continue; const nc = Math.max(...rows.map(r => [...r.children].reduce((a, c) => a + (+c.getAttribute('colspan') || 1), 0)));
        body += `<table:table table:style-name="Tab"><table:table-column table:number-columns-repeated="${nc}"/>`;
        for (const r of rows) { body += '<table:table-row>'; for (const c of r.children) { const cs = +c.getAttribute('colspan') || 1; body += `<table:table-cell table:style-name="Cell" office:value-type="string"${cs > 1 ? ` table:number-columns-spanned="${cs}"` : ''}><text:p text:style-name="${c.tagName === 'TH' ? 'Th' : 'Td'}">${await inline(c)}</text:p></table:table-cell>`; for (let k = 1; k < cs; k++) body += '<table:covered-table-cell/>'; } body += '</table:table-row>'; }
        body += '</table:table>'; continue;
      }
      if (t === 'div' && (n.classList.contains('fig') || n.classList.contains('tscroll'))) { if (n.querySelector('table') && !n.querySelector('svg')) { await block(n); continue; } body += `<text:p text:style-name="Fig">${await inline(n)}</text:p>`; continue; }
      if (t === 'ul' || t === 'ol') { for (const li of n.children) body += `<text:p text:style-name="Li">• ${await inline(li)}</text:p>`; continue; }
      if (t === 'div' && n.children.length && [...n.children].some(c => /^(h[1-4]|table|div|p|ul|ol)$/i.test(c.tagName)) && !n.classList.contains('eq')) { await block(n); continue; }
      const st = n.classList.contains('eq') ? 'Eq' : n.classList.contains('note') ? 'Note' : n.classList.contains('verdict') ? 'Verdict' : 'Body';
      const tx = await inline(n); if (tx.trim()) body += `<text:p text:style-name="${st}">${tx}</text:p>`;
    }
  };
  try { await block(host); } finally { host.remove(); }
  const NS = 'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:version="1.2"';
  const ps = (n, o) => `<style:style style:name="${n}" style:family="paragraph"${o.parent ? ` style:parent-style-name="${o.parent}"` : ''}><style:paragraph-properties fo:margin-top="${o.mt || '0cm'}" fo:margin-bottom="${o.mb || '0.1cm'}"${o.ml ? ` fo:margin-left="${o.ml}"` : ''}${o.tab ? '><style:tab-stops><style:tab-stop style:position="16.5cm" style:type="right"/></style:tab-stops></style:paragraph-properties>' : '/>'}<style:text-properties fo:font-size="${o.fs || '10pt'}"${o.b ? ' fo:font-weight="bold"' : ''}${o.c ? ` fo:color="${o.c}"` : ''}${o.it ? ' fo:font-style="italic"' : ''}/></style:style>`;
  const styles = `<?xml version="1.0" encoding="UTF-8"?><office:document-styles ${NS}><office:styles><style:default-style style:family="paragraph"><style:text-properties style:font-name="Calibri" fo:font-family="Calibri, Arial, sans-serif" fo:font-size="10pt" fo:language="pl" fo:country="PL"/></style:default-style></office:styles><office:automatic-styles><style:page-layout style:name="PL"><style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="1.8cm" fo:margin-bottom="1.8cm" fo:margin-left="2cm" fo:margin-right="1.8cm"/></style:page-layout></office:automatic-styles><office:master-styles><style:master-page style:name="Standard" style:page-layout-name="PL"/></office:master-styles></office:document-styles>`;
  const content = `<?xml version="1.0" encoding="UTF-8"?><office:document-content ${NS}><office:automatic-styles>` +
    ps('Title', { fs: '16pt', b: true, mb: '0.3cm' }) + ps('H1', { fs: '13pt', b: true, mt: '0.4cm', mb: '0.15cm', c: '#1d3f78' }) + ps('H2', { fs: '13pt', b: true, mt: '0.4cm', mb: '0.15cm', c: '#1d3f78' }) + ps('H3', { fs: '11pt', b: true, mt: '0.25cm', mb: '0.1cm' }) + ps('H4', { fs: '10pt', b: true, mt: '0.2cm' }) +
    ps('Body', {}) + ps('Eq', { ml: '0.4cm', tab: true }) + ps('Note', { fs: '9pt', it: true, c: '#4a5466' }) + ps('Verdict', { fs: '11pt', b: true, mt: '0.3cm' }) + ps('Li', { ml: '0.4cm' }) + ps('Fig', { mt: '0.2cm', mb: '0.2cm' }) + ps('Td', { fs: '9pt', mb: '0cm' }) + ps('Th', { fs: '9pt', b: true, mb: '0cm' }) +
    `<style:style style:name="Tsub" style:family="text"><style:text-properties style:text-position="sub 58%"/></style:style><style:style style:name="Tsup" style:family="text"><style:text-properties style:text-position="super 58%"/></style:style><style:style style:name="Tb" style:family="text"><style:text-properties fo:font-weight="bold"/></style:style>` +
    `<style:style style:name="Tok" style:family="text"><style:text-properties fo:color="#1d7f3c" fo:font-weight="bold"/></style:style><style:style style:name="Tfail" style:family="text"><style:text-properties fo:color="#c0262d" fo:font-weight="bold"/></style:style><style:style style:name="Twarn" style:family="text"><style:text-properties fo:color="#a35d00" fo:font-weight="bold"/></style:style>` +
    `<style:style style:name="Tab" style:family="table"><style:table-properties style:width="17cm" table:align="left" fo:margin-top="0.15cm" fo:margin-bottom="0.15cm"/></style:style><style:style style:name="Cell" style:family="table-cell"><style:table-cell-properties fo:padding="0.05cm" fo:border="0.5pt solid #9aa3b0"/></style:style>` +
    `</office:automatic-styles><office:body><office:text>${body}</office:text></office:body></office:document-content>`;
  const manifest = `<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text" manifest:version="1.2"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>${pics.map(p => `<manifest:file-entry manifest:full-path="${p.name}" manifest:media-type="image/png"/>`).join('')}</manifest:manifest>`;
  const enc = new TextEncoder();
  return WR.zip([{ name: 'mimetype', data: enc.encode('application/vnd.oasis.opendocument.text') }, { name: 'META-INF/manifest.xml', data: enc.encode(manifest) }, { name: 'styles.xml', data: enc.encode(styles) }, { name: 'content.xml', data: enc.encode(content) }, ...pics]);
};
// ZIP (metoda „stored”, CRC-32) – wystarcza dla OpenDocument
WR.zip = function (files) {
  const T = WR._crcT || (WR._crcT = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })());
  const crc = u => { let c = 0xFFFFFFFF; for (let i = 0; i < u.length; i++) c = T[(c ^ u[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  const enc = new TextEncoder(), parts = [], cen = []; let off = 0;
  const d = new Date(), dt = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate(), tm = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
  files.forEach(f => {
    const nm = enc.encode(f.name), c = crc(f.data), sz = f.data.length;
    const lh = new DataView(new ArrayBuffer(30)); lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true); lh.setUint16(10, tm, true); lh.setUint16(12, dt, true); lh.setUint32(14, c, true); lh.setUint32(18, sz, true); lh.setUint32(22, sz, true); lh.setUint16(26, nm.length, true); lh.setUint16(28, 0, true);
    parts.push(new Uint8Array(lh.buffer), nm, f.data);
    const ch = new DataView(new ArrayBuffer(46)); ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true); ch.setUint16(12, tm, true); ch.setUint16(14, dt, true); ch.setUint32(16, c, true); ch.setUint32(20, sz, true); ch.setUint32(24, sz, true); ch.setUint16(28, nm.length, true); ch.setUint32(42, off, true);
    cen.push(new Uint8Array(ch.buffer), nm);
    off += 30 + nm.length + sz;
  });
  const cs = cen.reduce((a, u) => a + u.length, 0), ed = new DataView(new ArrayBuffer(22)); ed.setUint32(0, 0x06054b50, true); ed.setUint16(8, files.length, true); ed.setUint16(10, files.length, true); ed.setUint32(12, cs, true); ed.setUint32(16, off, true);
  const all = [...parts, ...cen, new Uint8Array(ed.buffer)], n = all.reduce((a, u) => a + u.length, 0), out = new Uint8Array(n); let p = 0; all.forEach(u => { out.set(u, p); p += u.length; });
  return out;
};
})();
