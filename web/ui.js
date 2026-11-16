/* KRÓTKI WSPORNIK ST – interfejs użytkownika (układ i obsługa jak w programie BelkaŻB) */
(function () {
'use strict';
const WS = window.WS, WD = window.WD, ND = WS.ND;
const U = window.WU = {};
const APP = 'Krótki wspornik ST', VER = '2.0.0';
let S = null;           // projekt: { schema_version, info, variants[], active, meta }
let R = null;           // wynik analizy bieżącego wariantu
let filePath = '', dirty = false;

/* ------------------------------------------------------------ narzędzia */
const $ = (s, el) => (el || document).querySelector(s);
const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
const esc = s => String(s === undefined || s === null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = (v, dp) => {
  if (dp === undefined) dp = 2;
  if (v === null || v === undefined || typeof v !== 'number' || Number.isNaN(v)) return '—';
  if (!isFinite(v)) return v > 0 ? '∞' : '−∞';
  let s = (Math.abs(v) < 0.5 * Math.pow(10, -dp) ? 0 : v).toFixed(dp);
  const neg = s[0] === '-'; if (neg) s = s.slice(1);
  let [i, f] = s.split('.'); i = i.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return (neg ? '−' : '') + i + (f !== undefined ? ',' + f : '');
};
const sym = s => esc(s).replace(/_\{([^}]*)\}/g, '<sub>$1</sub>').replace(/\^\{([^}]*)\}/g, '<sup>$1</sup>')
  .replace(/_([0-9A-Za-ząćęłńóśźżθΔ]+(?:,[0-9A-Za-ząćęłńóśźż]+)*)/g, '<sub>$1</sub>');
const getP = (o, p) => p.split('.').reduce((a, k) => (a == null ? a : a[k]), o);
const setP = (o, p, v) => { const ks = p.split('.'); let a = o; for (let i = 0; i < ks.length - 1; i++) { if (a[ks[i]] === undefined || a[ks[i]] === null) a[ks[i]] = /^\d+$/.test(ks[i + 1]) ? [] : {}; a = a[ks[i]]; } a[ks[ks.length - 1]] = v; };
const parseNum = s => { if (typeof s === 'number') return s; const x = parseFloat(String(s).replace(',', '.').replace(/[\s ]/g, '')); return isFinite(x) ? x : null; };
const showNum = v => (v === '' || v === null || v === undefined) ? '' : String(+(+v).toFixed(6)).replace('.', ',');
const clone = o => JSON.parse(JSON.stringify(o));
const V = () => S.variants[S.active];
const rootOf = k => /^(info|meta)\./.test(k) ? S : V();
const getK = k => getP(rootOf(k), k);
const setK = (k, v) => setP(rootOf(k), k, v);
Object.assign(U, { $, $$, esc, fmt, sym, getP, clone });

/* ------------------------------------------------------------ projekt (zgodny z formatem .kwst programu Python) */
const DEF = ND.defaults;
function mergeDef(def, obj) {
  if (Array.isArray(def)) return Array.isArray(obj) ? obj : clone(def);
  if (def && typeof def === 'object') { const o = (obj && typeof obj === 'object' && !Array.isArray(obj)) ? obj : {}; Object.keys(def).forEach(k => { o[k] = mergeDef(def[k], o[k]); }); return o; }
  return obj === undefined ? def : obj;
}
function normVariant(v) {
  v = mergeDef(clone(DEF.variant), v || {});
  v.loads.actions = (v.loads.actions || []).map(a => mergeDef(clone(DEF.action), a));
  v.loads.combinations = (v.loads.combinations || []).map(c => mergeDef(clone(DEF.combination), c));
  const m = v.stm.manual;
  m.nodes = (m.nodes || []).map(q => mergeDef(clone(DEF.node), q)); m.members = (m.members || []).map(q => mergeDef(clone(DEF.member), q));
  m.supports = (m.supports || []).map(q => mergeDef(clone(DEF.support), q)); m.loads = (m.loads || []).map(q => mergeDef(clone(DEF.load), q));
  return v;
}
function defaultProject() {
  return { schema_version: DEF.schema_version, info: clone(DEF.info), variants: [normVariant(clone(DEF.variant))], active: 0, meta: { ticks: {}, repMode: 'full' } };
}
function normalize(p) {
  const o = { schema_version: DEF.schema_version, info: mergeDef(clone(DEF.info), p.info || {}), variants: (p.variants && p.variants.length ? p.variants : [DEF.variant]).map(normVariant),
    active: +p.active || 0, meta: Object.assign({ ticks: {}, repMode: 'full' }, p.meta || {}) };
  o.active = Math.max(0, Math.min(o.active, o.variants.length - 1));
  return o;
}
function projectJSON() {
  const project = { schema_version: S.schema_version, info: S.info, variants: S.variants, active: S.active };
  return JSON.stringify({ format: 'KROTKI_WSPORNIK_ST', program_version: VER, saved: new Date().toISOString().slice(0, 19).replace('T', ' '), project, ui: { meta: S.meta } }, null, 2);
}
function parseProject(text) {
  const o = JSON.parse(text);
  if (o && o.format === 'KROTKI_WSPORNIK_ST' && o.project) { const p = o.project; if ((+p.schema_version || 0) > DEF.schema_version) throw new Error('Plik zapisany w nowszej wersji schematu — zaktualizuj program.'); return normalize(Object.assign({}, p, { meta: o.ui && o.ui.meta })); }
  if (o && o.geometry && o.loads) return normalize({ variants: [o] });             // sam wariant (np. eksport JSON danych)
  throw new Error('To nie jest plik projektu programu Krótki wspornik ST (.kwst / .json).');
}

/* ------------------------------------------------------------ definicje pól danych */
const DBL = v => v.geometry.layout === 'double';
const LEFTOWN = v => DBL(v) && !v.geometry.left_mirror;
const MAN = v => v.stm.mode === 'manual';
const rng = (a, b, st) => { const r = []; for (let x = a; x <= b + 1e-9; x += st) r.push(+x.toFixed(3)); return r; };
const PHI = [8, 10, 12, 14, 16, 20, 25, 28, 32];
const sideFields = (sd, show) => {
  const p = `geometry.${sd === 'R' ? 'right' : 'left'}.`;
  return [
    { k: p + 'l_c', t: 'num', l: 'Wysięg wspornika l_{c}', u: 'mm', list: rng(200, 1000, 50), min: 50, show },
    { k: p + 'h_c', t: 'num', l: 'Wysokość przy licu słupa h_{c}', u: 'mm', list: rng(300, 1200, 50), min: 100, show },
    { k: p + 'h_e', t: 'num', l: 'Wysokość na końcu h_{e}', u: 'mm', list: rng(200, 1000, 50), min: 50, show },
    { k: p + 'x_slope', t: 'num', l: 'Początek skosu dolnej krawędzi x_{s}', u: 'mm', list: [0, 50, 100, 150, 200, 250, 300], min: 0, show },
    { k: p + 'a_c', t: 'num', l: 'Położenie obciążenia a_{c} (od lica)', u: 'mm', list: rng(100, 800, 25), min: 1, show },
  ];
};
const plateFields = (sd, show) => {
  const p = `geometry.${sd === 'R' ? 'right' : 'left'}.plate.`;
  return [
    { k: p + 'kind', t: 'sel', l: 'Rodzaj oparcia', o: [['steel_plate', 'płyta stalowa'], ['elastomer', 'łożysko elastomerowe'], ['direct', 'oparcie bezpośrednie']], show },
    { k: p + 'length', t: 'num', l: 'Długość płyty a_{p} (wzdłuż wysięgu)', u: 'mm', list: [60, 80, 100, 120, 150, 180, 200, 250, 300], min: 10, show },
    { k: p + 'width', t: 'num', l: 'Szerokość płyty b_{p}', u: 'mm', list: [100, 150, 200, 250, 300, 350, 400, 500], min: 10, show },
    { k: p + 'thickness', t: 'num', l: 'Grubość t_{p}', u: 'mm', list: [0, 10, 15, 20, 25, 30, 40], min: 0, show },
    { k: p + 'offset', t: 'num', l: 'Przesunięcie środka płyty względem a_{c}', u: 'mm', list: [-50, -25, 0, 25, 50], show },
  ];
};
const GEO_HINT = () => {
  if (!R || !R.stm || !R.governing || !R.stm[R.governing]) return '';
  const sm = R.stm[R.governing].sides.R; if (!sm) return '';
  const s = sm.state, p = sm.params;
  return `Model J.3 (kombinacja ${esc(R.governing)}): ξ<sub>A</sub> = ${fmt(p.xi_A, 0)} mm, z<sub>0</sub> = ${fmt(s.z0, 0)} mm, tan θ = ${fmt(s.tan_theta, 2)} ${s.tan_theta < 1 - 1e-9 || s.tan_theta > 2.5 + 1e-9 ? '<b style="color:var(--fail)">poza zakresem 1,0–2,5</b>' : '(zakres J.3(1): 1,0–2,5)'}; x<sub>c</sub> = ${fmt(s.x_c, 0)} mm.`;
};
const STEEL_OPTS = () => Object.keys(ND.steelGrades).map(k => [k, `${k} – f_yk = ${ND.steelGrades[k][0]} MPa, klasa ${ND.steelGrades[k][1]}`]);
const EXP_OPTS = () => Object.keys(ND.expGroup).map(k => [k, k]);
const CAT_OPTS = () => Object.entries(WS.CATEGORIES).map(([k, v]) => [k, v]);
const GROUPS = [
  { id: 'geo', title: 'Geometria wspornika', items: [
    { k: 'geometry.layout', t: 'sel', l: 'Układ', o: [['single', 'wspornik jednostronny'], ['double', 'wsporniki dwustronne']], re: true },
    { k: 'geometry.construction', t: 'sel', l: 'Wykonanie', o: [['monolithic', 'monolityczne'], ['precast', 'oparcie prefabrykatu']], re: true },
    { k: 'geometry.b', t: 'num', l: 'Szerokość wspornika b', u: 'mm', list: [200, 250, 300, 350, 400, 450, 500, 600], min: 50 },
    { t: 'sub', l: 'Wspornik prawy', show: DBL },
    ...sideFields('R'),
    { t: 'hint', keep: true, h: GEO_HINT },
    { k: 'geometry.left_mirror', t: 'chk', l: 'Lewy wspornik – lustrzane odbicie prawego', show: DBL, re: true },
    { t: 'sub', l: 'Wspornik lewy', show: LEFTOWN },
    ...sideFields('L', LEFTOWN),
    { t: 'hint', ex: true, exT: 'Zakres modelu', h: () => 'Krótki wspornik wg zał. J.3: a<sub>c</sub> < z<sub>0</sub> i 1,0 ≤ tan θ ≤ 2,5. Wysięg obciążenia a<sub>c</sub> mierzony od lica słupa do linii działania siły pionowej. Skos dolnej krawędzi zaczyna się w odległości x<sub>s</sub> od lica (x<sub>s</sub> = 0 – skos od lica). Wymiary można też zmieniać, przeciągając niebieskie uchwyty na schemacie.' },
  ] },
  { id: 'plate', title: 'Płyta oporowa / łożysko', items: [
    ...plateFields('R'),
    { t: 'sub', l: 'Płyta – wspornik lewy', show: LEFTOWN }, ...plateFields('L', LEFTOWN),
    { t: 'sub', l: 'Połączenie prefabrykowane (10.9.5)', show: v => v.geometry.construction === 'precast' },
    { k: 'geometry.precast.support_type', t: 'sel', l: 'Rodzaj oparcia (tabl. 10.2)', o: [['concentrated', 'skupione'], ['line', 'liniowe (stropy)'], ['ribbed', 'żebrowe']], show: v => v.geometry.construction === 'precast' },
    { k: 'geometry.precast.dry_connection', t: 'chk', l: 'Połączenie „na sucho” (f_{Rd} = 0,4·f_{cd})', show: v => v.geometry.construction === 'precast', re: true },
    { k: 'geometry.precast.f_bed', t: 'num', l: 'Wytrzymałość podlewki f_{bed}', u: 'MPa', list: [0, 10, 20, 30, 40], min: 0, show: v => v.geometry.construction === 'precast' && !v.geometry.precast.dry_connection },
    { k: 'geometry.precast.restraint_considered', t: 'chk', l: 'Uwzględniono siły od więzów (skurcz, pełzanie, temperatura)', show: v => v.geometry.construction === 'precast' },
  ] },
  { id: 'col', title: 'Słup', items: [
    { k: 'geometry.column.h_col', t: 'num', l: 'Wymiar słupa w płaszczyźnie wspornika h_{col}', u: 'mm', list: [250, 300, 350, 400, 450, 500, 600, 700, 800], min: 100 },
    { k: 'geometry.column.b_col', t: 'num', l: 'Wymiar słupa prostopadle b_{col}', u: 'mm', list: [250, 300, 350, 400, 450, 500, 600, 700, 800], min: 100 },
    { k: 'geometry.column.cover', t: 'num', l: 'Otulina słupa (do strzemion)', u: 'mm', list: [20, 25, 30, 35, 40, 45, 50], min: 5 },
    { k: 'geometry.column.phi_long', t: 'num', l: 'Średnica prętów podłużnych słupa', u: 'mm', list: PHI, min: 6 },
    { k: 'geometry.column.phi_link', t: 'num', l: 'Średnica strzemion słupa', u: 'mm', list: [6, 8, 10, 12], min: 4 },
    { k: 'geometry.column.above', t: 'num', l: 'Długość słupa nad wspornikiem (rysunek)', u: 'mm', list: [200, 300, 400, 600, 800, 1000], min: 0 },
    { k: 'geometry.column.below', t: 'num', l: 'Długość słupa pod wspornikiem', u: 'mm', list: [300, 500, 700, 900, 1200, 1500], min: 0 },
    { k: 'geometry.column.N_Ed', t: 'num', l: 'Siła osiowa w słupie N_{Ed} (informacyjnie)', u: 'kN', sc: 1e3, list: [0, 500, 1000, 2000, 3000] },
    { t: 'hint', ex: true, h: () => 'Słup nie jest sprawdzany – program przekazuje reakcje modelu lokalnego wspornika (zakładka Model STM) jako dane do osobnej weryfikacji słupa i jego strefy węzłowej. Długość słupa pod wspornikiem ogranicza ramię pionowe zakotwienia prętów odgiętych w słupie.' },
  ] },
  { id: 'mat', title: 'Materiały i otulina', items: [
    { k: 'materials.concrete', t: 'sel', l: 'Klasa betonu', o: () => WS.CONCRETE_CLASSES.map(c => [c, c]) },
    { k: 'materials.steel_name', t: 'sel', l: 'Stal zbrojeniowa', o: STEEL_OPTS, re: true, onset: (v, val) => { const g = ND.steelGrades[val]; if (g) { v.materials.steel_fyk = g[0]; v.materials.steel_class = g[1]; v.materials.link_fyk = g[0]; } } },
    { k: 'materials.steel_fyk', t: 'num', l: 'Granica plastyczności f_{yk}', u: 'MPa', list: [400, 450, 500, 550, 600], min: 400, max: 600 },
    { k: 'materials.steel_class', t: 'sel', l: 'Klasa ciągliwości (zał. C)', o: [['A', 'A'], ['B', 'B'], ['C', 'C']] },
    { k: 'materials.link_fyk', t: 'num', l: 'f_{yk} strzemion', u: 'MPa', list: [400, 500], min: 400, max: 600 },
    { k: 'materials.d_g', t: 'num', l: 'Maks. wymiar kruszywa d_{g}', u: 'mm', list: [8, 16, 20, 22, 32], min: 4, max: 63 },
    { k: 'materials.exposure', t: 'sel', l: 'Klasa ekspozycji', o: EXP_OPTS },
    { k: 'materials.structural_class', t: 'sel', l: 'Klasa konstrukcji', o: () => ND.structClasses.map(c => [c, c]) },
    { k: 'materials.delta_c_dev', t: 'num', l: 'Odchyłka wykonawcza Δc_{dev}', u: 'mm', list: [0, 5, 10], min: 0, max: 20 },
    { k: 'materials.c_nom_user', t: 'num', l: 'Otulina nominalna c_{nom} (ręcznie)', u: 'mm', list: ['', 25, 30, 35, 40, 45, 50], opt: true, ph: () => R && R.cover ? 'auto: ' + R.cover.c_nom : 'auto' },
    { k: 'materials.design_situation', t: 'sel', l: 'Sytuacja obliczeniowa', o: [['persistent', 'trwała / przejściowa'], ['accidental', 'wyjątkowa']] },
    { t: 'hint', h: () => R && R.materials ? `f<sub>cd</sub> = ${fmt(R.materials.concrete.fcd, 2)} MPa, ν′ = ${fmt(R.materials.concrete.nu_prime, 3)}, f<sub>yd</sub> = ${fmt(R.materials.steel.fyd, 1)} MPa${R.cover ? `; c<sub>nom</sub> = ${R.cover.c_nom} mm (c<sub>min,dur</sub> = ${R.cover.c_min_dur} mm)` : ''}` : '' },
  ] },
  { id: 'loads', title: 'Obciążenia i kombinacje', items: [
    { t: 'loads' },
    { t: 'sub', l: 'Kombinacje (PN-EN 1990)' },
    { k: 'loads.combination_mode', t: 'sel', l: 'Kombinacje', o: [['auto', 'automatyczne'], ['manual', 'zdefiniowane ręcznie']], re: true },
    { k: 'loads.settings.method', t: 'sel', l: 'SGN – wzór', o: [['6.10ab', 'wzory 6.10a i 6.10b'], ['6.10', 'wzór 6.10']], show: v => v.loads.combination_mode === 'auto' },
    { k: 'loads.settings.gamma_G_sup', t: 'num', l: 'γ_{G,sup}', list: [1.35, 1.2, 1.1, 1.0], min: 1, show: v => v.loads.combination_mode === 'auto' },
    { k: 'loads.settings.gamma_G_inf', t: 'num', l: 'γ_{G,inf}', list: [1.0, 0.9], min: 0, show: v => v.loads.combination_mode === 'auto' },
    { k: 'loads.settings.gamma_Q', t: 'num', l: 'γ_{Q}', list: [1.5, 1.35, 1.3], min: 1, show: v => v.loads.combination_mode === 'auto' },
    { k: 'loads.settings.xi', t: 'num', l: 'ξ (6.10b)', list: [0.85, 0.9, 1.0], min: 0, max: 1, show: v => v.loads.combination_mode === 'auto' && v.loads.settings.method === '6.10ab' },
    { k: 'loads.settings.include_sls', t: 'chk', l: 'Kombinacja quasi-stała SGU (kontrola rys)', show: v => v.loads.combination_mode === 'auto' },
    { t: 'combos', show: v => v.loads.combination_mode === 'manual' },
    { k: 'loads.settings.H_min_enabled', t: 'chk', l: 'Minimalna siła pozioma H ≥ k·V (świadome założenie)', re: true },
    { k: 'loads.settings.H_min_ratio', t: 'num', l: 'k = H_{min}/V', list: [0.1, 0.2, 0.3], min: 0, max: 1, show: v => v.loads.settings.H_min_enabled },
    { k: 'loads.settings.H_min_source', t: 'txt', l: 'Źródło założenia', ph: 'np. wytyczne inwestora, EN 1992-1-1 J.3 (komentarz)', show: v => v.loads.settings.H_min_enabled },
    { t: 'hint', ex: true, exT: 'Znaki i wartości', h: () => 'V – w dół (+); H – od słupa (+), do słupa (−); M – przesuwa wypadkową od słupa (+); e<sub>y</sub> – mimośród poprzeczny. Wartości „charakterystyczne” są kombinowane wg PN-EN 1990; wartości „obliczeniowe” wchodzą do kombinacji bez ponownego mnożenia przez γ.' },
  ] },
  { id: 'main', title: 'Zbrojenie główne (cięgno)', items: [
    { k: 'reinforcement.main.auto', t: 'chk', l: 'Dobór automatyczny (najmniejsze A_{s} spełniające wszystkie warunki)', re: true },
    { k: 'reinforcement.main.phi', t: 'sel', num: true, l: 'Średnica φ', o: PHI.map(d => [d, 'φ' + d]), show: v => !v.reinforcement.main.auto },
    { k: 'reinforcement.main.n_per_layer', t: 'num', l: 'Liczba prętów w warstwie n', list: rng(2, 10, 1), min: 1, show: v => !v.reinforcement.main.auto },
    { k: 'reinforcement.main.layers', t: 'sel', num: true, l: 'Liczba warstw', o: [[1, '1'], [2, '2'], [3, '3']], show: v => !v.reinforcement.main.auto },
    { k: 'reinforcement.main.layer_gap', t: 'num', l: 'Odstęp warstw w świetle', u: 'mm', list: ['', 25, 30, 35, 40], opt: true, ph: 's_min', show: v => !v.reinforcement.main.auto },
    { t: 'diams', show: v => v.reinforcement.main.auto },
    { k: 'reinforcement.main.anchor_load', t: 'sel', l: 'Zakotwienie przy obciążeniu', o: [['loop', 'pętle poziome (rys. 8.1d)'], ['bend_down', 'odgięcie w dół (rys. 8.1b)'], ['welded_bar', 'przyspawany pręt poprzeczny'], ['straight', 'pręt prosty'], ['mechanical', 'mechaniczne (ETA)']], re: true },
    { k: 'reinforcement.main.anchor_column', t: 'sel', l: 'Zakotwienie w słupie', o: [['bend_down', 'odgięcie w dół w słupie'], ['straight', 'pręt prosty'], ['mechanical', 'mechaniczne (ETA)']], show: v => !DBL(v), re: true },
    { k: 'reinforcement.main.welded_bar_phi', t: 'num', l: 'Średnica pręta przyspawanego φ_{t}', u: 'mm', list: ['', 14, 16, 20, 25, 28, 32], opt: true, ph: '= φ', show: v => v.reinforcement.main.anchor_load === 'welded_bar' },
    { k: 'reinforcement.main.mandrel_load', t: 'num', l: 'Średnica trzpienia przy obciążeniu φ_{m}', u: 'mm', list: ['', 80, 100, 125, 140, 160, 200, 250], opt: true, ph: 'tabl. 8.1N', show: v => v.reinforcement.main.anchor_load === 'bend_down' },
    { k: 'reinforcement.main.front_leg', t: 'num', l: 'Ramię pionowe na końcu wspornika', u: 'mm', list: ['', 100, 150, 200, 250], opt: true, ph: 'auto', show: v => v.reinforcement.main.anchor_load === 'bend_down' },
    { k: 'reinforcement.main.mandrel_column', t: 'num', l: 'Średnica trzpienia w słupie φ_{m}', u: 'mm', list: ['', 80, 100, 125, 140, 160, 200, 250], opt: true, ph: 'tabl. 8.1N', show: v => !DBL(v) && v.reinforcement.main.anchor_column === 'bend_down' },
    { k: 'reinforcement.main.column_leg', t: 'num', l: 'Ramię pionowe w słupie', u: 'mm', list: ['', 200, 300, 400, 500, 600, 800], opt: true, ph: 'auto', show: v => !DBL(v) && v.reinforcement.main.anchor_column === 'bend_down' },
    { k: 'reinforcement.main.bond', t: 'sel', l: 'Warunki przyczepności (rys. 8.2)', o: [['poor', 'słabe (η₁ = 0,7) – pręty górne'], ['good', 'dobre (η₁ = 1,0)']] },
    { k: 'reinforcement.main.alpha3_mode', t: 'sel', l: 'Współczynnik α₃', o: [['conservative', 'α₃ = 1,0 (konserwatywnie)'], ['computed', 'obliczany ze strzemion']], re: true },
    { k: 'reinforcement.main.K_alpha3', t: 'num', l: 'K (rys. 8.4)', list: [0, 0.05, 0.1], min: 0, max: 0.1, show: v => v.reinforcement.main.alpha3_mode === 'computed' },
    { t: 'hint', keep: true, h: () => R && R.main ? `Przyjęto: <b>${esc(R.main.desc())}</b>, A<sub>s</sub> = ${fmt(R.main.As, 0)} mm², kotwienie: ${esc(WS.ANCHOR_LABEL[R.main_input.anchor_load] || '')}, c<sub>t</sub> = ${fmt(R.main.c_t, 1)} mm.` : '' },
  ] },
  { id: 'links', title: 'Strzemiona', items: [
    { k: 'reinforcement.links.auto', t: 'chk', l: 'Dobór automatyczny (J.3(2), J.3(3), rozłupywanie 6.5.3(3))', re: true },
    { k: 'reinforcement.links.h_phi', t: 'sel', num: true, l: 'Strzemiona poziome – φ', o: WS.LINK_DIAMETERS.map(d => [d, 'φ' + d]), show: v => !v.reinforcement.links.auto },
    { k: 'reinforcement.links.h_count', t: 'num', l: 'Liczba strzemion poziomych', list: rng(0, 8, 1), min: 0, show: v => !v.reinforcement.links.auto },
    { k: 'reinforcement.links.h_zone', t: 'num', l: 'Strefa strzemion poniżej cięgna', u: 'mm', list: ['', 200, 250, 300, 350, 400], opt: true, ph: '2/3·d', show: v => !v.reinforcement.links.auto },
    { k: 'reinforcement.links.v_phi', t: 'sel', num: true, l: 'Strzemiona pionowe – φ', o: WS.LINK_DIAMETERS.map(d => [d, 'φ' + d]), show: v => !v.reinforcement.links.auto },
    { k: 'reinforcement.links.v_count', t: 'num', l: 'Liczba strzemion pionowych', list: rng(0, 6, 1), min: 0, show: v => !v.reinforcement.links.auto },
    { k: 'reinforcement.links.i_phi', t: 'sel', num: true, l: 'Pręty ukośne w narożu – φ', o: WS.LINK_DIAMETERS.map(d => [d, 'φ' + d]) },
    { k: 'reinforcement.links.i_count', t: 'num', l: 'Liczba prętów ukośnych (J.3(5))', list: [0, 1, 2, 3], min: 0 },
    { k: 'reinforcement.links.min_constructive_h', t: 'num', l: 'Min. liczba strzemion poziomych (zalecenie)', list: [0, 1, 2, 3], min: 0, show: v => v.reinforcement.links.auto },
    { t: 'hint', keep: true, h: () => R && R.links ? Object.entries(R.links).map(([sd, ll]) => `${DBL(V()) ? (sd === 'R' ? 'P: ' : 'L: ') : ''}<b>${esc(ll.desc_h())}</b>; ${esc(ll.desc_v())}`).join('<br>') : '' },
  ] },
  { id: 'stm', title: 'Model STM', items: [
    { k: 'stm.mode', t: 'sel', l: 'Model', o: [['auto', 'automatyczny (zał. J.3, rys. J.5)'], ['manual', 'zdefiniowany ręcznie']], re: true },
    { k: 'stm.lever_arm', t: 'sel', l: 'Wysokość strefy ściskanej x_{c}', o: [['optimal', 'optymalne pole naprężeń'], ['node_limit', 'z warunku nośności węzła B'], ['user', 'podana ręcznie']], show: v => !MAN(v), re: true },
    { k: 'geometry.right.x_c_user', t: 'num', l: 'x_{c} (ręcznie)', u: 'mm', list: ['', 50, 75, 100, 125, 150, 200], opt: true, ph: 'lub z0', show: v => !MAN(v) && v.stm.lever_arm === 'user' },
    { k: 'geometry.right.z0_user', t: 'num', l: 'z_{0} (ręcznie)', u: 'mm', list: ['', 300, 350, 400, 450, 500], opt: true, ph: '—', show: v => !MAN(v) && v.stm.lever_arm === 'user' },
    { k: 'stm.node_b_position', t: 'sel', l: 'Węzeł B', o: [['in_column', 'w słupie (ξ_B = −a_B/2)'], ['face', 'na licu słupa (rys. J.5)']], show: v => !MAN(v) },
    { k: 'stm.strut_limit', t: 'sel', l: 'Nośność krzyżulca', o: [['6.56', '0,6·ν′·f_cd – strefa zarysowana (6.56)'], ['6.55', 'f_cd – bez rozciągania poprzecznego (6.55)']] },
    { k: 'stm.include_aH', t: 'chk', l: 'Uwzględnij ramię a_{H} siły poziomej' },
    { k: 'stm.neglect_favourable_H', t: 'chk', l: 'Pomijaj korzystną siłę H (skierowaną do słupa)' },
    { k: 'geometry.right.d_user', t: 'num', l: 'Wysokość użyteczna d (ręcznie)', u: 'mm', list: [''], opt: true, ph: 'auto', show: v => !MAN(v) },
    { k: 'geometry.right.a_H_user', t: 'num', l: 'Ramię a_{H} (ręcznie)', u: 'mm', list: [''], opt: true, ph: 'c_t + t_p', show: v => !MAN(v) },
    { k: 'stm.node_10pct', t: 'chk', l: 'Zwiększenie σ_{Rd,max} węzłów o 10% (6.5.4(5))', re: true },
    { k: 'stm.node_10pct_justification', t: 'txt', l: 'Uzasadnienie', ph: 'wymagane – bez uzasadnienia zwiększenie nie jest stosowane', show: v => v.stm.node_10pct },
    { t: 'manual', show: MAN },
  ] },
  { id: 'norm', title: 'Parametry normowe', items: [
    { k: 'normative.edition', t: 'sel', l: 'Podstawa normowa', o: () => Object.values(ND.editions).map(e => [e.id, e.title + (e.implemented ? '' : ' – niezaimplementowana')]) },
    { k: 'normative.ndp_confirmed', t: 'chk', l: 'Potwierdzam zgodność parametrów NDP z Załącznikiem Krajowym' },
    { k: 'normative.apply_engineering_recommendations', t: 'chk', l: 'Stosuj zalecenia inżynierskie (np. h ≥ 0,5·h_{c} pod krawędzią płyty)' },
    { t: 'html', h: () => `<div class="lhead"><span>Tabela parametrów: wartości, źródła, statusy</span><button class="addb" data-ndp="1">Parametry NDP…</button></div>` },
    { t: 'hint', keep: true, h: v => V().normative.ndp_confirmed ? '' : 'Bez potwierdzenia NDP wynik ma charakter warunkowy („SPEŁNIONO WARUNKOWO”) – program nie formułuje pozytywnego wniosku ogólnego.' },
  ] },
  { id: 'proj', title: 'Dane projektu', closed: true, items: [
    { k: 'info.number', t: 'txt', l: 'Numer projektu' }, { k: 'info.object', t: 'txt', l: 'Obiekt' }, { k: 'info.element', t: 'txt', l: 'Element' },
    { k: 'info.designer', t: 'txt', l: 'Projektant' }, { k: 'info.checker', t: 'txt', l: 'Sprawdzający' }, { k: 'info.notes', t: 'txt', l: 'Uwagi' },
  ] },
];
U.GROUPS = GROUPS;

/* ------------------------------------------------------------ pola formularza */
function optionsOf(f) { return typeof f.o === 'function' ? f.o(V()) : f.o; }
const exDetails = (ex, t) => ex ? `<details class="exh"><summary>${t || 'Objaśnienie'}</summary><div>${ex}</div></details>` : '';
function hintHTML(f) { const h = f.h(V()); if (!h) return ''; return f.ex ? exDetails(h, f.exT) : h; }
function fieldsHTML(items, gid) {
  let html = '';
  items.forEach((f, i) => {
    if (f.show && !f.show(V())) return;
    const id = `f_${gid}_${i}`;
    if (f.t === 'hint') { const h = hintHTML(f); html += `<div class="hint${f.keep ? ' keep info' : ''}" data-hint="${gid}_${i}"${h ? '' : ' style="display:none"'}>${h}</div>`; return; }
    if (f.t === 'sub') { html += `<div class="lsub">${sym(f.l)}</div>`; return; }
    if (f.t === 'html') { html += f.h(V()); return; }
    if (f.t === 'sel') {
      const v = getK(f.k), opts = optionsOf(f);
      html += `<div class="row"><label for="${id}">${sym(f.l)}</label><select id="${id}" data-k="${f.k}" data-num="${f.num ? 1 : ''}" data-re="${f.re ? 1 : ''}" data-gi="${gid}_${i}">${opts.map(([val, lab]) => `<option value="${esc(val)}" ${String(val) === String(v) ? 'selected' : ''}>${esc(lab)}</option>`).join('')}</select><span></span></div>`;
    } else if (f.t === 'num') {
      const raw = getK(f.k), v = raw === null || raw === undefined || raw === '' ? '' : f.sc ? raw / f.sc : raw;
      const ph = typeof f.ph === 'function' ? f.ph(V()) : f.ph;
      html += `<div class="row"><label for="${id}">${sym(f.l)}</label><div class="combo"><input id="${id}" data-k="${f.k}" value="${esc(showNum(v))}" ${ph ? `placeholder="${esc(ph)}"` : ''} data-opt="${f.opt ? 1 : ''}" data-sc="${f.sc || ''}" data-int="${/count|n_per_layer|i_count|min_constructive/.test(f.k) ? 1 : ''}" data-min="${f.min !== undefined ? f.min : ''}" data-max="${f.max !== undefined ? f.max : ''}" data-re="${f.re ? 1 : ''}" data-ph="${typeof f.ph === 'function' ? gid + '_' + i : ''}" autocomplete="off" spellcheck="false"><button tabindex="-1" data-list="${esc(JSON.stringify(f.list || []))}" aria-label="lista">▾</button></div><span class="unit">${esc(f.u || '')}</span></div>`;
    } else if (f.t === 'txt') {
      html += `<div class="row wide"><label for="${id}">${sym(f.l)}</label><input class="txt" id="${id}" data-kt="${f.k}" value="${esc(getK(f.k) || '')}" placeholder="${esc(f.ph || '')}" spellcheck="false" autocomplete="off"></div>`;
    } else if (f.t === 'chk') {
      html += `<label class="chk"><input type="checkbox" data-k="${f.k}" data-re="${f.re ? 1 : ''}" ${getK(f.k) ? 'checked' : ''}><span>${sym(f.l)}</span></label>`;
    } else if (f.t === 'loads') html += loadsHTML();
    else if (f.t === 'combos') html += combosEditHTML();
    else if (f.t === 'diams') html += diamsHTML();
    else if (f.t === 'manual') html += manualHTML();
  });
  return html;
}
/* obciążenia – lista oddziaływań */
const NAT = [['characteristic', 'charakterystyczne'], ['design', 'obliczeniowe']];
function loadsHTML() {
  const v = V(), dbl = DBL(v);
  let h = `<div class="lhead"><span>Oddziaływania (${v.loads.actions.length})</span><button class="addb" data-addact="1">+ dodaj</button></div>`;
  v.loads.actions.forEach((a, i) => {
    const opt = (o, cur) => o.map(([k, l]) => `<option value="${esc(k)}" ${k === cur ? 'selected' : ''}>${esc(l)}</option>`).join('');
    h += `<div class="litem" style="border-left-color:${a.category === 'G' ? '#4a5466' : a.category === 'A' ? '#c0262d' : '#1d5bb8'}">
      <div class="lrow"><span class="lid">${i + 1}</span><input class="txt lname" data-la="${i}.name" value="${esc(a.name)}" spellcheck="false">${dbl ? `<select data-la="${i}.side" style="flex:0 0 74px">${opt([['R', 'prawy'], ['L', 'lewy']], a.side)}</select>` : ''}<button class="del" data-delact="${i}" title="Usuń oddziaływanie" aria-label="Usuń">×</button></div>
      <div class="lrow"><select data-la="${i}.category">${opt(CAT_OPTS(), a.category)}</select><select data-la="${i}.nature" style="flex:0 0 132px">${opt(NAT, a.nature)}</select></div>
      <div class="lrow">V <input class="txt" data-la="${i}.V" data-sc="1000" value="${showNum(a.V / 1e3)}"><span class="u">kN</span>H <input class="txt" data-la="${i}.H" data-sc="1000" value="${showNum(a.H / 1e3)}"><span class="u">kN</span>M <input class="txt sm" data-la="${i}.M" data-sc="1000000" value="${showNum(a.M / 1e6)}"><span class="u">kNm</span>e<sub>y</sub> <input class="txt sm" data-la="${i}.e_y" value="${showNum(a.e_y)}"><span class="u">mm</span></div>
      ${a.note ? `<div class="lrow"><span class="hint" style="margin:0">${esc(a.note)}</span></div>` : ''}</div>`;
  });
  return h;
}
function combosEditHTML() {
  const v = V(), acts = v.loads.actions;
  let h = `<div class="lhead"><span>Kombinacje ręczne (${v.loads.combinations.length})</span><button class="addb" data-addcmb="1">+ dodaj</button></div>`;
  v.loads.combinations.forEach((c, i) => {
    h += `<div class="litem"><div class="lrow"><input class="txt lname" data-lc="${i}.name" value="${esc(c.name)}"><select data-lc="${i}.kind" style="flex:0 0 170px">${Object.entries(WS.COMB_KINDS).map(([k, l]) => `<option value="${k}" ${k === c.kind ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select><button class="del" data-delcmb="${i}">×</button></div>
      <div class="lrow">${acts.map(a => `${esc(a.name)} × <input class="txt sm" data-lf="${i}" data-an="${esc(a.name)}" value="${showNum(c.factors[a.name] !== undefined ? c.factors[a.name] : 0)}">`).join(' ')}</div></div>`;
  });
  return h;
}
function diamsHTML() {
  const al = V().reinforcement.allowed_diameters;
  return `<div class="row wide"><label>Dozwolone średnice (dobór)</label><div class="dchips">${PHI.filter(d => d >= 10).map(d => `<label class="chk" style="display:inline-flex;margin-right:10px"><input type="checkbox" data-diam="${d}" ${al.includes(d) ? 'checked' : ''}><span>φ${d}</span></label>`).join('')}</div></div>`;
}
function manualHTML() {
  const m = V().stm.manual;
  const tbl = (key, cols, rows) => `<div class="lhead"><span>${{ nodes: 'Węzły', members: 'Pręty', supports: 'Podpory', loads: 'Obciążenia węzłowe (obliczeniowe)' }[key]} (${rows.length})</span><button class="addb" data-madd="${key}">+ dodaj</button></div>` +
    rows.map((r, i) => `<div class="lrow">${cols.map(([f, lab, ty, sc, w]) => ty === 'sel' ? `${lab} <select data-mk="${key}.${i}.${f}" style="flex:0 0 ${w || 80}px">${sc.map(([k, l]) => `<option value="${k}" ${String(r[f]) === String(k) ? 'selected' : ''}>${l}</option>`).join('')}</select>`
      : ty === 'chk' ? `<label class="chk" style="display:inline-flex">${lab}<input type="checkbox" data-mk="${key}.${i}.${f}" ${r[f] ? 'checked' : ''}></label>`
      : `${lab} <input class="txt${ty === 's' ? '' : ' sm'}" data-mk="${key}.${i}.${f}" data-sc="${sc || ''}" data-mt="${ty}" value="${esc(ty === 's' ? r[f] : showNum(sc ? r[f] / sc : r[f]))}" style="${w ? `width:${w}px` : ''}">`).join(' ')}<button class="del sm" data-mdel="${key}.${i}">×</button></div>`).join('');
  return `<div class="hint keep">Model ręczny: współrzędne w mm (oś y w górę, 0 = górna krawędź wspornika, oś słupa x = 0); obciążenia węzłowe są wartościami obliczeniowymi. <button class="addb" data-mfrom="1">Wczytaj z modelu automatycznego</button></div>` +
    tbl('nodes', [['id', '', 's', '', 44], ['x', 'x', 'n'], ['y', 'y', 'n']], m.nodes) +
    tbl('members', [['id', '', 's', '', 40], ['n1', '', 's', '', 34], ['n2', '–', 's', '', 34], ['kind', '', 'sel', [['strut', 'krzyżulec'], ['tie', 'cięgno']], 86], ['width', 'w', 'n'], ['thickness', 't', 'n'], ['As', 'A_s', 'n']], m.members) +
    tbl('supports', [['node', 'węzeł', 's', '', 40], ['ux', 'u_x', 'chk'], ['uy', 'u_y', 'chk'], ['bearing_width', 'szer.', 'n']], m.supports) +
    tbl('loads', [['node', 'węzeł', 's', '', 40], ['Fx', 'F_x', 'n', 1e3], ['Fy', 'F_y', 'n', 1e3]], m.loads) + '<div class="hint">F w kN (F<sub>y</sub> < 0 – w dół); w, t, szer. w mm; A<sub>s</sub> w mm².</div>';
}
function renderInputs() {
  renderAutoBar();
  const host = $('#inputs'), pane = $('#p-data .dleft'), st = pane ? pane.scrollTop : 0;
  const openState = {}; $$('details.grp', host).forEach(d => openState[d.dataset.id] = d.open);
  host.innerHTML = GROUPS.map(G => { const open = openState[G.id] !== undefined ? openState[G.id] : !G.closed; return `<details class="grp" data-id="${G.id}" ${open ? 'open' : ''}><summary>${esc(G.title)}</summary><div class="fields">${fieldsHTML(G.items, G.id)}</div></details>`; }).join('');
  if (pane) pane.scrollTop = st;
  bindInputs(host);
}
function refreshHints() {
  GROUPS.forEach(G => G.items.forEach((f, i) => {
    if (f.t !== 'hint') return;
    const el = $(`[data-hint="${G.id}_${i}"]`); if (!el) return;
    const open = !!el.querySelector('details.exh[open]'), h = hintHTML(f); el.innerHTML = h; el.style.display = h ? '' : 'none';
    if (open) { const d = el.querySelector('details.exh'); if (d) d.open = true; }
  }));
  $$('#inputs [data-ph]').forEach(el => { if (!el.dataset.ph) return; const [gid, ii] = [el.dataset.ph.split('_')[0], +el.dataset.ph.split('_')[1]]; const G = GROUPS.find(q => q.id === gid), f = G && G.items[ii]; if (f && typeof f.ph === 'function') el.placeholder = f.ph(V()); });
}
const fieldDef = el => { const gi = el.dataset.gi; if (!gi) return null; const [g, i] = gi.split('_'); const G = GROUPS.find(q => q.id === g); return G ? G.items[+i] : null; };
function bindInputs(host) {
  $$('select[data-k]', host).forEach(el => el.addEventListener('change', () => {
    let v = el.value; if (el.dataset.num) v = parseNum(v);
    setK(el.dataset.k, v); const f = fieldDef(el); if (f && f.onset) f.onset(V(), v);
    changed(true);
  }));
  $$('input[type=checkbox][data-k]', host).forEach(el => el.addEventListener('change', () => { setK(el.dataset.k, el.checked); changed(!!el.dataset.re || true); }));
  $$('[data-kt]', host).forEach(el => el.addEventListener('input', () => { setK(el.dataset.kt, el.value); changed(false); }));
  $$('.combo input', host).forEach(el => {
    el.addEventListener('input', () => numInput(el, false));
    el.addEventListener('change', () => numInput(el, true));
    el.addEventListener('keydown', e => { if (e.key === 'ArrowDown' && e.altKey) { openList(el.nextElementSibling); e.preventDefault(); } });
  });
  $$('.combo button', host).forEach(b => b.addEventListener('mousedown', e => { e.preventDefault(); openList(b); }));
  // oddziaływania
  $$('[data-la]', host).forEach(el => {
    const [i, fld] = el.dataset.la.split('.'), a = () => V().loads.actions[+i];
    if (el.tagName === 'SELECT') { el.addEventListener('change', () => { a()[fld] = el.value; changed(true); }); return; }
    el.addEventListener('input', () => {
      if (fld === 'name') { const old = a().name; a().name = el.value; V().loads.combinations.forEach(c => { if (old in c.factors) { c.factors[el.value] = c.factors[old]; delete c.factors[old]; } }); changed(false); return; }
      const raw = el.value.trim(), x = raw === '' ? 0 : parseNum(raw); el.classList.toggle('bad', x === null); if (x === null) return;
      a()[fld] = x * (+el.dataset.sc || 1); changed(false);
    });
  });
  $$('[data-addact]', host).forEach(b => b.addEventListener('click', () => { const v = V(); const a = Object.assign(clone(DEF.action), { name: 'Q' + (v.loads.actions.length + 1), category: 'Q_B', V: 100e3, note: '' }); v.loads.actions.push(a); changed(true); }));
  $$('[data-delact]', host).forEach(b => b.addEventListener('click', () => { V().loads.actions.splice(+b.dataset.delact, 1); changed(true); }));
  $$('[data-addcmb]', host).forEach(b => b.addEventListener('click', () => { const v = V(); const c = Object.assign(clone(DEF.combination), { name: 'K' + (v.loads.combinations.length + 1), factors: {} }); v.loads.actions.forEach(a => { c.factors[a.name] = a.category === 'G' ? 1.35 : 1.5; }); v.loads.combinations.push(c); changed(true); }));
  $$('[data-delcmb]', host).forEach(b => b.addEventListener('click', () => { V().loads.combinations.splice(+b.dataset.delcmb, 1); changed(true); }));
  $$('[data-lc]', host).forEach(el => { const [i, fld] = el.dataset.lc.split('.'); el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', () => { V().loads.combinations[+i][fld] = el.value; changed(el.tagName === 'SELECT'); }); });
  $$('[data-lf]', host).forEach(el => el.addEventListener('input', () => { const x = parseNum(el.value); el.classList.toggle('bad', x === null); if (x === null) return; V().loads.combinations[+el.dataset.lf].factors[el.dataset.an] = x; changed(false); }));
  $$('[data-diam]', host).forEach(el => el.addEventListener('change', () => { const d = +el.dataset.diam, a = V().reinforcement.allowed_diameters; const i = a.indexOf(d); if (el.checked && i < 0) a.push(d); if (!el.checked && i >= 0) a.splice(i, 1); a.sort((x, y) => x - y); changed(false); }));
  // model ręczny
  $$('[data-mk]', host).forEach(el => {
    const [key, i, fld] = el.dataset.mk.split('.'), row = () => V().stm.manual[key][+i];
    if (el.type === 'checkbox') { el.addEventListener('change', () => { row()[fld] = el.checked; changed(false); }); return; }
    if (el.tagName === 'SELECT') { el.addEventListener('change', () => { row()[fld] = el.value; changed(false); }); return; }
    el.addEventListener('input', () => {
      if (el.dataset.mt === 's') { row()[fld] = el.value.trim(); changed(false); return; }
      const x = parseNum(el.value); el.classList.toggle('bad', x === null); if (x === null) return; row()[fld] = x * (+el.dataset.sc || 1); changed(false);
    });
  });
  $$('[data-madd]', host).forEach(b => b.addEventListener('click', () => { const k = b.dataset.madd, m = V().stm.manual, d = { nodes: DEF.node, members: DEF.member, supports: DEF.support, loads: DEF.load }[k]; const it = clone(d); if (k === 'nodes') it.id = 'N' + (m.nodes.length + 1); if (k === 'members') it.id = 'M' + (m.members.length + 1); m[k].push(it); changed(true); }));
  $$('[data-mdel]', host).forEach(b => b.addEventListener('click', () => { const [k, i] = b.dataset.mdel.split('.'); V().stm.manual[k].splice(+i, 1); changed(true); }));
  $$('[data-mfrom]', host).forEach(b => b.addEventListener('click', () => {
    const v2 = clone(V()); v2.stm.mode = 'auto'; let r2; try { r2 = WS.analyze(v2); } catch (e) { r2 = null; }
    if (!r2 || !r2.stm[r2.governing] || !r2.stm[r2.governing].struts.length) { toast('Model automatyczny niedostępny dla obecnych danych.'); return; }
    V().stm.manual = WS.manualFromResult(r2.stm[r2.governing], V().geometry.b); changed(true); toast('Wczytano model z kombinacji ' + r2.governing + '.');
  }));
  $$('[data-ndp]', host).forEach(b => b.addEventListener('click', () => window.WV.ndpPopup()));
}
function numInput(el, final) {
  const raw = el.value.trim(), opt = !!el.dataset.opt, sc = +el.dataset.sc || 1;
  const min = el.dataset.min !== '' ? parseFloat(el.dataset.min) : null, max = el.dataset.max !== '' ? parseFloat(el.dataset.max) : null;
  if (raw === '' && opt) { el.classList.remove('bad'); setK(el.dataset.k, null); changed(final); return; }
  let v = parseNum(raw);
  const bad = v === null || (min !== null && v < min) || (max !== null && v > max) || (el.dataset.int && v !== Math.round(v));
  el.classList.toggle('bad', bad); if (bad) return;
  setK(el.dataset.k, v * sc);
  if (final) el.value = showNum(v);
  changed(final && !!el.dataset.re);
}
let popFor = null;
function openList(btn) {
  const pop = $('#pop'), inp = btn.previousElementSibling;
  if (popFor === inp && pop.style.display === 'block') { closeList(); return; }
  const list = JSON.parse(btn.dataset.list || '[]'); if (!list.length) return;
  pop.innerHTML = list.map(v => `<div data-v="${esc(String(v))}" class="${String(v) === String(parseNum(inp.value) ?? '') ? 'cur' : ''}">${v === '' ? (inp.placeholder || '—') : esc(showNum(v))}</div>`).join('');
  const r = inp.parentElement.getBoundingClientRect();
  pop.style.display = 'block'; pop.style.minWidth = r.width + 'px';
  const ph = Math.min(260, pop.scrollHeight), below = window.innerHeight - r.bottom > ph + 6;
  pop.style.left = r.left + 'px'; pop.style.top = (below ? r.bottom + 2 : r.top - ph - 2) + 'px';
  popFor = inp;
  const cur = $('.cur', pop); if (cur) cur.scrollIntoView({ block: 'center' });
  $$('div', pop).forEach(d => d.addEventListener('mousedown', e => { e.preventDefault(); inp.value = showNum(d.dataset.v); numInput(inp, true); closeList(); inp.focus(); }));
}
function closeList() { $('#pop').style.display = 'none'; popFor = null; }
document.addEventListener('mousedown', e => { if (!e.target.closest('#pop') && !e.target.closest('.combo button')) closeList(); });
window.addEventListener('resize', closeList);

/* pasek doboru nad danymi */
function renderAutoBar() {
  const el = $('#autobar'); if (!el) return;
  const v = V(), auto = v.reinforcement.main.auto && v.reinforcement.links.auto;
  el.innerHTML = `<div class="autobar"><button class="btn sm ${auto ? '' : 'pri'}" id="adReb" title="Włącz automatyczny dobór zbrojenia głównego i strzemion (najmniejsze pole stali spełniające wszystkie sprawdzenia, z wykonalnym zakotwieniem i gięciem)">⚙ Dobierz zbrojenie</button>
    <button class="btn sm" id="adFix" title="Przepisz dobrane zbrojenie jako dane ręczne (do dalszej edycji)" ${R && R.main && auto ? '' : 'disabled'}>⇩ Przyjmij dobrane jako ręczne</button>
    <button class="btn sm" id="adOpt" title="Optymalizacja wymiarów, klasy betonu i średnic – zakładka Optymalizacja">⚙ Optymalizuj wymiary…</button>
    <button class="btn sm" id="adCmp" title="Porównanie wariantów projektu" ${S.variants.length > 1 ? '' : 'disabled'}>Porównaj warianty</button></div>`;
  $('#adReb', el).onclick = () => { v.reinforcement.main.auto = true; v.reinforcement.links.auto = true; changed(true); toast('Dobór automatyczny zbrojenia włączony.'); };
  $('#adFix', el).onclick = () => {
    if (!R || !R.main) return; const mb = v.reinforcement.main, li = v.reinforcement.links, mi = R.main_input;
    Object.assign(mb, { auto: false, phi: R.main.phi, n_per_layer: R.main.n, layers: R.main.layers, anchor_load: mi.anchor_load });
    Object.assign(li, { auto: false, h_phi: R.links_input.h_phi, h_count: R.links_input.h_count, v_phi: R.links_input.v_phi, v_count: R.links_input.v_count });
    changed(true); toast('Zbrojenie przepisane do danych ręcznych.');
  };
  $('#adOpt', el).onclick = () => U.selectTab('opt');
  $('#adCmp', el).onclick = () => window.WV.comparePopup();
}

/* ------------------------------------------------------------ obliczenia */
let tmr = null;
function changed(rerender) {
  dirty = true; updateTitle();
  if (rerender) renderInputs();
  clearTimeout(tmr); tmr = setTimeout(recalc, 60);
  autosave();
}
function recalc() {
  try { R = WS.analyze(clone(V())); } catch (e) { console.error(e); R = { checks: [], messages: [{ level: 'error', text: 'Błąd obliczeń: ' + e.message }], verdict: { code: 'BLOCKED', title: 'OBLICZENIA ZABLOKOWANE', text: e.message, positive: false }, stm: {}, combinations: [] }; }
  U.R = R; U.S = S;
  refreshHints(); syncTicks(); renderStatus(); renderDsum();
  const ab = $('#adFix'); if (ab) ab.disabled = !(R && R.main && V().reinforcement.main.auto);
  rendered = {}; renderActive();
}
U.recalc = recalc; U.changed = changed;
const errs = () => R ? WS.errorsOf(R) : [];
const hasErr = () => !R || errs().length > 0;

/* ------------------------------------------------------------ zakładki */
let rendered = {};
function renderActive() {
  const tab = $('.tabs button.on').dataset.tab; if (rendered[tab]) return; rendered[tab] = true;
  const el = $('#p-' + tab);
  try {
    if (tab === 'data') { renderDataSide(); return; }
    if (tab === 'opt') { window.WV.renderOpt(el); return; }
    if (tab === 'report') { window.WV.renderReport(el); return; }
    if (hasErr() && tab !== 'sum') { el.innerHTML = errBox(); return; }
    ({ sum: renderSummary, stm: window.WV.renderStm, reb: window.WV.renderRebar })[tab](el);
  } catch (e) { console.error(e); el.innerHTML = `<div class="msg err">Błąd wyświetlania: ${esc(e.message)}</div>`; }
}
U.renderActive = renderActive;
U.invalidate = t => { if (t) rendered[t] = false; else rendered = {}; };
function errBox() { return `<div class="msgs">${errs().map(e => `<div class="msg err">${esc(e.text)}</div>`).join('') || '<div class="msg err">Brak wyników.</div>'}</div><p class="hint">Popraw dane w zakładce Dane – wyniki pojawią się automatycznie.</p>`; }

/* ------------------------------------------------------------ status, podgląd wyników */
const STL = { ok: 'OK', fail: 'NIE', warn: 'UWAGA', na: 'N/D' };
const isFail = c => c.status === 'fail';
function etaMax() { const c = R ? WS.critical(R) : null; return c && c.eta !== null ? c.eta : null; }
function renderStatus() {
  const el = $('#status'), set = (cls, txt, tip) => { el.className = cls; el.textContent = txt; el.title = tip || ''; };
  if (!R || !R.verdict) { set('fail', '✖ Brak wyników'); return; }
  const vd = R.verdict, e = etaMax(), et = e !== null && isFinite(e) ? ` · η = ${fmt(e * 100, 0)}%` : '';
  const nf = R.checks.filter(isFail).length;
  if (vd.code === 'BLOCKED') set('fail', `✖ ${errs().length ? 'Błąd danych / modelu' : 'Obliczenia zablokowane'}`, vd.text);
  else if (vd.code === 'OUT_OF_SCOPE') set('fail', '✖ Model poza zakresem J.3', vd.text);
  else if (vd.code === 'FAIL') set('fail', `✖ Niespełnione warunki: ${nf}`, vd.text);
  else if (vd.code === 'CONDITIONAL') set('warn', `✔ Spełniono warunkowo (NDP)${et}`, vd.text);
  else set('ok', `✔ Spełniono w zakresie programu${et}`, vd.text);
}
const DSUM = [['Model', c => c.group === 'Model', true], ['Krzyżulce', c => c.group === 'Krzyżulce'], ['Węzły', c => c.group === 'Węzły' || c.group === 'Docisk'], ['Cięgno', c => c.group === 'Cięgna'],
  ['Zakotwienie', c => c.group === 'Zakotwienie' || c.group === 'Wykonalność'], ['Strzemiona', c => c.group === 'Zbrojenie poprzeczne' || c.group === 'Rozłupywanie'], ['Konstrukcja', c => ['Konstrukcyjne', 'Mechanizmy dodatkowe', 'Połączenia prefabrykowane'].includes(c.group)], ['SGU', c => c.group === 'SGU']];
function dsumHTML() {
  if (!R || !R.checks) return '';
  if (hasErr()) return `<div class="dsum"><span class="dsb fail">✖ błąd danych – wyniki niedostępne</span></div>`;
  let h = '<div class="dsum">';
  DSUM.forEach(([l, pr, noEta], gi) => {
    const cs = R.checks.filter(pr).filter(x => x.status !== 'na'); if (!cs.length) return;
    const st = cs.some(isFail) ? 'fail' : cs.some(x => x.status === 'warn') ? 'warn' : 'ok';
    const et = cs.filter(x => x.eta !== null && !x.id.endsWith('_T81') && !x.id.endsWith('_LEG') && x.id !== 'MODEL_EQUILIBRIUM');
    const w = et.length ? et.reduce((p, q) => ((isFinite(q.eta) ? q.eta : 99) > (isFinite(p.eta) ? p.eta : 99) ? q : p)) : null;
    const bad = cs.filter(isFail).length;
    h += `<button class="dsb ${st}" data-dg="${gi}" title="${w ? esc(w.title) + ' – ' + (isFinite(w.eta) ? fmt(w.eta * 100, 0) + '%' : '∞') : esc(l)} · kliknij, aby przejść do Podsumowania"><span class="ic">${st === 'fail' ? '✖' : st === 'warn' ? '!' : '✔'}</span>${esc(l)}${w && !noEta ? `<span class="pc">${isFinite(w.eta) ? fmt(w.eta * 100, 0) + '%' : '∞'}</span>` : ''}${bad ? `<span class="nb">${bad}</span>` : ''}</button>`;
  });
  return h + '</div>';
}
function bindDsum(el) {
  $$('[data-dg]', el).forEach(b => b.addEventListener('click', () => {
    const pr = DSUM[+b.dataset.dg][1], c = R.checks, x = c.find(q => pr(q) && isFail(q)) || c.find(q => pr(q) && q.status === 'warn');
    U.selectTab('sum');
    setTimeout(() => { const i = x ? c.indexOf(x) : c.findIndex(pr); const tr = $(`#p-sum tr[data-ci="${i}"]`); if (tr) { tr.scrollIntoView({ block: 'center' }); flash(tr); } }, 80);
  }));
}
function renderDsum() { $$('#dsum, .dsumx').forEach(x => { x.innerHTML = dsumHTML(); bindDsum(x); }); }
U.renderDsum = renderDsum;
function flash(el) { if (!el) return; el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2200); }
let hlgT = 0;
function hlg(t) {
  const els = (Array.isArray(t) ? t : [t]).flatMap(x => typeof x === 'string' ? $$(x) : x ? [x] : []);
  els.forEach((el, i) => { const box = el.closest ? (el.closest('.row, tr, label.chk, .litem, .lrow') || el) : el; if (i === 0 && box.scrollIntoView) box.scrollIntoView({ block: 'center' }); box.classList.remove('hlg'); void box.offsetWidth; box.classList.add('hlg'); });
  if (els.length) hlgT = Date.now();
  return els.length;
}
document.addEventListener('pointerdown', e => { if (Date.now() - hlgT < 400) return; if (e.target.closest && e.target.closest('#modal .dlg')) return; $$('.hlg').forEach(x => x.classList.remove('hlg')); }, true);
U.hlg = hlg; U.flash = flash;

/* przejście z Podsumowania do danych, od których zależy warunek */
function fieldsFor(c) {
  const id = c.id, sd = /_L(_|$)/.test(id) || /_L$/.test(id) ? 'L' : 'R', side = sd === 'L' && LEFTOWN(V()) ? 'left' : 'right', g = `geometry.${side}.`;
  const M = 'reinforcement.main.', L = 'reinforcement.links.';
  if (/^STRUT_.*_(A|B)$/.test(id)) return [g + 'h_c', 'geometry.b', g + 'plate.length', 'materials.concrete', 'stm.strut_limit'];
  if (/TANMIN|TANMAX|^J3_SCOPE/.test(id)) return [g + 'a_c', g + 'h_c', 'stm.node_b_position'];
  if (/^NODE_A_.*_(BEAR|STRUT)$|^BEARING/.test(id)) return [g + 'plate.length', g + 'plate.width', 'materials.concrete'];
  if (/^NODE_B_FIT/.test(id)) return ['geometry.column.h_col', 'stm.node_b_position'];
  if (/^NODE_B/.test(id)) return [g + 'h_c', 'geometry.b', 'materials.concrete', 'stm.lever_arm'];
  if (/^NODE_A_ANCH/.test(id)) return [g + 'plate.offset', g + 'a_c', g + 'l_c'];
  if (/^TIE_AXIS/.test(id)) return [g + 'd_user'];
  if (/^TIE_|^AS_M|^SPACING_MAIN|^SPACING_LAYERS|^FIT_LOOP|^SLS/.test(id)) return V().reinforcement.main.auto ? [M + 'auto', 'materials.concrete'] : [M + 'phi', M + 'n_per_layer', M + 'layers'];
  if (/^ANCH_LOAD/.test(id)) return [M + 'anchor_load', M + 'bond', g + 'l_c'];
  if (/^ANCH_COL/.test(id)) return [M + 'anchor_column', M + 'column_leg', 'geometry.column.below'];
  if (/^MANDREL_LOAD/.test(id)) return [M + 'mandrel_load', M + 'front_leg', g + 'h_e'];
  if (/^MANDREL_COL/.test(id)) return [M + 'mandrel_column', M + 'column_leg', 'geometry.column.below'];
  if (/^COVER/.test(id)) return ['materials.exposure', 'materials.c_nom_user', 'materials.delta_c_dev'];
  if (/^J32|^J33|^SPLIT|^SPACING_LINKS|^J35/.test(id)) return V().reinforcement.links.auto ? [L + 'auto'] : [L + 'h_count', L + 'h_phi', L + 'v_count', L + 'v_phi'];
  if (/^SHEAR_MAX/.test(id)) return [g + 'h_c', 'geometry.b', 'materials.concrete'];
  if (/^OUTER_DEPTH/.test(id)) return [g + 'h_e', g + 'x_slope'];
  if (/^PRECAST/.test(id)) return [g + 'plate.length', 'geometry.precast.support_type', 'geometry.precast.dry_connection'];
  if (/^H_EFFECT|^TORSION/.test(id)) return ['@loads'];
  if (/^CONTAIN/.test(id)) return [g + 'x_slope', g + 'h_e', g + 'h_c'];
  if (/^MAN_|^MODEL/.test(id)) return MAN(V()) ? ['@manual'] : ['stm.mode'];
  if (/^COLUMN|^NODE_C|^PLATE_STEEL/.test(id)) return ['geometry.column.h_col'];
  return ['stm.mode'];
}
function gotoCheck(c) {
  const ks = fieldsFor(c);
  U.selectTab('data');
  setTimeout(() => {
    const sels = [];
    ks.forEach(k => {
      if (k === '@loads') { const g = $('#inputs details[data-id="loads"]'); if (g) { g.open = true; sels.push(...$$('.litem', g)); } return; }
      if (k === '@manual') { const g = $('#inputs details[data-id="stm"]'); if (g) { g.open = true; sels.push(...$$('[data-mk]', g)); } return; }
      const el = $(`#inputs [data-k="${k}"], #inputs [data-kt="${k}"]`); if (el) { const g = el.closest('details.grp'); if (g) g.open = true; sels.push(el); }
    });
    if (!hlg(sels)) { const g = $('#inputs details[data-id="stm"]'); if (g) { g.open = true; flash(g); } }
  }, 90);
}
U.gotoCheck = gotoCheck;

/* ------------------------------------------------------------ podsumowanie */
const DP = { force: 1, stress: 2, length: 0, area: 0, ratio: 3, moment: 1, none: 2 };
const SC = { force: 1e3, moment: 1e6 };
function ckVal(c, v) {
  if (v === null || v === undefined) return '—';
  const x = v / (SC[c.kind] || 1);
  if (c.id === 'MODEL_EQUILIBRIUM' || (Math.abs(x) > 0 && Math.abs(x) < 0.01 && c.kind === 'force')) return x.toExponential(1).replace('.', ',');
  return fmt(x, c.kind === 'length' && Math.abs(x) < 100 ? 1 : DP[c.kind]);
}
function ckCond(c) {
  if (c.E_d === null || c.R_d === null) return '';
  const u = WS.UNIT_OF[c.kind] ? ' ' + WS.UNIT_OF[c.kind] : '';
  return `${ckVal(c, c.E_d)} ≤ ${ckVal(c, c.R_d)}${u}`;
}
function utilBar(c) {
  if (c.eta === null || c.status === 'na' || c.id === 'MODEL_EQUILIBRIUM') return '';
  const r = isFinite(c.eta) ? c.eta : 9.99, w = Math.min(100, r * 100), cls = c.status === 'fail' ? 'fail' : (c.status === 'warn' || r > 0.9) ? 'warn' : '';
  return `<span class="ub ${cls}"><i style="width:${w}%"></i></span><span class="pct">${isFinite(c.eta) ? fmt(r * 100, 0) + '%' : '∞'}</span>`;
}
Object.assign(U, { ckCond, ckVal, utilBar, STL });
let prevStat = null;
function syncTicks() {
  if (!R || !R.checks || !R.checks.length || hasErr()) return;
  const T = S.meta.ticks = S.meta.ticks || {}, SAT = c => c.status === 'ok' || c.status === 'na';
  if (!S.meta.ticksInit) { if (!Object.keys(T).length) R.checks.forEach(c => { if (SAT(c)) T[c.id] = true; }); S.meta.ticksInit = true; }
  else if (prevStat) R.checks.forEach(c => { const p = prevStat[c.id], now = SAT(c); if ((p === undefined || p === false) && now) T[c.id] = true; else if (p === true && !now) delete T[c.id]; });
  prevStat = {}; R.checks.forEach(c => { prevStat[c.id] = SAT(c); });
}
function card(t, v, s, cls) { return `<div class="card ${cls || ''}"><div class="t">${t}</div><div class="v">${v}</div><div class="s">${s}</div></div>`; }
const stCls = c => !c ? '' : c.status === 'fail' ? 'fail' : c.status === 'warn' ? 'warn' : c.status === 'ok' ? 'ok' : '';
function msgsHTML() {
  const seen = new Set(), out = [];
  (R.messages || []).forEach(m => { if (m.level === 'info' || seen.has(m.text)) return; seen.add(m.text); out.push(`<div class="msg ${m.level === 'error' ? 'err' : 'wrn'}">${esc(m.text)}</div>`); });
  return out.length ? `<div class="msgs">${out.join('')}</div>` : '';
}
function renderSummary(el) {
  const c = R.checks, vd = R.verdict, crit = WS.critical(R), gov = R.stm && R.stm[R.governing], sm = gov && gov.sides && (gov.sides.R || gov.sides.L);
  const tie = c.find(x => x.id === 'TIE_R') || c.find(x => /^TIE_[RL]$/.test(x.id)), vcls = { PASS_SCOPE: 'ok', CONDITIONAL: 'warn', FAIL: 'fail', OUT_OF_SCOPE: 'fail', BLOCKED: 'fail' }[vd.code];
  let cards = card('Wynik', esc(vd.title), esc(vd.code === 'PASS_SCOPE' ? 'wszystkie sprawdzenia w zakresie programu' : vd.code === 'CONDITIONAL' ? 'NDP niepotwierdzone' : vd.code === 'FAIL' ? `niespełnione: ${c.filter(isFail).length}` : 'brak pozytywnego wniosku'), vcls);
  if (crit) cards += card('Element krytyczny', isFinite(crit.eta) ? fmt(crit.eta * 100, 0) + '%' : '∞', sym(crit.title), stCls(crit));
  if (tie) cards += card('Cięgno', `${fmt(tie.E_d / 1e3, 1)} / ${fmt(tie.R_d / 1e3, 1)}`, `T<sub>Ed</sub> / T<sub>Rd</sub> [kN]`, stCls(tie));
  if (sm) cards += card('Krzyżulec', `θ = ${fmt(sm.state.theta_deg, 1)}°`, `tan θ = ${fmt(sm.state.tan_theta, 2)} · x<sub>c</sub> = ${fmt(sm.state.x_c, 0)} mm · z<sub>0</sub> = ${fmt(sm.state.z0, 0)} mm`, sm.state.tan_theta < 1 - 1e-9 || sm.state.tan_theta > 2.5 + 1e-9 ? 'fail' : 'ok');
  if (R.main) cards += card('Zbrojenie główne', esc(R.main.desc()), `A<sub>s</sub> = ${fmt(R.main.As, 0)} mm² · ${esc(WS.ANCHOR_LABEL[R.main_input.anchor_load] || '')}`, stCls(c.find(x => /^ANCH_LOAD/.test(x.id) && isFail(x)) || tie));
  if (R.cover) cards += card('Otulina', `${R.cover.c_nom} mm`, `c<sub>nom</sub> do strzemion · ${esc(R.cover.structural_class)} · ${esc(R.cover.exposure)}${R.cover.user ? ' · ręcznie' : ''}`, stCls(c.find(x => /^COVER/.test(x.id) && x.status !== 'ok')));
  if (R.governing) cards += card('Kombinacja decydująca', esc(R.governing), `${R.combinations.filter(q => q.is_uls).length} komb. SGN · ${esc(R.model_type)}`, '');
  let html = `<div class="dsumx"></div><div class="cards">${cards}</div>`;
  html += `<div class="verdict ${vcls}"><b>${esc(vd.title)}.</b> ${esc(vd.text)}</div>`;
  html += msgsHTML();
  if (!c.length) { el.innerHTML = html; renderDsum(); return; }
  const ticks = S.meta.ticks || {}, nT = c.filter(x => ticks[x.id]).length;
  const nF = c.filter(isFail);
  if (nF.length) html += `<div class="failnav">Niespełnione warunki: ${nF.map(x => `<button class="goto" data-goto2="${c.indexOf(x)}">${sym(x.title)}</button>`).join('')}</div>`;
  html += `<div class="tickbar"><span id="tickCnt">Odhaczono: <b>${nT}</b> z ${c.length}</span><button class="btn sm" id="tickOk">Odhacz spełnione</button><button class="btn sm" id="tickClr">Wyczyść znaczniki</button><span class="hint">Kliknij podstawę normową, aby zobaczyć objaśnienie; kliknij warunek – jak obliczono.</span></div>`;
  html += `<div class="tscroll"><table class="ctab"><thead><tr><th class="tk" title="Sprawdzone">✓</th><th>Sprawdzenie</th><th>Podstawa</th><th style="text-align:right">Warunek</th><th>Wykorzystanie</th><th>Status</th><th class="nt">Uwagi</th></tr></thead><tbody>`;
  let grp = '';
  c.forEach((x, i) => {
    if (x.group !== grp) { grp = x.group; html += `<tr class="g"><td colspan="7">${esc(grp)}</td></tr>`; }
    const on = !!ticks[x.id], notes = (x.notes || []).filter(Boolean);
    html += `<tr class="${on ? 'done' : ''}" data-ci="${i}"><td class="tk"><input type="checkbox" data-tick="${i}" ${on ? 'checked' : ''} aria-label="sprawdzone"></td><td>${sym(x.title)}${x.basis !== WS.BASIS.NORMATIVE ? ` <span class="bas" title="Charakter podstawy">${esc(x.basis)}</span>` : ''}</td><td class="ref"><button class="nref" data-ref="${i}" title="Objaśnienie podstawy">${esc(x.clause.replace(/^EN 1992-1-1 /, ''))}</button></td><td class="val">${ckCond(x)}</td><td class="bar" style="white-space:nowrap">${utilBar(x)}</td><td class="stc"><span class="st ${x.status}">${STL[x.status]}</span>${x.status === 'fail' || x.status === 'warn' ? `<button class="goto" data-goto="${i}" title="Przejdź do danych, od których zależy warunek">pokaż →</button>` : ''}</td><td class="nt">${notes.length || x.conclusion ? exDetails(esc(x.conclusion) + (notes.length ? '<br>' + notes.map(esc).join('<br>') : '')) : ''}</td></tr>`;
  });
  html += '</tbody></table></div>';
  el.innerHTML = html; renderDsum();
  const upd = () => { const n = c.filter(x => (S.meta.ticks || {})[x.id]).length; $('#tickCnt', el).innerHTML = `Odhaczono: <b>${n}</b> z ${c.length}`; };
  const setTick = (x, v) => { S.meta.ticks = S.meta.ticks || {}; if (v) S.meta.ticks[x.id] = true; else delete S.meta.ticks[x.id]; };
  $$('[data-tick]', el).forEach(cb => cb.addEventListener('change', () => { setTick(c[+cb.dataset.tick], cb.checked); cb.closest('tr').classList.toggle('done', cb.checked); upd(); dirty = true; updateTitle(); autosave(); rendered.report = false; }));
  $('#tickOk', el).onclick = () => { c.forEach(x => { if (x.status === 'ok' || x.status === 'na') setTick(x, true); }); dirty = true; autosave(); rendered.report = false; renderSummary(el); };
  $('#tickClr', el).onclick = () => { S.meta.ticks = {}; dirty = true; autosave(); rendered.report = false; renderSummary(el); };
  $$('[data-ref]', el).forEach(b => b.addEventListener('click', () => normPopup(c[+b.dataset.ref])));
  $$('tr[data-ci] td.val, tr[data-ci] td.bar', el).forEach(td => { td.classList.add('xclick'); td.title = 'Kliknij – jak obliczono (wzór, podstawienie, punkt normy)'; td.addEventListener('click', () => explainPopup(c[+td.closest('tr').dataset.ci])); });
  $$('tr[data-ci] td:nth-child(2)', el).forEach(td => { td.classList.add('xclick'); td.addEventListener('click', () => explainPopup(c[+td.closest('tr').dataset.ci])); });
  $$('[data-goto], [data-goto2]', el).forEach(b => b.addEventListener('click', () => gotoCheck(c[+(b.dataset.goto || b.dataset.goto2)])));
}

/* ------------------------------------------------------------ okna objaśnień */
const normLab = k => k === '1990' ? 'PN-EN 1990, rozdz. 6.4–6.5' : k === 'model' ? 'Kontrola modelu (program)' : k === 'J' ? 'PN-EN 1992-1-1, załącznik J' : k === 'J.3' ? 'PN-EN 1992-1-1, zał. J.3' : `PN-EN 1992-1-1, pkt ${k}`;
const normBody = keys => keys.filter(k => window.WSN && window.WSN.N[k]).map(k => { const e = window.WSN.N[k]; return `<div class="nsec"><div class="nlab">${esc(normLab(k))}</div><h4>${e.t}</h4><p>${e.s}</p>${e.f ? `<div class="nf">${e.f}</div>` : ''}${e.h ? `<div class="nh"><b>Podpowiedź:</b> ${e.h}</div>` : ''}</div>`; }).join('');
U.normBody = normBody;
function openModal(html, cls) { const m = $('#modal'); m.innerHTML = `<div class="dlg ${cls || ''}">${html}</div>`; m.style.display = 'flex'; $$('[data-close]', m).forEach(b => b.onclick = () => { m.style.display = 'none'; }); const f = $('[data-close]', m); if (f) f.focus(); return m; }
U.openModal = openModal;
function normPopup(x) {
  const keys = window.WSN ? window.WSN.find(x.clause, x.group) : [], cond = ckCond(x);
  openModal(`<h3>${esc(x.clause)}</h3><div class="ncur"><b>W tym projekcie:</b> ${sym(x.title)}${cond ? ` – ${cond}` : ''}${x.eta !== null && isFinite(x.eta) && x.status !== 'na' ? `, wykorzystanie ${fmt(x.eta * 100, 0)}%` : ''} · <span class="st ${x.status}">${STL[x.status]}</span><br><small>Charakter podstawy: ${esc(x.basis)}</small></div>${normBody(keys) || `<p>Brak objaśnienia dla odnośnika „${esc(x.clause)}”.</p>`}<p class="ndisc">Streszczenia i podpowiedzi opracowane na potrzeby programu – nie zastępują treści normy PN-EN 1992-1-1 z Załącznikiem Krajowym.</p><div class="dbtn"><button class="btn pri" data-close>Zamknij</button></div>`, 'norm');
}
function explainHTML(c) {
  const sy = Object.entries(c.symbols || {});
  return `<div class="ncur"><b>Wynik:</b> ${ckCond(c) || '—'}${c.eta !== null && isFinite(c.eta) && c.status !== 'na' ? ` · wykorzystanie <b>${fmt(c.eta * 100, 0)}%</b>` : ''} · <span class="st ${c.status}">${STL[c.status]} – ${esc(WS.ST_LABEL[c.status])}</span></div>
    <h4 class="lsec">Wzór</h4><div class="eqx">${sym(c.formula || '—')}</div>
    ${sy.length ? `<h4 class="lsec">Oznaczenia</h4><table class="kv">${sy.map(([k, v]) => `<tr><td>${sym(k)}</td><td style="text-align:left;font-weight:400">${esc(v)}</td></tr>`).join('')}</table>` : ''}
    <h4 class="lsec">Podstawienie i wynik</h4><div class="eqx">${sym(c.substitution || '—')}</div>
    <h4 class="lsec">Wniosek</h4><p>${esc(c.conclusion || '')}</p>
    ${(c.notes || []).length ? `<h4 class="lsec">Uwagi</h4><ul>${c.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul>` : ''}
    <p class="hint">Podstawa: ${esc(c.clause)} · charakter: ${esc(c.basis)}${c.combination ? ' · kombinacja: ' + esc(c.combination) : ''}${c.element_ref ? ' · element: ' + esc(c.element_ref) : ''} · id: ${esc(c.id)}</p>`;
}
U.explainHTML = explainHTML;
function explainPopup(c) {
  if (!c) return;
  const keys = window.WSN ? window.WSN.find(c.clause, c.group) : [];
  openModal(`<h3>Jak obliczono: ${sym(c.title)}</h3>${explainHTML(c)}<h4 class="lsec">Punkt normy</h4>${normBody(keys) || `<p>Brak objaśnienia dla „${esc(c.clause)}”.</p>`}<p class="ndisc">Objaśnienia opracowane na potrzeby programu – nie zastępują treści normy.</p><div class="dbtn"><button class="btn" id="exGo">Pokaż dane →</button><button class="btn pri" data-close>Zamknij</button></div>`, 'norm expl');
  $('#exGo').onclick = () => { $('#modal').style.display = 'none'; gotoCheck(c); };
}
U.explainPopup = explainPopup; U.normPopup = normPopup;
/* odnośniki do punktów normy w tekście → przyciski z objaśnieniem */
const NREF_RX = /(PN-EN\s*1990|EN\s*1990)?([,\s]*)(?:([Tt]abl?\.|[Rr]ys\.|[Ww]zór|[Ww]zory|[Ww]zoru|[Ww]z\.|[Zz]ał\.)\s*)?(\()?(?<![\p{L}\d.,])(\d{1,2}\.\d{1,2}(?:\.\d{1,2}){0,3}[a-zA-Z]{0,3}|J\.\d(?:\(\d\))?|[A-J](?![\p{L}\d]))(\(\d{1,2}\))?(\))?(?!\d|,\d)/gu;
const NL_SKIP = 'svg,button,select,option,textarea,input,script,style,.nlink,.dlg.norm,#top,.tabs,.nf,[contenteditable],#report';
function linkRefs(root) {
  const B = window.WSN; if (!root || !B) return 0;
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: n => /\d\.\d|ał\.\s*[A-J]|J\.\d/.test(n.nodeValue) && n.parentElement && !n.parentElement.closest(NL_SKIP) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
  const list = []; let n; while ((n = tw.nextNode())) list.push(n);
  let cnt = 0;
  list.forEach(tn => {
    const t = tn.nodeValue; let last = 0, made = false, m, prevEnd = 0; const frag = document.createDocumentFragment();
    NREF_RX.lastIndex = 0;
    while ((m = NREF_RX.exec(t))) {
      const [all, g1, g2, pre, po, tok, tail, pc] = m; const pe = prevEnd; prevEnd = m.index + all.length;
      if (!all.length) { NREF_RX.lastIndex++; continue; }
      if (!tok) continue;
      const preL = (pre || '').toLowerCase();
      let kind = /^tab/.test(preL) ? 'tab' : /^rys/.test(preL) ? 'rys' : /^wz/.test(preL) ? 'eq' : /^zał/.test(preL) ? 'zal' : '';
      if (/^[A-J]$/.test(tok) && kind !== 'zal') continue;
      if (!kind) { const parts = tok.replace(/[a-zA-Z]+$/, '').split('.').length; kind = parts === 2 && !tail && (po && pc || /[a-zA-Z]$/.test(tok)) && !/^J/.test(tok) ? 'eq' : 'cl'; }
      const keys = B.resolve(kind, tok.replace(/\(\d\)$/, ''), (g1 || '') + ' ' + t.slice(Math.max(pe, m.index - 40), m.index)); if (!keys.length) continue;
      const both = !!(po && pc); let s0 = m.index + (g1 || '').length + (g2 || '').length, s1 = m.index + all.length;
      if (po && !both) { if (!pre) s0 += 1; } if (pc && !both) s1 -= 1;
      if (s0 > last) frag.appendChild(document.createTextNode(t.slice(last, s0)));
      const b = document.createElement('button'); b.type = 'button'; b.className = 'nlink'; b.dataset.nk = keys.join(','); b.dataset.nref = t.slice(s0, s1).replace(/^\(|\)$/g, '').trim();
      b.title = keys.map(normLab).join('; ') + ' – kliknij, aby zobaczyć objaśnienie'; b.textContent = t.slice(s0, s1);
      frag.appendChild(b); last = s1; made = true; cnt++;
    }
    if (!made) return;
    if (last < t.length) frag.appendChild(document.createTextNode(t.slice(last)));
    tn.parentNode.replaceChild(frag, tn);
  });
  return cnt;
}
let nlT = 0;
const nlObs = new MutationObserver(recs => { if (!recs.some(r => r.addedNodes.length && r.target.nodeType === 1 && !r.target.closest('svg'))) return; clearTimeout(nlT); nlT = setTimeout(() => { ['#out', '#modal'].forEach(s => linkRefs($(s))); nlObs.takeRecords(); }, 120); });
function normRefPopup(ref, keys) {
  let m = $('#nmodal');
  if (!m) { m = document.createElement('div'); m.id = 'nmodal'; m.setAttribute('role', 'dialog'); document.body.appendChild(m); }
  m.innerHTML = `<div class="dlg norm"><h3>[${esc(ref)}]</h3>${normBody(keys) || `<p>Brak objaśnienia dla „${esc(ref)}”.</p>`}<p class="ndisc">Streszczenie i podpowiedź opracowane na potrzeby programu – nie zastępują treści normy.</p><div class="dbtn"><button class="btn pri" id="nmClose">Zamknij</button></div></div>`;
  m.style.display = 'flex';
  const close = () => { m.style.display = 'none'; window.removeEventListener('keydown', kd, true); };
  const kd = e => { if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); close(); } };
  window.addEventListener('keydown', kd, true); m.onmousedown = e => { if (e.target === m) close(); }; $('#nmClose', m).onclick = close; $('#nmClose', m).focus();
}
document.addEventListener('click', e => { const b = e.target && e.target.closest && e.target.closest('.nlink'); if (!b) return; e.preventDefault(); e.stopPropagation(); normRefPopup(b.dataset.nref, (b.dataset.nk || '').split(',').filter(Boolean)); }, true);

/* ------------------------------------------------------------ zakładka Dane – panel boczny ze schematem */
let schMode = (() => { try { return localStorage.getItem('ws.sch') || 'stm'; } catch (e) { return 'stm'; } })();
let schStress = (() => { try { return localStorage.getItem('ws.str') !== '0'; } catch (e) { return true; } })();
let drag = null, schScene = null;
function schemeSVG(W, view) {
  const v = V(), useR = R && !hasErr() && R.geometry;
  schScene = WD.sceneScheme(v, drag ? null : (useR ? R : null), { stm: schMode === 'stm', stress: schStress, rebar: schMode === 'reb', handles: true, dims: true });
  if (schScene.err) return `<div class="msg err">${esc(schScene.err)}</div>`;
  return WD.svg(schScene, W, { H: Math.max(420, Math.min(720, W * 0.9)), view });
}
function variantTabsHTML() {
  return `<div class="beamtabs">${S.variants.map((q, i) => `<button class="btab ${i === S.active ? 'on' : ''}" data-vt="${i}" title="${esc(q.name)} – dwuklik: zmień nazwę"><span>${i + 1} ${esc(q.name.slice(0, 18))}</span>${i === S.active && S.variants.length > 1 ? `<i data-vdel="${i}" title="Usuń wariant">×</i>` : ''}</button>`).join('')}${S.variants.length < 10 ? '<button class="btab add" data-vadd="1" title="Nowy wariant (kopia bieżącego)">+</button>' : ''}</div>`;
}
function combosTableHTML() {
  if (!R || !R.combinations || !R.combinations.length) return '';
  const sides = DBL(V()) ? ['R', 'L'] : ['R'];
  return `<div class="box"><h4>Kombinacje obciążeń (wartości obliczeniowe)</h4><div class="tscroll"><table class="sched cmbt"><tr><th>Kombinacja</th><th>Rodzaj</th>${sides.map(sd => `<th>V${sides.length > 1 ? '<sub>' + sd + '</sub>' : ''} [kN]</th><th>H [kN]</th><th>M [kNm]</th>`).join('')}</tr>${R.combinations.map(c => `<tr class="${c.name === R.governing ? 'gov' : ''}"><td>${esc(c.name)}${c.name === R.governing ? ' <b title="kombinacja decydująca">◆</b>' : ''}</td><td>${esc(WS.COMB_KINDS[c.kind] || c.kind)}</td>${sides.map(sd => { const a = c.sides[sd] || { V: 0, H: 0, M: 0 }; return `<td class="n">${fmt(a.V / 1e3, 1)}</td><td class="n">${fmt(a.H / 1e3, 1)}</td><td class="n">${fmt(a.M / 1e6, 1)}</td>`; }).join('')}</tr>`).join('')}</table></div>${(R.assumptions || []).filter(a => /kombinac|H_min|γ/i.test(a)).slice(0, 3).map(a => `<p class="hint">${esc(a)}</p>`).join('')}</div>`;
}
function quickHTML() {
  if (!R || hasErr() || !R.stm || !R.stm[R.governing]) return '';
  const gov = R.stm[R.governing]; if (!gov.sides || !Object.keys(gov.sides).length) return '';
  return `<div class="box"><h4>Model J.3 – kombinacja decydująca ${esc(R.governing)}</h4><table class="kv">${Object.entries(gov.sides).map(([sd, sm]) => { const s = sm.state, p = sm.params; return `${DBL(V()) ? `<tr><td colspan="3"><b>Wspornik ${WS.SIDE_NAME[sd]}</b></td></tr>` : ''}<tr><td>V<sub>Ed</sub> / H<sub>Ed</sub></td><td>${fmt(p.V / 1e3, 1)} / ${fmt(p.H / 1e3, 1)}</td><td>kN</td></tr><tr><td>Siła w cięgnie T<sub>Ed</sub></td><td>${fmt(s.T / 1e3, 1)}</td><td>kN</td></tr><tr><td>Siła w krzyżulcu C<sub>Ed</sub></td><td>${fmt(s.C / 1e3, 1)}</td><td>kN</td></tr><tr><td>x<sub>c</sub> / z<sub>0</sub></td><td>${fmt(s.x_c, 0)} / ${fmt(s.z0, 0)}</td><td>mm</td></tr><tr><td>θ (tan θ)</td><td>${fmt(s.theta_deg, 1)}° (${fmt(s.tan_theta, 2)})</td><td></td></tr><tr><td>A<sub>s,req</sub> = T/f<sub>yd</sub></td><td>${fmt(s.T / R.materials.steel.fyd, 0)}</td><td>mm²</td></tr>`; }).join('')}</table><p class="hint">Dobór x<sub>c</sub>: ${esc((Object.values(gov.sides)[0].search || {}).method || '')}.</p></div>`;
}
function renderDataSide() {
  const el = $('#dataside'); if (!el) return;
  const W = Math.max(380, Math.min(900, el.clientWidth - 26 || 640));
  el.innerHTML = `${variantTabsHTML()}<div class="box schemebox"><div class="schhd"><b>Schemat wspornika</b><span class="segsw">${[['stm', 'Model STM'], ['reb', 'Zbrojenie'], ['geo', 'Geometria']].map(([k, l]) => `<button class="${schMode === k ? 'on' : ''}" data-sm="${k}">${l}</button>`).join('')}</span>${schMode === 'stm' ? `<label class="chk" style="display:inline-flex;margin-left:8px"><input type="checkbox" id="schStr" ${schStress ? 'checked' : ''}><span>pola naprężeń (η)</span></label>` : ''}</div>
    <div class="schemewrap" id="schWrap">${schemeSVG(W)}</div>${schMode === 'stm' && schStress && R && !hasErr() ? WD.etaLegend() : ''}
    <p class="hint">Kliknij element (wspornik, płytę, słup, obciążenie, zbrojenie), aby przejść do jego danych. Niebieskie uchwyty przeciągnij, aby zmienić a<sub>c</sub>, l<sub>c</sub>, h<sub>c</sub>, h<sub>e</sub> (krok 5 mm).</p></div>${quickHTML()}${combosTableHTML()}`;
  bindScheme(el);
}
const GO_GROUP = { geo: 'geo', col: 'col', plate: 'plate', loads: 'loads', main: 'main', links: 'links', mat: 'mat', stm: 'stm' };
function bindScheme(el) {
  $$('[data-sm]', el).forEach(b => b.addEventListener('click', () => { schMode = b.dataset.sm; try { localStorage.setItem('ws.sch', schMode); } catch (e) { /* */ } renderDataSide(); }));
  const sc = $('#schStr', el); if (sc) sc.addEventListener('change', () => { schStress = sc.checked; try { localStorage.setItem('ws.str', schStress ? '1' : '0'); } catch (e) { /* */ } renderDataSide(); });
  $$('[data-vt]', el).forEach(b => { b.addEventListener('click', ev => { if (ev.target.dataset.vdel) return; switchVariant(+b.dataset.vt); }); b.addEventListener('dblclick', () => renameVariant(+b.dataset.vt)); });
  $$('[data-vdel]', el).forEach(b => b.addEventListener('click', async ev => { ev.stopPropagation(); if (await ask(`Usunąć wariant „${esc(V().name)}”?`, 'Usuń', true)) { S.variants.splice(S.active, 1); S.active = Math.max(0, S.active - 1); afterVariant(); } }));
  $$('[data-vadd]', el).forEach(b => b.addEventListener('click', () => { const v = clone(V()); v.name = 'Wariant ' + (S.variants.length + 1); S.variants.push(v); S.active = S.variants.length - 1; afterVariant(); toast('Utworzono wariant (kopia poprzedniego).'); }));
  const wrap = $('#schWrap', el); if (!wrap) return;
  wrap.addEventListener('click', e => {
    if (drag) return; const t = e.target.closest('[data-go], [data-ref]'); if (!t) return;
    const ref = t.dataset.ref || '', go = t.dataset.go || (ref.startsWith('member:') || ref.startsWith('node:') ? 'stm' : '');
    if (ref && (ref.startsWith('member:') || ref.startsWith('node:')) && R && !hasErr()) { window.WV.elementPopup(ref, R.governing); return; }
    const gid = GO_GROUP[go]; if (!gid) return;
    const g = $(`#inputs details[data-id="${gid}"]`); if (g) { g.open = true; g.scrollIntoView({ block: 'start', behavior: 'smooth' }); flash(g); }
  });
  wrap.addEventListener('pointerdown', e => {
    const h = e.target.closest('.hdl'); if (!h || !schScene || !schScene.view) return;
    e.preventDefault(); h.setPointerCapture && h.setPointerCapture(e.pointerId);
    const [key, sd] = h.dataset.h.split(':'), side = sd === 'L' && LEFTOWN(V()) ? 'left' : 'right', svg = wrap.querySelector('svg'), view = Object.assign({}, schScene.view);
    const gm = WS.buildGeometry(V().geometry), sg = gm.sides[sd] || gm.sides.R;
    drag = { key, side, sd, view, svg, sg, t: 0 };
    const mv = ev => {
      const sv = wrap.querySelector('svg') || svg, r = sv.getBoundingClientRect(); if (!r.width) return; const f = view.W / r.width, [x, y] = WD.toModel({ view }, (ev.clientX - r.left) * f, (ev.clientY - r.top) * f);
      const si = V().geometry[side], xi = sg.s * (x - sg.x_face), r5 = q => Math.round(q / 5) * 5;
      if (key === 'a_c') si.a_c = Math.max(si.plate.length / 2 + 5, Math.min(si.l_c - si.plate.length / 2 - 5, r5(xi)));
      else if (key === 'l_c') si.l_c = Math.max(si.a_c + si.plate.length / 2 + 5, Math.min(2000, r5(xi)));
      else if (key === 'h_e') si.h_e = Math.max(50, Math.min(si.h_c, r5(-y)));
      else if (key === 'h_c') si.h_c = Math.max(si.h_e, Math.min(2500, r5(-y)));
      wrap.innerHTML = schemeSVG(view.W, view);
      const now = Date.now(); if (now - drag.t > 300) { drag.t = now; const inp = $(`#inputs [data-k="geometry.${side}.${key}"]`); if (inp) inp.value = showNum(si[key]); }
    };
    const up = () => { window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up); drag = null; dirty = true; renderInputs(); changed(false); };
    window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up);
  });
}
function afterVariant() { prevStat = null; dirty = true; renderInputs(); recalc(); updateTitle(); autosave(); }
function switchVariant(i) { if (i === S.active) return; S.active = i; afterVariant(); }
function renameVariant(i) {
  const m = openModal(`<h3>Nazwa wariantu</h3><input class="txt" id="vnm" value="${esc(S.variants[i].name)}" style="height:30px"><div class="dbtn"><button class="btn" data-close>Anuluj</button><button class="btn pri" id="vok">Zapisz</button></div>`, 'sm');
  const inp = $('#vnm', m); inp.focus(); inp.select();
  const ok = () => { S.variants[i].name = inp.value.trim() || S.variants[i].name; m.style.display = 'none'; dirty = true; renderDataSide(); updateTitle(); autosave(); rendered.report = false; };
  $('#vok', m).onclick = ok; inp.addEventListener('keydown', e => { if (e.key === 'Enter') ok(); });
}
// podział zakładki Dane: dane | schemat (przeciąganie; zapamiętywany)
(function () {
  const wrap = () => $('#p-data .datawrap'), set = v => { const w = wrap(); if (w) w.style.setProperty('--dsl', v); };
  try { const v = localStorage.getItem('ws.dsl'); if (v) setTimeout(() => set(v), 0); } catch (e) { /* */ }
  document.addEventListener('pointerdown', e => {
    const h = e.target.closest && e.target.closest('#dsplit'); if (!h) return;
    e.preventDefault(); const w = wrap(), r = w.getBoundingClientRect(); h.classList.add('drag'); document.body.classList.add('dsdrag');
    const mv = ev => { const pc = Math.max(25, Math.min(75, (ev.clientX - r.left) / r.width * 100)); set(pc.toFixed(1) + '%'); };
    const up = () => { h.classList.remove('drag'); document.body.classList.remove('dsdrag'); window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up); try { localStorage.setItem('ws.dsl', w.style.getPropertyValue('--dsl')); } catch (e2) { /* */ } renderDataSide(); };
    window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up);
  });
  document.addEventListener('dblclick', e => { if (e.target.closest && e.target.closest('#dsplit')) { set('50%'); renderDataSide(); } });
})();

/* ------------------------------------------------------------ kolory rysunków (motyw) */
const SVCOL = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;
function themeSvgIn(root) {
  root.querySelectorAll('svg [fill], svg [stroke]').forEach(el => ['fill', 'stroke'].forEach(a => {
    const v = el.getAttribute(a); if (!v || !SVCOL.test(v)) return;
    let h = v.slice(1).toLowerCase(); if (h.length === 3) h = h.replace(/./g, c => c + c);
    el.style.setProperty(a, `var(--sv-${h}, #${h})`);
  }));
}
new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => { if (n.nodeType !== 1) return; if (n.tagName.toLowerCase() === 'svg') themeSvgIn(n.parentNode || n); else if (n.querySelector('svg')) themeSvgIn(n); }))).observe(document.documentElement, { childList: true, subtree: true });

/* ------------------------------------------------------------ host / pliki */
const ART = !!window.__ARTIFACT;
const Cap = { dl: null, db: null, col: null, list: [], ready: false, slow: false, err: null };
let cloudId = null, cloudName = '';
const pending = {}; let reqId = 0;
window.__hostReply = (id, res) => { const p = pending[id]; if (p) { delete pending[id]; p(res); } };
function hostCall(op, args) { return new Promise(res => { const id = ++reqId; pending[id] = res; try { window.hostRequest(JSON.stringify(Object.assign({ id, op }, args))); } catch (e) { delete pending[id]; res({ ok: false, err: String(e) }); } }); }
const inHost = () => typeof window.hostRequest === 'function';
function toast(msg, ms) { const t = $('#toast'); t.textContent = msg; t.style.display = 'block'; clearTimeout(toast.t); toast.t = setTimeout(() => t.style.display = 'none', ms || 2600); }
const baseName = p => (p || '').split(/[\\/]/).pop();
const safeName = ext => (S.info.name || 'wspornik').replace(/[\\/:*?"<>|]+/g, '_').trim() + ext;
Object.assign(U, { toast, safeName, inHost, hostCall, ART, Cap, baseName });
function updateTitle() {
  const lab = ART ? (cloudId ? '☁ ' + (cloudName || 'projekt') : (filePath ? baseName(filePath) : 'nowy projekt')) : (filePath ? baseName(filePath) : 'bez nazwy');
  $('#fileName').textContent = (dirty ? '● ' : '') + lab;
  if (ART) return;
  const t = `Krótki wspornik ST – ${S.info.name || 'projekt'} [${lab}${dirty ? ' *' : ''}]`;
  document.title = t;
  if (typeof window.hostTitle === 'function') { try { window.hostTitle(t); } catch (e) { /* */ } }
}
let asT = null;
function autosave() {
  clearTimeout(asT);
  asT = setTimeout(() => {
    const data = JSON.stringify({ state: S, filePath, cloudId, cloudName });
    if (typeof window.hostStore === 'function') { try { window.hostStore(data); } catch (e) { /* */ } }
    else { try { localStorage.setItem('wspornik-autosave', data); } catch (e) { /* */ } }
  }, 600);
}
function ask(msg, okLabel, danger) {
  return new Promise(res => {
    const m = $('#modal');
    m.innerHTML = `<div class="dlg sm"><p>${msg}</p><div class="dbtn"><button class="btn" data-a="0">Anuluj</button><button class="btn ${danger ? 'dng' : 'pri'}" data-a="1">${okLabel}</button></div></div>`;
    m.style.display = 'flex';
    const done = v => { m.style.display = 'none'; m.onclick = null; document.removeEventListener('keydown', kd, true); res(v); };
    const kd = e => { if (e.key === 'Escape') { e.stopPropagation(); done(false); } };
    document.addEventListener('keydown', kd, true);
    m.onclick = e => { const b = e.target.closest('[data-a]'); if (b) done(b.dataset.a === '1'); else if (e.target === m) done(false); };
    $('[data-a="1"]', m).focus();
  });
}
U.ask = ask;
async function offerFile(name, data, okMsg) {
  if (!Cap.dl) { toast('Pobieranie plików nie jest dostępne w tym widoku.'); return false; }
  try { await Cap.dl.save({ filename: name, data }); toast(okMsg); return true; }
  catch (e) { const c = e && e.code; if (c === 'declined') return false; toast(c === 'rate_limited' ? 'Poczekaj chwilę – poprzednie pobieranie jeszcze trwa.' : 'Nie udało się pobrać pliku' + (c ? ` (${c})` : '') + '.'); return false; }
}
async function download(name, content, mime) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mime + ';charset=utf-8' });
  if (typeof window.showSaveFilePicker === 'function') {          // przeglądarka (plik app.html otwarty z dysku): okno zapisu z nazwą pliku
    const ext = (name.match(/\.[a-z0-9]+$/i) || [''])[0];
    try {
      const h = await window.showSaveFilePicker({ suggestedName: name, types: ext ? [{ description: ext.slice(1).toUpperCase(), accept: { [mime || 'application/octet-stream']: [ext] } }] : undefined });
      const w = await h.createWritable(); await w.write(blob); await w.close(); toast('Zapisano: ' + h.name); return true;
    } catch (e) { if (e && e.name === 'AbortError') return false; }
  }
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
  return true;
}
/* zapis dowolnego pliku: okno programu (.exe), artefakt (pobieranie) albo przeglądarka */
async function saveAny(name, content, mime, filter, okMsg, b64) {
  if (inHost()) {
    let payload = content, isB64 = false;
    if (b64) { let s = ''; for (let i = 0; i < content.length; i += 0x8000) s += String.fromCharCode.apply(null, content.subarray(i, i + 0x8000)); payload = btoa(s); isB64 = true; }
    const r = await hostCall('save', { path: '', name, content: payload, b64: isB64, filter }); if (r && r.ok) toast((okMsg || 'Zapisano') + ': ' + baseName(r.path)); else if (r && r.err) toast('Błąd: ' + r.err);
    return;
  }
  const data = b64 ? new Blob([content], { type: mime }) : content;
  if (ART) { await offerFile(name, data, (okMsg || 'Plik') + ' pobrany.'); return; }
  await download(name, data, mime);
}
U.saveAny = saveAny;
async function saveFile(as) {
  if (inHost()) {
    const r = await hostCall('save', { path: as ? '' : filePath, name: safeName('.kwst'), content: projectJSON(), filter: 'project' });
    if (r && r.ok) { filePath = r.path; dirty = false; updateTitle(); autosave(); toast('Zapisano: ' + baseName(filePath)); } else if (r && r.err) toast('Błąd zapisu: ' + r.err);
  } else if (ART) {
    if (Cap.col && !as) { await cloudSave(false); return; }
    if (await offerFile(safeName('.kwst'), projectJSON(), 'Plik projektu pobrany.')) { dirty = false; updateTitle(); }
    else if (!Cap.dl && !Cap.col) toast('Zapis niedostępny w tym widoku – zmiany są pamiętane tylko w tej przeglądarce.', 4000);
  } else if (await download(safeName('.kwst'), projectJSON(), 'application/json') !== false) { dirty = false; updateTitle(); }
}
function applyState(st, path, quiet) {
  S = st; filePath = path || ''; dirty = false; prevStat = null;
  $('#projName').value = S.info.name || '';
  renderInputs(); recalc(); updateTitle(); autosave();
  if (!quiet) toast('Wczytano: ' + (baseName(path) || S.info.name || 'projekt'));
}
function loadProject(text, path) {
  let p; try { p = parseProject(text); } catch (e) { toast(e.message, 4000); return; }
  cloudId = null; cloudName = ''; applyState(p, path);
}
async function openFile() {
  if (dirty && !(await ask('Niezapisane zmiany zostaną utracone. Otworzyć inny projekt?', 'Otwórz'))) return;
  if (inHost()) { const r = await hostCall('open', { filter: 'project' }); if (r && r.ok) loadProject(r.content, r.path); else if (r && r.err) toast('Błąd odczytu: ' + r.err); }
  else { const inp = $('#fileIn'); inp.value = ''; inp.onchange = () => { const f = inp.files[0]; if (!f) return; f.text().then(t => loadProject(t, f.name)); }; inp.click(); }
}
async function newProject() {
  if (dirty && !(await ask('Niezapisane zmiany zostaną utracone. Utworzyć nowy projekt?', 'Nowy projekt'))) return;
  cloudId = null; cloudName = ''; S = defaultProject(); filePath = ''; dirty = false; prevStat = null;
  $('#projName').value = S.info.name; renderInputs(); recalc(); updateTitle(); autosave();
}
function doPrint() {
  if (ART) { U.selectTab('report'); window.WV.exportHTML(); return; }
  U.selectTab('report'); setTimeout(() => window.print(), 120);
}
/* moje projekty (artefakt: konto użytkownika) */
async function initCapabilities() {
  if (!ART || !window.claude || typeof window.claude.use !== 'function') return;
  window.claude.use('downloads').then(dl => { Cap.dl = dl || null; $('#bExport').hidden = !Cap.dl; rendered.report = false; }, () => { /* */ });
  try {
    const [db, user] = await Promise.all([window.claude.use('db'), window.claude.use('user')]);
    if (!db || !user) return; const uid = await user.id(); if (!uid) return;
    Cap.db = db; Cap.col = db.collection('data/users/' + uid); $('#bCloud').hidden = false;
    const tmo = setTimeout(() => { if (!Cap.ready) { Cap.slow = true; renderCloud(); } }, 10000);
    Cap.col.orderBy('saved', 'desc').onSnapshot(snap => { Cap.list = snap.docs.filter(d => d.exists).map(d => Object.assign({ id: d.id }, d.data())); if (!snap.metadata.fromCache) { Cap.ready = true; Cap.slow = false; clearTimeout(tmo); } renderCloud(); },
      e => { Cap.err = e && e.code; Cap.ready = true; clearTimeout(tmo); renderCloud(); });
  } catch (e) { /* bez zapisu na koncie */ }
}
const fmtDate = iso => { try { const d = new Date(iso); return d.toLocaleDateString('pl-PL') + ' ' + d.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; } };
let cloudOpen = false;
function openCloud() { cloudOpen = true; renderCloud(); $('#modal').style.display = 'flex'; }
function renderCloud() {
  if (!cloudOpen) return;
  const m = $('#modal'); let list;
  if (Cap.err) list = `<p class="pempty">Nie udało się odczytać zapisanych projektów (${esc(Cap.err)}). Zapis do pliku nadal działa.</p>`;
  else if (!Cap.ready && !Cap.list.length) list = `<p class="pempty">${Cap.slow ? 'Nie można teraz połączyć się z zapisanymi projektami. Spróbuj za chwilę.' : 'Wczytywanie zapisanych projektów…'}</p>`;
  else if (!Cap.list.length) list = `<p class="pempty">Nie masz jeszcze zapisanych projektów. Kliknij „Zapisz bieżący”, aby zapisać wspornik na swoim koncie – będzie dostępny na każdym urządzeniu, na którym otworzysz tę stronę.</p>`;
  else list = `<ul class="plist">${Cap.list.map(p => `<li class="${p.id === cloudId ? 'cur' : ''}"><div class="pn"><b>${esc(p.name || 'bez nazwy')}</b><small>zapisano ${esc(fmtDate(p.saved))}${p.summary ? ' · ' + esc(p.summary) : ''}</small></div><button class="btn" data-po="${esc(p.id)}">Otwórz</button><button class="btn dng" data-pd="${esc(p.id)}">Usuń</button></li>`).join('')}</ul>`;
  m.innerHTML = `<div class="dlg"><h3>Moje projekty</h3><p>Projekty zapisane na Twoim koncie claude.ai – widoczne tylko dla Ciebie.</p><div class="dbtn" style="justify-content:flex-start;margin-top:8px"><button class="btn pri" id="pcSave">${cloudId ? 'Zapisz zmiany' : 'Zapisz bieżący'}</button>${cloudId ? '<button class="btn" id="pcNew">Zapisz jako nowy</button>' : ''}${Cap.dl ? '<button class="btn" id="pcFile">Pobierz plik .kwst</button>' : ''}</div>${list}<div class="dbtn"><button class="btn" id="pcClose">Zamknij</button></div></div>`;
  m.style.display = 'flex';
  $('#pcClose', m).onclick = () => { cloudOpen = false; m.style.display = 'none'; };
  $('#pcSave', m).onclick = () => cloudSave(false);
  if ($('#pcNew', m)) $('#pcNew', m).onclick = () => cloudSave(true);
  if ($('#pcFile', m)) $('#pcFile', m).onclick = () => offerFile(safeName('.kwst'), projectJSON(), 'Plik projektu pobrany.');
  $$('[data-po]', m).forEach(b => b.onclick = () => cloudLoad(b.dataset.po));
  $$('[data-pd]', m).forEach(b => b.onclick = () => cloudDelete(b.dataset.pd));
}
function summaryLine() { const g = V().geometry, r = g.right; return `${g.layout === 'double' ? 'dwustronny' : 'jednostronny'} b×h_c = ${g.b}×${r.h_c} mm, l_c = ${r.l_c} mm, ${V().materials.concrete}` + (R && R.verdict ? ' · ' + R.verdict.title : ''); }
let cloudBusy = false;
async function cloudSave(asNew) {
  if (!Cap.col || cloudBusy) return; cloudBusy = true;
  const ref = (!asNew && cloudId) ? Cap.col.doc(cloudId) : Cap.col.doc();
  const body = JSON.parse(JSON.stringify({ app: 'KrotkiWspornikST', version: 1, name: S.info.name || 'bez nazwy', saved: new Date().toISOString(), summary: summaryLine(), project: JSON.parse(projectJSON()) }));
  try {
    try { await ref.set(body); } catch (e) { if (e && e.code === 'unavailable') { await new Promise(r => setTimeout(r, 400 + Math.random() * 600)); await ref.set(body); } else throw e; }
    cloudId = ref.id; cloudName = body.name; dirty = false; updateTitle(); autosave(); toast('Zapisano na koncie: ' + body.name); renderCloud();
  } catch (e) { const c = e && e.code; toast(c === 'quota_exceeded' ? 'Brak miejsca na kolejne projekty – usuń niepotrzebne.' : 'Nie udało się zapisać' + (c ? ` (${c})` : '') + '.', 4000); }
  finally { cloudBusy = false; }
}
async function cloudLoad(id) {
  const p = Cap.list.find(x => x.id === id); if (!p) return;
  if (dirty && id !== cloudId && !(await ask('Niezapisane zmiany zostaną utracone. Otworzyć projekt „' + esc(p.name || '') + '”?', 'Otwórz'))) { renderCloud(); return; }
  cloudOpen = false; $('#modal').style.display = 'none';
  let st; try { st = parseProject(JSON.stringify(p.project)); } catch (e) { toast(e.message); return; }
  cloudId = p.id; cloudName = p.name || ''; applyState(st, '', true); toast('Otwarto: ' + (p.name || 'projekt'));
}
async function cloudDelete(id) {
  const p = Cap.list.find(x => x.id === id); if (!p) return;
  if (await ask(`Usunąć projekt „${esc(p.name || 'bez nazwy')}” z konta? Tej operacji nie można cofnąć.`, 'Usuń', true)) {
    try { await Cap.col.doc(id).delete(); if (id === cloudId) { cloudId = null; cloudName = ''; updateTitle(); autosave(); } toast('Usunięto projekt.'); } catch (e) { toast('Nie udało się usunąć projektu.'); }
  }
  openCloud();
}
function about() {
  const web = ART ? '<p>Wersja przeglądarkowa: projekty zapisujesz na swoim koncie („Moje projekty”) albo jako plik .kwst – ten sam plik otworzy program KrotkiWspornikST.exe. Ostatni stan jest pamiętany w tej przeglądarce.</p>' : '';
  openModal(`<h3>Krótki wspornik ST ${VER} – wsporniki krótkie metodą Strut-and-Tie</h3>
  <p>Projektowanie i sprawdzanie krótkich wsporników żelbetowych modelem kratownicowym (STM) wg PN-EN 1992-1-1 (6.5, zał. J.3, rozdz. 8, 9, 10.9.5) z parametrami krajowymi do potwierdzenia przez projektanta.</p>
  <ul><li><b>Model STM</b> – zał. J.3, rys. J.5: węzeł A (CCT) pod płytą, węzeł B (CCC) przy licu słupa, cięgno; wysokość strefy ściskanej x<sub>c</sub> dobierana jako najkorzystniejsze dopuszczalne pole naprężeń (1,0 ≤ tan θ ≤ 2,5); kontrola równowagi, stateczności i zgodności rozwiązania analitycznego z macierzowym; model ręczny dowolnej kratownicy.</li>
  <li><b>Sprawdzenia</b> – krzyżulce (6.55/6.56), węzły (6.60–6.62), docisk (6.63), rozłupywanie (6.58/6.59), cięgno, J.3(2), J.3(3), V<sub>Rd,c</sub>, 6.2.2(6), zakotwienia (8.4, 8.6), gięcie (8.3), otulina (4.4.1), odstępy (8.2), zbrojenie min./maks., połączenia prefabrykowane (10.9.5), rysy (7.3.3 – orientacyjnie).</li>
  <li><b>Zbrojenie</b> – dobór automatyczny: najmniejsze pole stali z wykonalnym zakotwieniem (pętle, odgięcia, pręt przyspawany), strzemiona poziome i pionowe; zestawienie stali; rysunek DXF.</li>
  <li><b>Statusy</b> – SPEŁNIONO / NIE SPEŁNIONO / WYMAGA OSOBNEJ WERYFIKACJI / NIE DOTYCZY; wynik pozytywny jest blokowany przy błędach krytycznych, modelu poza zakresem lub niepotwierdzonych NDP.</li></ul>
  <p>Dane – zakładka <b>Dane</b> (schemat obok formularza: kliknij element, przeciągnij uchwyty). Wyniki – <b>Model STM</b>, <b>Zbrojenie wspornika</b>, <b>Podsumowanie</b> (kliknij warunek – jak obliczono; podstawę – objaśnienie punktu normy). Warianty – zakładki nad schematem.</p>${web}
  <p>Skróty: F2 – raport, Ctrl+S – zapisz, Ctrl+O – otwórz${ART ? '' : ', Ctrl+P – drukuj raport'}.</p>
  <p style="font-size:12px;color:var(--ink3)">Program jest narzędziem pomocniczym. Wyniki wymagają weryfikacji przez osobę z odpowiednimi uprawnieniami budowlanymi. Lokalny model wspornika nie obejmuje sprawdzenia słupa, łożyska i elementów stalowych.</p>
  <div class="dbtn"><button class="btn pri" data-close>Zamknij</button></div>`);
}

/* ------------------------------------------------------------ start */
function init() {
  nlObs.observe(document.body, { childList: true, subtree: true });
  let saved = window.__AUTOSAVE || null;
  if (!saved) { try { saved = JSON.parse(localStorage.getItem('wspornik-autosave') || 'null'); } catch (e) { saved = null; } }
  S = defaultProject();
  if (saved && saved.state) { try { S = normalize(saved.state); filePath = saved.filePath || ''; cloudId = saved.cloudId || null; cloudName = saved.cloudName || ''; } catch (e) { S = defaultProject(); } }
  if (ART) { $('#bPrint').hidden = true; $('#bSaveAs').hidden = true; $('#bExport').hidden = true; }
  $('#projName').value = S.info.name || '';
  $('#projName').addEventListener('input', e => { S.info.name = e.target.value; dirty = true; updateTitle(); autosave(); rendered.report = false; });
  $$('.tabs button').forEach(b => b.addEventListener('click', () => { $$('.tabs button').forEach(x => x.classList.toggle('on', x === b)); $$('.pane').forEach(p => p.classList.toggle('on', p.id === 'p-' + b.dataset.tab)); renderActive(); }));
  $$('[data-act]').forEach(b => b.addEventListener('click', () => ({ new: newProject, open: openFile, save: () => saveFile(false), saveas: () => saveFile(true), cloud: openCloud, print: doPrint, exporthtml: () => window.WV.exportHTML(), about })[b.dataset.act]()));
  document.addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if (!ART && (e.key === 'F5' || (e.ctrlKey && k === 'r'))) { e.preventDefault(); return; }
    if ($('#modal').style.display === 'flex' && e.key !== 'Escape') return;
    if (e.ctrlKey && k === 's') { e.preventDefault(); saveFile(e.shiftKey); }
    else if (e.ctrlKey && k === 'o') { e.preventDefault(); openFile(); }
    else if (e.ctrlKey && k === 'n' && !ART) { e.preventDefault(); newProject(); }
    else if (e.ctrlKey && k === 'p') { e.preventDefault(); doPrint(); }
    else if (e.key === 'F2') { e.preventDefault(); U.selectTab('report'); }
    else if (e.key === 'Escape') { closeList(); cloudOpen = false; $('#modal').style.display = 'none'; }
  });
  $('#modal').addEventListener('mousedown', e => { if (e.target.id === 'modal' && !$('[data-a]', e.currentTarget)) { cloudOpen = false; e.currentTarget.style.display = 'none'; } });
  let rz = null, lastW = window.innerWidth;
  window.addEventListener('resize', () => { if (Math.abs(window.innerWidth - lastW) < 40) return; lastW = window.innerWidth; clearTimeout(rz); rz = setTimeout(() => { rendered = {}; renderActive(); }, 150); });
  renderInputs(); recalc(); renderInputs(); updateTitle(); initCapabilities();
}
Object.assign(U, {
  V, getS: () => S, setDirty: () => { dirty = true; updateTitle(); autosave(); },
  applyVariant: v => { S.variants[S.active] = normVariant(v); afterVariant(); },
  addVariant: v => { S.variants.push(normVariant(v)); S.active = S.variants.length - 1; afterVariant(); },
  selectTab: t => { const b = $(`.tabs button[data-tab="${t}"]`); if (b) b.click(); },
  projectJSON, VER, APP, DBL, normVariant,
});
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
