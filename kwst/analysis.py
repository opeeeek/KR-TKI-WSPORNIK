"""Orkiestrator analizy: dane wejściowe → model STM → sprawdzenia → werdykt.

Funkcja :func:`run_analysis` jest deterministyczna i nie korzysta z GUI —
może być wywoływana w testach automatycznych.
"""
from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass, field

from . import stm_solver as ss
from .anchorage_engine import (AnchorageInput, AnchorageResult, anchorage_check, anchorage_length, mandrel_checks,
                               mandrel_min_table, ANCHOR_LABEL)
from .checks_common import make, n, kN, mm, mm2, MPa, SIDE_NAME
from .core.model import Variant, MainBarsInput, LinksInput, Layout, Construction, side_input
from .core.results import Check, CheckStatus, Basis, Message, Level, Verdict
from .core.units import Kind, bar_area
from .geometry_engine import GeometryModel, build_geometry
from .load_engine import evaluate_combinations, DesignCombination
from .material_engine import Materials, build_materials, MaterialError, node_limits
from .node_checks import node_checks, node_c_check, local_bearing_check, manual_member_checks
from .normative_parameters import (get_parameter_set, EditionNotImplemented, ParameterSet, TABLE_7_2N, TABLE_7_3N,
                                   TABLE_10_2)
from .reinforcement_design import (CoverResult, MainLayout, LinksLayout, BarMark, cover_requirements, main_layout,
                                   links_layout, links_crossing_strut, cover_checks, spacing_checks, vrdc,
                                   j3_link_checks, min_max_checks, design_main_bars, design_links, bar_schedule,
                                   s_min)
from .stm_generator import StmResult, build_corbel_model, build_manual_model
from .strut_checks import strut_checks, splitting_check
from .tie_checks import tie_checks
from .validation_engine import validate_input, post_validate, hash_obj, result_fingerprint, ValidationItem

log = logging.getLogger("kwst.analysis")

STRENGTH_GROUPS = {"Krzyżulce", "Węzły", "Cięgna", "Docisk", "Rozłupywanie", "Zakotwienie",
                   "Zbrojenie poprzeczne", "Mechanizmy dodatkowe", "Połączenia prefabrykowane"}
STATUS_RANK = {CheckStatus.FAIL: 3, CheckStatus.VERIFY: 2, CheckStatus.OK: 1, CheckStatus.NA: 0}

LIMITATIONS = [
    "Lokalny model STM wspornika NIE obejmuje sprawdzenia słupa (nośność przekroju, węzeł słupa, zbrojenie "
    "podłużne i poprzeczne słupa) — reakcje modelu przekazywane na słup wymagają osobnej weryfikacji.",
    "Płyta stalowa, łożysko (elastomerowe), spoiny, kotwy i inne elementy stalowe — poza zakresem programu "
    "(EN 1993, EN 1337).",
    "Skręcanie wspornika i słupa od mimośrodu poprzecznego e_y — poza zakresem (uwzględniono jedynie redukcję "
    "szerokości efektywnej).",
    "Stan graniczny użytkowalności: wyłącznie uproszczona kontrola rys cięgna (tabl. 7.2N/7.3N bez korekt); "
    "ugięcia nie są sprawdzane.",
    "Obciążenia dynamiczne, zmęczenie, sytuacja pożarowa, obciążenia sejsmiczne — poza zakresem.",
    "Model płaski (2D) — przestrzenny rozkład naprężeń uwzględniono przez grubości efektywne t_A, t_B.",
    "Wsporniki, dla których a_c ≥ z0 (tan θ < 1), nie są krótkimi wspornikami wg J.3 — należy je projektować "
    "jak belki wspornikowe (6.1, 6.2); program nie wykonuje takiego wymiarowania.",
    "Węzły w trójosiowym ściskaniu (6.5.4(6), k₄) — nie są stosowane automatycznie.",
]


@dataclass
class AnalysisResult:
    variant_name: str
    edition_id: str = ""
    edition_title: str = ""
    materials: Materials | None = None
    geometry: GeometryModel | None = None
    cover: CoverResult | None = None
    main: MainLayout | None = None
    main_input: MainBarsInput | None = None
    links_input: LinksInput | None = None
    links: dict[str, LinksLayout] = field(default_factory=dict)
    combinations: list[DesignCombination] = field(default_factory=list)
    stm: dict[str, StmResult] = field(default_factory=dict)
    governing: str = ""
    checks: list[Check] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=lambda: list(LIMITATIONS))
    design_log: list[str] = field(default_factory=list)
    schedule: list[BarMark] = field(default_factory=list)
    anchorage: dict[str, AnchorageResult] = field(default_factory=dict)
    mandrels: dict[str, float] = field(default_factory=dict)
    verdict: Verdict | None = None
    validation: list[ValidationItem] = field(default_factory=list)
    params_used: list[dict] = field(default_factory=list)
    input_hash: str = ""
    fingerprint: str = ""
    model_type: str = ""
    sls: dict = field(default_factory=dict)
    geometry_signature: tuple = ()

    @property
    def errors(self) -> list[Message]:
        return [m for m in self.messages if m.level == Level.ERROR]

    def critical(self) -> Check | None:
        """Element krytyczny — maksymalne wykorzystanie spośród sprawdzeń nośności (bez wymagań
        konstrukcyjnych spełnianych z definicji, np. minimalna średnica trzpienia)."""
        def strength(c: Check) -> bool:
            return c.group in STRENGTH_GROUPS and not c.id.endswith(("_T81", "_LEG"))
        cands = [c for c in self.checks if strength(c) and c.eta is not None and
                 c.status in (CheckStatus.OK, CheckStatus.FAIL) and math.isfinite(c.eta)]
        fails_inf = [c for c in self.checks if c.status == CheckStatus.FAIL and
                     (c.eta is None or not math.isfinite(c.eta))]
        if fails_inf:
            return fails_inf[0]
        return max(cands, key=lambda c: c.eta) if cands else None

    @property
    def governing_stm(self) -> StmResult | None:
        return self.stm.get(self.governing)

    def checks_by_group(self) -> dict[str, list[Check]]:
        out: dict[str, list[Check]] = {}
        for c in self.checks:
            out.setdefault(c.group, []).append(c)
        return out


# ---------------------------------------------------------------------------
def _side_inputs(v: Variant) -> dict:
    out = {}
    for sd in (["R", "L"] if v.geometry.layout == Layout.DOUBLE else ["R"]):
        si = side_input(v.geometry, sd)
        out[sd] = {"a_H_user": si.a_H_user, "d_user": si.d_user,
                   "x_c_user": si.x_c_user if v.stm.lever_arm == "user" else None,
                   "z0_user": si.z0_user if v.stm.lever_arm == "user" else None}
    return out


def _merge(agg: dict[str, Check], c: Check) -> None:
    old = agg.get(c.id)
    if old is None:
        agg[c.id] = c
        return
    r_new, r_old = STATUS_RANK[c.status], STATUS_RANK[old.status]
    if r_new > r_old or (r_new == r_old and (c.eta or 0.0) > (old.eta or 0.0)):
        agg[c.id] = c


def _blocked(res: AnalysisResult, ndp: bool = False) -> AnalysisResult:
    res.verdict = Verdict.build(res.checks, res.errors, ndp)
    res.fingerprint = result_fingerprint(res)
    return res


def run_analysis(v: Variant) -> AnalysisResult:
    res = AnalysisResult(v.name)
    res.input_hash = hash_obj(v)
    try:
        ps = get_parameter_set(v.normative)
    except (EditionNotImplemented, KeyError, ValueError) as exc:
        res.messages.append(Message(Level.ERROR, str(exc), "normative", "parametry normowe"))
        return _blocked(res)
    res.edition_id = ps.edition.id
    res.edition_title = ps.edition.title
    res.messages += validate_input(v)
    try:
        res.geometry = build_geometry(v.geometry)
        res.geometry_signature = res.geometry.signature()
    except Exception as exc:  # noqa: BLE001
        res.messages.append(Message(Level.ERROR, f"Błąd geometrii: {exc}"))
    if res.errors:
        return _blocked(res, v.normative.ndp_confirmed)
    try:
        res.materials = build_materials(v.materials, ps)
    except MaterialError as exc:
        res.messages.append(Message(Level.ERROR, str(exc), "materials"))
        return _blocked(res, v.normative.ndp_confirmed)
    combos, cmsgs, cass = evaluate_combinations(v.loads, v.geometry, ps)
    res.combinations = combos
    res.messages += cmsgs
    res.assumptions += cass
    if res.errors:
        return _blocked(res, v.normative.ndp_confirmed)
    try:
        if v.stm.mode == "manual":
            _run_manual(v, res, ps)
        else:
            _run_auto(v, res, ps)
    except ss.StmModelError as exc:
        res.messages.append(Message(Level.ERROR, f"Model STM: {exc}", "stm"))
    except Exception as exc:  # noqa: BLE001 — błędy są raportowane, nie ukrywane
        log.exception("Błąd analizy")
        res.messages.append(Message(Level.ERROR, f"Błąd wewnętrzny obliczeń: {type(exc).__name__}: {exc}"))
    res.params_used = [ps.describe(k) for k in sorted(ps.used)]
    if not v.normative.ndp_confirmed:
        res.messages.append(Message(Level.WARNING, "Parametry NDP nie zostały potwierdzone przez projektanta "
                                                   "(zakładka Parametry normowe) — wynik ma charakter warunkowy."))
    res.validation = post_validate(res)
    for it in res.validation:
        if not it.ok:
            res.messages.append(Message(Level.ERROR, f"Walidacja automatyczna: {it.name} — {it.detail}", "validation"))
    res.verdict = Verdict.build(res.checks, res.errors, v.normative.ndp_confirmed)
    res.fingerprint = result_fingerprint(res)
    return res


# ---------------------------------------------------------------------------
# Tryb automatyczny (model J.3)
# ---------------------------------------------------------------------------
def _anchor_geometry(gm: GeometryModel, side: str, cv: CoverResult) -> dict:
    sg = gm.sides[side]
    col_near = gm.column_cover + gm.column_phi_link + gm.column_phi_long / 2.0
    col_far_inner = gm.h_col - gm.column_cover - gm.column_phi_link - gm.column_phi_long
    return {
        "load_start": sg.plate.xi_inner,
        "load_end": sg.l_c - cv.c_nom,
        "col_start": -col_near,
        "col_end": -col_far_inner,
        "l_load": sg.l_c - cv.c_nom - sg.plate.xi_inner,
        "l_col": col_far_inner - col_near,
    }


def _mandrel_and_ab(ml: MainLayout, cv: CoverResult, anchor: str, user_m: float | None, ps: ParameterSet
                    ) -> tuple[float, float, str]:
    tmin = mandrel_min_table(ml.phi, ps)
    if anchor == "loop":
        k = ml.n // 2
        cc = (ml.z_positions[k] - ml.z_positions[k - 1]) if ml.n >= 2 else 0.0
        phi_m = cc - ml.phi
        ab = cv.c_top_main + ml.phi / 2.0
        if ml.layers > 1:
            ab = min(ab, (ml.phi + ml.gap_v) / 2.0)
        return phi_m, ab, f"pętla najbardziej wewnętrzna: rozstaw osiowy ramion {cc:.0f} mm"
    phi_m = user_m if user_m is not None else tmin
    ab = min(ml.s_cc / 2.0 if ml.n >= 2 else math.inf, cv.c_side_main + ml.phi / 2.0)
    return phi_m, ab, "przyjęta średnica trzpienia" if user_m is not None else "φ_m = φ_m,min wg tabl. 8.1N"


@dataclass
class _AnchorSetup:
    """Geometria zakotwień jednej strony (długości mierzone wzdłuż osi pręta, rys. 8.1a)."""
    load: AnchorageInput
    col: AnchorageInput
    load_desc: str
    col_desc: str
    load_bend: tuple | None = None      # (φ_m, a_b, opis, r, prosta, łuk, ramię_max, ramię_użytk_lub_None)
    col_bend: tuple | None = None
    ext: float = 0.0


def _anchor_setup(gm: GeometryModel, side: str, ml: MainLayout, cv: CoverResult, mb: MainBarsInput, T: float,
                  links: LinksLayout | None, ps: ParameterSet, double: bool, dT: float) -> _AnchorSetup:
    geo = _anchor_geometry(gm, side, cv)
    sg = gm.sides[side]
    sum_Ast = 0.0
    if links is not None and mb.alpha3_mode == "computed":
        sum_Ast = sum(2.0 * bar_area(links.v_phi) for x in links.v_positions
                      if geo["load_start"] <= x <= geo["load_end"])
    base = dict(phi=ml.phi, As_prov=ml.As, force=T, a_clear=ml.a_clear if ml.n >= 2 else 1e6,
                c1=cv.c_side_main, c=cv.c_top_main, bond=mb.bond, alpha3_mode=mb.alpha3_mode, K=mb.K_alpha3,
                sum_Ast=sum_Ast, phi_t=mb.welded_bar_phi, s_cc=ml.s_cc if ml.n >= 2 else 0.0)
    ext = ps.v("hook_extension") * ml.phi
    load_bend = None
    l_load = geo["l_load"]
    load_desc = (f"od wewnętrznej krawędzi płyty (ξ = {geo['load_start']:.0f} mm) do zewnętrznej krawędzi pręta "
                 f"(ξ = {geo['load_end']:.0f} mm)")
    if mb.anchor_load == "bend_down":
        phi_m, ab, how = _mandrel_and_ab(ml, cv, "bend_down", mb.mandrel_load, ps)
        r = (phi_m + ml.phi) / 2.0
        straight = geo["l_load"] - (r + ml.phi / 2.0)
        arc = math.pi * r / 2.0
        leg_max = sg.h_e - cv.c_nom - ml.phi / 2.0 - (cv.c_top_main + ml.phi / 2.0 + r)
        load_bend = (phi_m, ab, how, r, straight, arc, leg_max, mb.front_leg)
        l_load = straight + arc + max(0.0, min(leg_max, mb.front_leg if mb.front_leg is not None else leg_max))
        load_desc = ("wzdłuż osi pręta od wewnętrznej krawędzi płyty: odcinek prosty + łuk + ramię pionowe "
                     "(rys. 8.1a)")
    elif mb.anchor_load == "loop":
        load_bend = _mandrel_and_ab(ml, cv, "loop", None, ps) + (0.0, 0.0, 0.0, 0.0, None)
    a_load = AnchorageInput(id=f"ANCH_LOAD_{side}", title=f"Zakotwienie zbrojenia głównego od strony obciążenia "
                            f"({SIDE_NAME[side]})", anchor=mb.anchor_load, l_avail=l_load,
                            element_ref=f"member:T{side}", **base)
    col_bend = None
    if double:
        a_col = AnchorageInput(id="ANCH_COL_DT", title="Przekazanie różnicy sił cięgien w słupie (pręty ciągłe)",
                               anchor="continuous", l_avail=gm.h_col - 2.0 * gm.column_cover,
                               element_ref="node:C", **{**base, "force": dT})
        col_desc = "szerokość słupa w świetle otulin (pręty ciągłe przez słup)"
    else:
        l_col = geo["l_col"]
        col_desc = ("od prętów pionowych przy bliższej krawędzi słupa do zewnętrznej krawędzi pręta przy dalszej "
                    "krawędzi (wewnątrz prętów słupa) — J.3(4)")
        if mb.anchor_column == "bend_down":
            phi_m, ab, how = _mandrel_and_ab(ml, cv, "bend_down", mb.mandrel_column, ps)
            r = (phi_m + ml.phi) / 2.0
            straight = geo["l_col"] - (r + ml.phi / 2.0)
            arc = math.pi * r / 2.0
            leg_max = gm.below + sg.h_c - ml.c_t - r
            col_bend = (phi_m, ab, how, r, straight, arc, leg_max, mb.column_leg)
            l_col = straight + arc + max(0.0, min(leg_max, mb.column_leg if mb.column_leg is not None else leg_max))
            col_desc = ("wzdłuż osi pręta od prętów pionowych przy bliższej krawędzi słupa: odcinek poziomy + łuk + "
                        "ramię pionowe w słupie (rys. 8.1a, J.3(4))")
        a_col = AnchorageInput(id=f"ANCH_COL_{side}", title="Zakotwienie zbrojenia głównego w słupie",
                               anchor=mb.anchor_column, l_avail=l_col, element_ref=f"member:T{side}", **base)
    return _AnchorSetup(a_load, a_col, load_desc, col_desc, load_bend, col_bend, ext)


def _anchor_capacity(a: AnchorageInput, mats: Materials, ps: ParameterSet) -> float:
    """Największa siła, dla której l_bd ≤ l_dost (bisekcja; l_bd rośnie monotonicznie z σ_sd)."""
    if a.anchor in ("mechanical",) or a.As_prov <= 0:
        return math.inf
    Fmax = a.As_prov * mats.steel.fyd

    def ok(F: float) -> bool:
        return anchorage_length(AnchorageInput(**{**a.__dict__, "force": F}), mats, ps).lbd <= a.l_avail + 1e-9
    if ok(Fmax):
        return math.inf
    if not ok(1e-3):
        return 0.0
    lo, hi = 0.0, Fmax
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if ok(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _anchor_caps(gm, ml, cv, mb, mats, ps, double) -> dict[str, float]:
    caps = {}
    for sd in gm.sides:
        su = _anchor_setup(gm, sd, ml, cv, mb, 0.0, None, ps, double, 0.0)
        c = _anchor_capacity(su.load, mats, ps)
        if not double:
            c = min(c, _anchor_capacity(su.col, mats, ps))
        caps[sd] = c
    return caps


def _bend_checks(prefix: str, title: str, bend: tuple, ml: MainLayout, Fbt: float, mats, ps, combo, ref,
                 lbd: float | None, ext: float, depth_label: str) -> tuple[list[Check], float]:
    """Sprawdzenia gięcia (tabl. 8.1N, (8.1)) i mieszczenia się ramienia; zwraca (checks, przyjęte ramię)."""
    phi_m, ab, how, r, straight, arc, leg_max, leg_user = bend
    out = mandrel_checks(prefix, f"{title} ({how})", ml.phi, phi_m, Fbt, ab, mats, ps, combo, ref)
    if leg_max <= 0 and straight == 0 and arc == 0:
        return out, 0.0     # pętla — bez ramienia
    if leg_user is not None:
        leg = leg_user
    else:
        need = (lbd - straight - arc) if lbd is not None else ext
        leg = math.ceil(max(ext, need) / 10.0) * 10.0
        leg = min(leg, max(leg_max, 0.0)) if leg > leg_max else leg
    out.append(make(prefix + "_LEG", "Wykonalność", f"{title} — ramię pionowe za odgięciem",
                    "EN 1992-1-1 §8.4.1, rys. 8.1b (przedłużenie ≥ 5φ); geometria elementu", Basis.NORMATIVE,
                    "5φ ≤ l_ramienia ≤ l_ramienia,max",
                    {"l_ramienia,max": depth_label},
                    f"l_ramienia = {mm(leg)} (min. 5φ = {mm(ext)}; max = {mm(leg_max)})",
                    max(ext, leg), max(leg_max, 0.0) if leg >= ext - 1e-9 else leg, Kind.LENGTH, combo, ref,
                    E_label="wymagane", R_label="dostępne"))
    return out, leg


def _anchorage_checks(v: Variant, gm: GeometryModel, side: str, ml: MainLayout, cv: CoverResult, mb: MainBarsInput,
                      T: float, mats: Materials, ps: ParameterSet, combo: str, links: LinksLayout | None,
                      double: bool, dT: float = 0.0) -> tuple[list[Check], dict[str, AnchorageResult], bool, str,
                                                              dict[str, float]]:
    """Komplet sprawdzeń zakotwienia i gięcia dla jednej strony. Zwraca (checks, wyniki, ok, przyczyna, geometria)."""
    checks: list[Check] = []
    results: dict[str, AnchorageResult] = {}
    sg = gm.sides[side]
    geo = _anchor_geometry(gm, side, cv)
    su = _anchor_setup(gm, side, ml, cv, mb, T, links, ps, double, dT)
    reason = ""
    info: dict[str, float] = {}
    sigma = min(T / ml.As, mats.steel.fyd) if ml.As > 0 else 0.0
    Fbt = sigma * bar_area(ml.phi)
    # --- strona obciążenia --------------------------------------------------
    lbd_load = anchorage_length(su.load, mats, ps).lbd if su.load.anchor != "mechanical" else None
    if su.load_bend is not None and su.load.anchor == "bend_down":
        cs, leg = _bend_checks(f"MANDREL_LOAD_{side}", "Gięcie zbrojenia głównego w dół na końcu wspornika",
                               su.load_bend, ml, Fbt, mats, ps, combo, f"member:T{side}", lbd_load, su.ext,
                               "wysokość końca wspornika minus otuliny i promień gięcia")
        _, _, _, r, straight, arc, leg_max, _ = su.load_bend
        su.load.l_avail = straight + arc + max(0.0, min(leg, leg_max))
        info.update({"load": su.load_bend[0], "leg_front": leg})
        checks += cs
    elif su.load_bend is not None:
        phi_m, ab, how = su.load_bend[:3]
        info["load"] = phi_m
        checks += mandrel_checks(f"MANDREL_LOAD_{side}", f"Gięcie pętli zbrojenia głównego ({how})", ml.phi, phi_m,
                                 Fbt, ab, mats, ps, combo, f"member:T{side}")
    c1, r1 = anchorage_check(su.load, mats, ps, combo, "; zał. J.3(4), §6.5.4(7)")
    c1.notes.append("Długość dostępna: " + su.load_desc + f" = {su.load.l_avail:.0f} mm.")
    checks.insert(0, c1)
    if r1:
        results[f"load_{side}"] = r1
    if c1.status == CheckStatus.FAIL:
        reason = "l_bd > l_dost (strona obciążenia)"
    # --- strona słupa -------------------------------------------------------
    lbd_col = anchorage_length(su.col, mats, ps).lbd if su.col.anchor != "mechanical" else None
    if su.col_bend is not None:
        cs, leg = _bend_checks(f"MANDREL_COL_{side}", "Gięcie zbrojenia głównego w słupie", su.col_bend, ml, Fbt,
                               mats, ps, combo, "node:C", lbd_col, su.ext, "długość słupa poniżej wspornika")
        _, _, _, r, straight, arc, leg_max, _ = su.col_bend
        su.col.l_avail = straight + arc + max(0.0, min(leg, leg_max))
        info.update({"column": su.col_bend[0], "leg_col": leg})
        checks += cs
    c2, r2 = anchorage_check(su.col, mats, ps, combo, "; zał. J.3(4)")
    c2.notes.append("Długość dostępna: " + su.col_desc + f" = {su.col.l_avail:.0f} mm.")
    checks.insert(1, c2)
    if r2:
        results[c2.id] = r2
    if c2.status == CheckStatus.FAIL and not reason:
        reason = "l_bd > l_dost (strona słupa)"
    if any(c.status == CheckStatus.FAIL for c in checks[2:]) and not reason:
        bad = next(c for c in checks[2:] if c.status == CheckStatus.FAIL)
        reason = bad.title
    if mb.anchor_load == "loop" and ml.n % 2:
        checks.append(make(f"FIT_LOOP_{side}", "Wykonalność", "Pętle poziome — parzysta liczba prętów",
                           "Zasady konstruowania", Basis.NORMATIVE, "n parzyste", {}, f"n = {ml.n}", None, None,
                           Kind.NONE, combo, f"member:T{side}", status=CheckStatus.FAIL))
        reason = reason or "nieparzysta liczba prętów dla pętli"
    # zbrojenie musi obejmować cały węzeł A (6.5.4(7))
    checks.append(make(f"NODE_A_ANCH_{side}", "Zakotwienie",
                       "Zbrojenie główne przechodzi przez cały węzeł A (poza zewnętrzną krawędź płyty)",
                       "EN 1992-1-1 §6.5.4(7)", Basis.NORMATIVE, "ξ_koniec pręta ≥ ξ_zewn. krawędź płyty", {},
                       f"ξ_koniec = {mm(geo['load_end'])}; ξ_płyta,zewn = {mm(sg.plate.xi_outer)}",
                       sg.plate.xi_outer, geo["load_end"], Kind.LENGTH, combo, f"node:A{side}",
                       E_label="ξ_płyta", R_label="ξ_pręt"))
    if checks[-1].status == CheckStatus.FAIL and not reason:
        reason = "pręty nie obejmują węzła A"
    return checks, results, not reason, reason, info


def _design_T(gm, combos, mats, ps, st, c_t, side_inputs) -> dict[str, float]:
    Tm: dict[str, float] = {}
    for c in combos:
        r = build_corbel_model(gm, c, mats, ps, st, c_t, None, True, side_inputs)
        errs = [m for m in r.messages if m.level == Level.ERROR]
        if errs:
            raise ss.StmModelError(errs[0].text)
        for sd, sm in r.sides.items():
            Tm[sd] = max(Tm.get(sd, 0.0), sm.state.T)
        for sd, act in c.sides.items():
            if act.V <= 1e-6 and act.H > 0:
                Tm[sd] = max(Tm.get(sd, 0.0), act.H)
    return Tm


def _run_auto(v: Variant, res: AnalysisResult, ps: ParameterSet) -> None:
    gm = res.geometry
    mats = res.materials
    st = v.stm
    ri = v.reinforcement
    double = v.geometry.layout == Layout.DOUBLE
    uls = [c for c in res.combinations if c.is_uls]
    sls = [c for c in res.combinations if c.kind == "SLS_QP"]
    side_inputs = _side_inputs(v)
    mb = copy.deepcopy(ri.main)
    li = copy.deepcopy(ri.links)
    if double:
        mb.anchor_column = "continuous"
    fyd = mats.steel.fyd
    res.model_type = "J.3 — wsporniki dwustronne" if double else "J.3 — wspornik jednostronny"
    res.assumptions += _model_assumptions(v, ps)
    T_cache: dict[float, dict[str, float]] = {}

    def as_req(c_t: float) -> float:
        key = round(c_t, 6)
        if key not in T_cache:
            T_cache[key] = _design_T(gm, uls, mats, ps, st, c_t, side_inputs)
        return max(T_cache[key].values()) / fyd if T_cache[key] else 0.0

    links_lay: dict[str, LinksLayout] = {}
    prev_sig = None
    for outer in range(4):
        cv = cover_requirements(v.materials, ps, mb.phi, li.h_phi, li.v_phi, li.v_count > 0, li.h_count > 0)
        if ri.main.auto:
            dlog: list[str] = []

            def anchor_ok(ml: MainLayout, anchor: str) -> tuple[bool, str]:
                Tm = T_cache.get(round(ml.c_t, 6)) or _design_T(gm, uls, mats, ps, st, ml.c_t, side_inputs)
                trial = copy.deepcopy(mb)
                trial.anchor_load = anchor
                for sd in gm.sides:
                    dT = abs(Tm.get("R", 0.0) - Tm.get("L", 0.0)) if double else 0.0
                    _, _, ok, why, _ = _anchorage_checks(v, gm, sd, ml, cv_c(ml.phi), trial, Tm.get(sd, 0.0), mats, ps,
                                                         "", None, double, dT)
                    if not ok:
                        return False, why
                return True, ""

            def cv_c(phi: float) -> CoverResult:
                return cover_requirements(v.materials, ps, phi, li.h_phi, li.v_phi, li.v_count > 0, li.h_count > 0)

            cand = design_main_bars(gm, v.materials, ri, ps, as_req, anchor_ok, dlog)
            if cand is None:
                res.design_log += dlog
                reasons = []
                for line in dlog:
                    if " (" in line and ")" in line:
                        r_ = line[line.index(" (") + 2:line.rindex(")")]
                        if r_ not in reasons:
                            reasons.append(r_)
                res.messages.append(Message(Level.ERROR, "Automatyczny dobór zbrojenia głównego: brak wykonalnego "
                                                         "układu prętów. Przyczyny: " + "; ".join(reasons[:4]) +
                                            ". Zmień geometrię (wysięg, wysokość końca, położenie płyty), typ "
                                            "zakotwienia, klasę betonu lub dobierz zbrojenie ręcznie.",
                                            "reinforcement.main"))
                return
            mb.phi, mb.n_per_layer, mb.layers, mb.anchor_load = cand.phi, cand.n, cand.layers, cand.anchor_load
            cv = cv_c(mb.phi)
            if outer == 0:
                res.design_log += dlog
            res.design_log.append(f"Przyjęto zbrojenie główne: {cand.layout.desc()} (A_s = {cand.layout.As:.0f} mm² "
                                  f"≥ A_s,req = {cand.As_req:.0f} mm²), kotwienie: {ANCHOR_LABEL[cand.anchor_load]}.")
        ml = main_layout(gm.b, cv, mb.phi, mb.n_per_layer, mb.layers, mb.layer_gap, v.materials.d_g, ps)
        # nośność zakotwień jako dodatkowe kryterium doboru pola naprężeń (x_c)
        caps = _anchor_caps(gm, ml, cv, mb, mats, ps, double)
        side_chk = {sd: {**side_inputs.get(sd, {}), "T_anch": caps.get(sd)} for sd in gm.sides}
        # sprawdzenie modelu dla wszystkich kombinacji SGN przy przyjętym zbrojeniu
        stm = {c.name: build_corbel_model(gm, c, mats, ps, st, ml.c_t, ml.As, False, side_chk) for c in uls}
        gov = _governing(stm)
        # strzemiona
        if ri.links.auto:
            li = _auto_links(v, gm, ml, cv, li, stm, mats, ps, res.design_log, side_inputs)
        links_lay = _links_layouts(v, gm, ml, cv, li, stm.get(gov), ps)
        sig = (mb.phi, mb.n_per_layer, mb.layers, li.h_phi, li.h_count, li.v_phi, li.v_count)
        if sig == prev_sig or (not ri.main.auto and not ri.links.auto):
            break
        prev_sig = sig
    # komplet sprawdzeń (z iteracyjnym zwiększaniem strzemion przy doborze automatycznym)
    for _ in range(8):
        checks = _all_checks(v, res, ps, gm, mats, cv, ml, mb, li, links_lay, stm, uls, sls, side_chk, double)
        if not ri.links.auto:
            break
        need_more = [c for c in checks if c.status == CheckStatus.FAIL and
                     (c.id.startswith("SPLIT_") or c.id.startswith("J32_"))]
        need_v = [c for c in checks if c.status == CheckStatus.FAIL and c.id.startswith("J33_")]
        if not need_more and not need_v:
            break
        if need_more:
            li.h_count += 1
        if need_v:
            li.v_count += 1
        res.design_log.append(f"Korekta doboru strzemion: poziome {li.h_count}×φ{li.h_phi:.0f}, "
                              f"pionowe {li.v_count}×φ{li.v_phi:.0f}.")
        links_lay = _links_layouts(v, gm, ml, cv, li, stm.get(_governing(stm)), ps)
    res.cover, res.main, res.main_input, res.links_input, res.links, res.stm = cv, ml, mb, li, links_lay, stm
    res.governing = _governing(stm)
    res.checks = checks
    try:
        res.schedule = bar_schedule(gm, v.geometry, ml, links_lay, cv, mb, res.mandrels.get("load", 0.0) or
                                    mandrel_min_table(ml.phi, ps), res.mandrels.get("column", 0.0) or
                                    mandrel_min_table(ml.phi, ps), v.materials.steel_name, mb.welded_bar_phi)
    except Exception as exc:  # noqa: BLE001
        res.messages.append(Message(Level.WARNING, f"Zestawienie stali niekompletne: {exc}"))


def _governing(stm: dict[str, StmResult]) -> str:
    best, gname = -1.0, ""
    for name, r in stm.items():
        for sm in r.sides.values():
            e = sm.state.eta_max()
            if e > best:
                best, gname = e, name
    return gname or (next(iter(stm)) if stm else "")


def _links_layouts(v, gm, ml, cv, li, gov_res: StmResult | None, ps) -> dict[str, LinksLayout]:
    out = {}
    for sd in gm.sides:
        sm = gov_res.sides.get(sd) if gov_res else None
        d = sm.params.d if sm else gm.sides[sd].h_c - ml.c_t
        xi_A = sm.state.xi_A if sm else gm.sides[sd].a_c
        out[sd] = links_layout(gm, sd, ml, cv, li, d, xi_A, v.materials.d_g, ps)
    return out


def _auto_links(v, gm, ml, cv, li, stm, mats, ps, dlog, side_inputs) -> LinksInput:
    from .strut_checks import splitting_force
    k1, k2 = ps.v("J3_k1"), ps.v("J3_k2")
    fywd = mats.steel.link_fyd
    need_h = need_v = split = 0.0
    sin_t, cos_t = 1.0, 0.0
    room_h = room_v = 0
    for sd, sg in gm.sides.items():
        for r in stm.values():
            sm = r.sides.get(sd)
            if not sm:
                continue
            s = sm.state
            strut = next((x for x in r.struts if x.id == f"S{sd}"), None)
            if strut and strut.shape == "butelkowy":
                T = max(splitting_force(s.C, a, strut.b_avail, strut.length)[0] for a in (s.w_A, s.w_B))
                if T > split:
                    split, sin_t, cos_t = T, math.sin(s.theta), math.cos(s.theta)
            if sg.a_c > 0.5 * sg.h_c:
                Vc, _ = vrdc(gm.b, sm.params.d, ml.As, max(sm.params.H, 0.0), sg.h_c, mats, ps)
                if sm.params.V > Vc:
                    need_v = max(need_v, k2 * sm.params.V / fywd)
        if sg.a_c < 0.5 * sg.h_c:
            need_h = max(need_h, k1 * ml.As)
        d = sg.h_c - ml.c_t
        zone = (li.h_zone if li.h_zone is not None else ps.v("h_link_zone") * d)
        y_first = ml.layer_depths[-1] + ml.phi / 2.0 + ml.s_min
        y_end = min(ml.c_t + zone, sg.h_c - cv.c_nom - 8.0)
        pitch = 16.0 + s_min(16.0, v.materials.d_g, ps)
        rh = int(max(0.0, (y_end - y_first)) // pitch) + 1 if y_end >= y_first else 0
        room_h = rh if room_h == 0 else min(room_h, rh)
        x_span = sg.a_c - (cv.c_nom + 25.0)
        rv = int(max(0.0, x_span) // pitch) + 1 if x_span > 0 else 0
        room_v = rv if room_v == 0 else min(room_v, rv)
    return design_links(need_h, need_v, split, sin_t, cos_t, fywd, li, room_h, room_v, dlog)


def _model_assumptions(v: Variant, ps: ParameterSet) -> list[str]:
    st = v.stm
    a = [
        "Model STM wg EN 1992-1-1 zał. J.3, rys. J.5: węzeł A (CCT) pod obciążeniem na osi cięgna, węzeł B (CCC) "
        "w strefie ściskanej przy licu słupa, cięgno zakotwione w słupie.",
        ("Węzeł B umieszczony w słupie (pozioma ścianka węzła przekazuje V na słup), ξ_B = −a_B/2 — założenie "
         "inżynierskie (konserwatywne względem rys. J.5)." if st.node_b_position == "in_column"
         else "Węzeł B na licu słupa (ξ_B = 0) — zgodnie z rys. J.5."),
        {"optimal": "Wysokość strefy ściskanej x_c dobierana jako najkorzystniejsze dopuszczalne pole naprężeń "
                    "(minimalizacja maksymalnego wykorzystania przy 1,0 ≤ tan θ ≤ 2,5) — twierdzenie o dolnej "
                    "ocenie nośności.",
         "node_limit": "Wysokość strefy ściskanej x_c z warunku σ_B = min(σ_Rd,max węzła CCC; σ_Rd,max krzyżulca).",
         "user": "Wysokość strefy ściskanej x_c / ramię z0 przyjęte przez użytkownika."}[st.lever_arm],
        f"Nośność krzyżulca wg {'(6.56): 0,6·ν′·f_cd (strefa zarysowana)' if st.strut_limit == '6.56' else '(6.55): f_cd'}.",
        "Siła pozioma H przyłożona na górnej powierzchni płyty oporowej (a_H = c_t + t_p), wypadkowa (V, H) "
        "przecina oś cięgna w węźle A." if st.include_aH else "Pominięto ramię a_H siły poziomej.",
        "Korzystne działanie siły H skierowanej do słupa jest pomijane." if st.neglect_favourable_H else
        "Uwzględniono siłę H skierowaną do słupa (zmniejsza siłę w cięgnie).",
        f"Warunki przyczepności zbrojenia głównego: {'dobre (η₁ = 1,0)' if v.reinforcement.main.bond == 'good' else 'słabe (η₁ = 0,7) — założenie konserwatywne dla prętów górnych'}.",
        "Grubość efektywna węzła A i krzyżulca przy A równa szerokości płyty oporowej b_p (bez rozchodzenia w "
        "kierunku szerokości) — założenie bezpieczne.",
    ]
    if st.node_10pct and st.node_10pct_justification.strip():
        a.append("Zwiększenie σ_Rd,max węzłów o 10% (6.5.4(5)) — uzasadnienie: " + st.node_10pct_justification)
    return a


def _all_checks(v, res, ps, gm, mats, cv, ml, mb, li, links_lay, stm, uls, sls, side_inputs, double) -> list[Check]:
    agg: dict[str, Check] = {}
    st = v.stm
    T_max: dict[str, float] = {}
    V_max: dict[str, tuple[float, float, float]] = {}
    dT = 0.0
    fywd = mats.steel.link_fyd
    res.messages = [m for m in res.messages if m.source != "model"]
    seen_msgs: set[str] = set()

    def msg(level, text, ref=""):
        if text not in seen_msgs:
            seen_msgs.add(text)
            res.messages.append(Message(level, text, ref, "model"))

    for c in uls:
        r = stm[c.name]
        for m in r.messages:
            msg(m.level, f"[{c.name}] {m.text}", m.ref)
        sol = r.solution
        if sol.status != "error":
            st_ok = sol.stable
            _merge(agg, make("MODEL_STABILITY", "Model", "Stateczność / wyznaczalność modelu kratownicowego",
                             "EN 1992-1-1 §5.6.4, §6.5.1 — kontrola modelu", Basis.MODEL,
                             "rank(A) = liczba równań; stopień niewyznaczalności m + r − 2w",
                             {"A": "macierz równowagi węzłów"},
                             f"rank(A) = {sol.rank}, równań {sol.n_equations}, niewiadomych {sol.n_unknowns}, "
                             f"stopień = {sol.degree}; status: {sol.status}",
                             None, None, Kind.NONE, c.name, "model",
                             status=CheckStatus.OK if st_ok else CheckStatus.FAIL,
                             conclusion="Model geometrycznie niezmienny i statycznie wyznaczalny." if sol.status ==
                             "determinate" else ("Model niewyznaczalny — siły zależne od sztywności." if st_ok else
                                                 "Model ZMIENNY — wynik pozytywny zablokowany.")))
            tol = sol.tolerance
            resid = max(sol.max_residual, abs(sol.global_residual[0]), abs(sol.global_residual[1]))
            _merge(agg, make("MODEL_EQUILIBRIUM", "Model", "Residuum równowagi węzłów i równowaga globalna",
                             "Kontrola numeryczna modelu", Basis.MODEL, "max|A·f + P| ≤ tol; ΣF = 0; ΣM = 0", {},
                             f"max residuum = {resid:.3e} N; tol = {tol:.3e} N; ΣM = {sol.global_residual[2]:.3e} N·mm; "
                             f"różnica rozw. analitycznego i macierzowego = {r.comparison.get('max_rel_diff', 0):.2e}",
                             resid, tol, Kind.FORCE, c.name, "model", E_label="residuum", R_label="tol"))
        for sd, sm in r.sides.items():
            s, p = sm.state, sm.params
            strut = next(x for x in r.struts if x.id == f"S{sd}")
            for ck in strut_checks(sm, strut, mats, ps, st, c.name):
                if ck.id.endswith("TANMIN") or ck.id.endswith("TANMAX"):
                    ck = make(ck.id, ck.group, ck.title, ck.clause, ck.basis, ck.formula, ck.symbols,
                              ck.substitution, ck.E_d, ck.R_d, ck.kind, ck.combination, ck.element_ref,
                              ["Niespełnienie oznacza, że model J.3 jest poza zakresem stosowania — wymagana "
                               "alternatywna metoda (belka wspornikowa 6.1/6.2 lub analiza nieliniowa / MES), "
                               "NIE wykonana przez program."], recommendation=True, E_label=ck.E_label,
                              R_label=ck.R_label)
                _merge(agg, ck)
            for ck in node_checks(sm, mats, ps, st, c.name):
                _merge(agg, ck)
            for ck in tie_checks(sm, ml.As, ml.desc(), ml.c_t, mats, ps, c.name):
                _merge(agg, ck)
            _merge(agg, local_bearing_check(gm, sm, mats, ps, c.name))
            ll = links_lay.get(sd)
            nh, nv = links_crossing_strut(ll, gm, sd, cv, s.xi_A, s.y_A, s.xi_B, s.y_B) if ll else (0, 0)
            R_links = (nh * 2.0 * bar_area(ll.h_phi) * fywd * math.sin(s.theta) +
                       nv * 2.0 * bar_area(ll.v_phi) * fywd * math.cos(s.theta)) if ll else 0.0
            desc = (f"{nh}×2·{n(bar_area(ll.h_phi) if ll else 0, 1)}·{n(fywd, 1)}·sin θ + "
                    f"{nv}×2·{n(bar_area(ll.v_phi) if ll else 0, 1)}·{n(fywd, 1)}·cos θ")
            ck, _ = splitting_check(sm, strut, R_links, desc, c.name)
            _merge(agg, ck)
            # zakres stosowania J.3
            _merge(agg, make(f"J3_SCOPE_{sd}", "Model", f"Zakres modelu krótkiego wspornika: a_c < z0 ({SIDE_NAME[sd]})",
                             "EN 1992-1-1 zał. J.3(1)", Basis.INFORMATIVE, "a_c < z0",
                             {"a_c": "odległość obciążenia od lica słupa", "z0": "ramię sił wewnętrznych"},
                             f"a_c,ef = {mm(p.xi_A, 1)} (z uwzgl. M i H·a_H); z0 = {mm(s.z0, 1)}",
                             p.xi_A, s.z0, Kind.LENGTH, c.name, f"member:S{sd}", recommendation=True,
                             E_label="a_c", R_label="z0",
                             notes=[] if sm.feasible else [sm.infeasible_reason]))
            if not sm.feasible:
                msg(Level.WARNING, f"Strona {sd}: {sm.infeasible_reason}", f"side:{sd}")
            # mieszczenie się pola naprężeń w obrysie
            cont = r.containment
            okc = all(cont.get(f"{k}_{sd}", True) for k in ("strut_lower", "strut_upper", "node_A", "node_B"))
            bad = [k for k in ("strut_lower", "strut_upper", "node_A", "node_B") if not cont.get(f"{k}_{sd}", True)]
            _merge(agg, make(f"CONTAIN_{sd}", "Model", f"Pole naprężeń mieści się w obrysie betonu ({SIDE_NAME[sd]})",
                             "Spójność geometrii modelu (6.5.1) — krzyżulce i węzły w obrysie", Basis.MODEL,
                             "krawędzie krzyżulca i strefy węzłowe w obrysie wspornika/słupa", {},
                             "Wszystkie elementy pola naprężeń leżą w obrysie." if okc else
                             "Poza obrysem: " + ", ".join(bad) + " — geometria (np. skos dolnej krawędzi) niezgodna "
                             "z przyjętym modelem.", None, None, Kind.NONE, c.name, f"member:S{sd}",
                             status=CheckStatus.OK if okc else CheckStatus.FAIL))
            # węzeł B w słupie
            if st.node_b_position == "in_column":
                lim = gm.h_col if not double else gm.h_col / 2.0
                _merge(agg, make(f"NODE_B_FIT_{sd}", "Model", f"Strefa węzła B{sd} mieści się w słupie",
                                 "Spójność geometrii modelu", Basis.MODEL,
                                 "a_B ≤ h_col (dwustronne: a_B ≤ h_col/2)", {},
                                 f"a_B = {mm(s.a_B, 1)}; limit = {mm(lim)}", s.a_B, lim, Kind.LENGTH, c.name,
                                 f"node:B{sd}", E_label="a_B", R_label="limit"))
            T_max[sd] = max(T_max.get(sd, 0.0), s.T)
            Vm = V_max.get(sd, (0.0, 0.0, 0.0))
            if p.V > Vm[0]:
                V_max[sd] = (p.V, p.H, p.d)
        if double:
            Ts = {sd: r.sides[sd].state.T for sd in r.sides}
            dT = max(dT, abs(Ts.get("R", 0.0) - Ts.get("L", 0.0)))
        Ttot = max((sm.state.T for sm in r.sides.values()), default=0.0)
        _merge(agg, node_c_check(Ttot, c.name, double))
        _merge(agg, _column_transfer(r, c.name, v))
    # pozostałe kombinacje: strony bez siły pionowej (T = H)
    for c in uls:
        for sd, act in c.sides.items():
            if act.V <= 1e-6 and act.H > 0:
                T_max[sd] = max(T_max.get(sd, 0.0), act.H)
    gov_name = _governing(stm)
    gov = stm.get(gov_name)
    # --- zakotwienia i gięcie ------------------------------------------------
    res.anchorage = {}
    res.mandrels = {}
    for sd in gm.sides:
        cks, ares, _, _, mand = _anchorage_checks(v, gm, sd, ml, cv, mb, T_max.get(sd, 0.0), mats, ps,
                                                  "obwiednia SGN", links_lay.get(sd), double, dT)
        for ck in cks:
            _merge(agg, ck)
        res.anchorage.update(ares)
        res.mandrels.update(mand)
    # --- otulina, rozstaw, minimum ------------------------------------------
    for ck in cover_checks(cv, ml.phi):
        _merge(agg, ck)
    for sd in gm.sides:
        for ck in spacing_checks(ml, links_lay.get(sd)):
            ck.id = ck.id if ck.id != "SPACING_LINKS" else f"SPACING_LINKS_{sd}"
            _merge(agg, ck)
    for sd, sg in gm.sides.items():
        d = sg.h_c - ml.c_t
        for ck in min_max_checks(gm.b, d, sg.h_c, ml.As, mats, ps):
            ck.id += f"_{sd}"
            _merge(agg, ck)
        if sd in V_max:
            Vd, Hd, dd = V_max[sd]
            Vc, vtxt = vrdc(gm.b, dd, ml.As, max(Hd, 0.0), sg.h_c, mats, ps)
            for ck in j3_link_checks(sd, sg.a_c, sg.h_c, Vd, Vc, vtxt, ml, links_lay[sd], mats, ps, "obwiednia SGN"):
                _merge(agg, ck)
            # 6.2.2(6)
            c_ = mats.concrete
            VRmax = ps.v("shear_max_factor") * gm.b * dd * c_.nu_shear * c_.fcd
            _merge(agg, make(f"SHEAR_MAX_{sd}", "Mechanizmy dodatkowe",
                             f"Graniczna siła poprzeczna przy licu słupa ({SIDE_NAME[sd]})",
                             "EN 1992-1-1 §6.2.2(6), wzory (6.5), (6.6N)", Basis.NORMATIVE,
                             "V_Ed ≤ 0,5·b_w·d·ν·f_cd;  ν = 0,6·(1 − f_ck/250)",
                             {"b_w": "szerokość wspornika", "d": "wysokość użyteczna przy licu"},
                             f"0,5·{n(gm.b, 0)}·{n(dd, 0)}·{n(c_.nu_shear, 3)}·{n(c_.fcd)} = {kN(VRmax)}; V_Ed = {kN(Vd)}",
                             Vd, VRmax, Kind.FORCE, "obwiednia SGN", f"member:S{sd}", E_label="V_Ed", R_label="V_Rd,max",
                             notes=["Sprawdzenie uzupełniające: obciążenie przyłożone w odległości ≤ 2d od podpory "
                                    "(słupa); nośność krzyżulców i węzłów sprawdzono w modelu STM."]))
            # wysokość pod zewnętrzną krawędzią płyty (zalecenie)
            h_out = sg.depth_at(sg.plate.xi_outer)
            ratio = ps.v("outer_depth_ratio")
            if v.normative.apply_engineering_recommendations:
                _merge(agg, make(f"OUTER_DEPTH_{sd}", "Konstrukcyjne",
                                 f"Wysokość wspornika pod zewnętrzną krawędzią płyty ({SIDE_NAME[sd]})",
                                 ps.param("outer_depth_ratio").clause, Basis.ENGINEERING,
                                 "h(ξ_płyta,zewn) ≥ 0,5·h_c", {},
                                 f"h = {mm(h_out)}; 0,5·h_c = {mm(ratio * sg.h_c)}", ratio * sg.h_c, h_out, Kind.LENGTH,
                                 "", f"node:A{sd}", recommendation=True, E_label="0,5·h_c", R_label="h_zewn"))
    # --- elementy poza zakresem / dodatkowe ---------------------------------
    for ck in _scope_checks(v, res, gm, mats, ps, ml, uls):
        _merge(agg, ck)
    # --- SGU: zarysowanie ---------------------------------------------------
    for ck in _sls_checks(v, res, gm, mats, ps, ml, cv, sls, gov, side_inputs):
        _merge(agg, ck)
    order = ["Model", "Krzyżulce", "Węzły", "Docisk", "Cięgna", "Rozłupywanie", "Zbrojenie poprzeczne",
             "Zakotwienie", "Konstrukcyjne", "Wykonalność", "Mechanizmy dodatkowe", "Połączenia prefabrykowane",
             "SGU", "Poza zakresem"]
    return sorted(agg.values(), key=lambda c: (order.index(c.group) if c.group in order else 99, c.id))


def _column_transfer(r: StmResult, combo: str, v: Variant) -> Check:
    parts = []
    for nid, (rx, ry) in sorted(r.solution.reactions.items()):
        parts.append(f"{nid}: R_x = {kN(rx)}, R_y = {kN(ry)}")
    N = v.geometry.column.N_Ed
    return make("COLUMN_TRANSFER", "Poza zakresem", "Przekazanie sił ze wspornika na słup",
                "EN 1992-1-1 §6.5, J.3(4); nośność słupa — rozdz. 6.1, 5.8", Basis.MODEL,
                "reakcje modelu lokalnego = obciążenie strefy słupa", {},
                "; ".join(parts) + (f"; N_Ed słupa = {kN(N)} (informacyjnie)" if N else ""),
                None, None, Kind.FORCE, combo, "node:C", status=CheckStatus.VERIFY,
                conclusion="Siły przekazywane na słup wymagają sprawdzenia słupa i jego strefy węzłowej — "
                           "wynik STM wspornika nie potwierdza nośności słupa.")


def _scope_checks(v: Variant, res: AnalysisResult, gm: GeometryModel, mats: Materials, ps: ParameterSet,
                  ml: MainLayout, uls: list[DesignCombination]) -> list[Check]:
    out: list[Check] = []
    H_any = any(abs(c.sides[sd].H) > 1e-6 for c in uls for sd in c.sides)
    ey_any = any(abs(c.sides[sd].e_y) > 1e-6 for c in uls for sd in c.sides)
    precast = v.geometry.construction == Construction.PRECAST
    Hmax = max((c.sides[sd].H for c in uls for sd in c.sides), default=0.0)
    if H_any:
        out.append(make("H_EFFECT", "Mechanizmy dodatkowe", "Wpływ siły poziomej H_Ed",
                        "EN 1992-1-1 zał. J.3, rys. J.5", Basis.INFORMATIVE,
                        "F_td = F_Ed·a_c/z0 + H_Ed·(a_H + z0)/z0 — uwzględnione w modelu", {},
                        f"Maksymalna siła pozioma w kombinacjach SGN: {kN(Hmax)} — uwzględniona w równowadze "
                        "węzła A i sile w cięgnie.", None, None, Kind.FORCE, "", "model", status=CheckStatus.OK,
                        conclusion="Wpływ siły poziomej uwzględniony w modelu STM."))
    elif precast and not v.geometry.precast.restraint_considered:
        out.append(make("H_EFFECT", "Mechanizmy dodatkowe", "Wpływ siły poziomej H_Ed (połączenie prefabrykowane)",
                        "EN 1992-1-1 §10.9.5 (oparcia elementów prefabrykowanych) — zalecenie", Basis.ENGINEERING,
                        "H_Ed od więzów (skurcz, pełzanie, temperatura)", {},
                        "Brak siły poziomej w połączeniu prefabrykowanym i brak potwierdzenia, że oddziaływania od "
                        "więzów zostały rozważone.", None, None, Kind.FORCE, "", "model", status=CheckStatus.VERIFY))
    else:
        out.append(make("H_EFFECT", "Mechanizmy dodatkowe", "Wpływ siły poziomej H_Ed", "EN 1992-1-1 zał. J.3",
                        Basis.INFORMATIVE, "—", {}, "Brak siły poziomej w kombinacjach SGN.", None, None,
                        Kind.FORCE, "", "model", status=CheckStatus.NA))
    out.append(make("TORSION", "Poza zakresem", "Skręcanie od mimośrodu poprzecznego", "EN 1992-1-1 §6.3",
                    Basis.NORMATIVE, "T_Ed = V_Ed·e_y", {},
                    "Występuje mimośród poprzeczny e_y — skręcanie wspornika i słupa wymaga osobnej weryfikacji."
                    if ey_any else "Brak mimośrodu poprzecznego.", None, None, Kind.MOMENT, "", "model",
                    status=CheckStatus.VERIFY if ey_any else CheckStatus.NA))
    out.append(make("PLATE_STEEL", "Poza zakresem", "Płyta oporowa / łożysko / spoiny",
                    "EN 1993-1-8, EN 1337", Basis.NORMATIVE, "—", {},
                    "Nośność płyty stalowej, łożyska i połączeń stalowych nie jest sprawdzana przez program.",
                    None, None, Kind.NONE, "", "model", status=CheckStatus.VERIFY))
    # 10.9.5 — oparcia prefabrykatów
    if precast:
        pc = v.geometry.precast
        keys = ["fRd_dry" if pc.dry_connection else "fRd_other", "table_10_2"]
        confirmed = all(ps.is_confirmed(k) for k in keys)
        c = mats.concrete
        for sd, sg in gm.sides.items():
            Vmax = max((cc.sides[sd].V for cc in uls if sd in cc.sides), default=0.0)
            if pc.dry_connection:
                fRd = ps.v("fRd_dry") * c.fcd
                ftxt = f"f_Rd = 0,4·f_cd = {MPa(fRd)} (połączenie na sucho)"
            else:
                fRd = min(pc.f_bed, ps.v("fRd_other") * c.fcd) if pc.f_bed > 0 else ps.v("fRd_other") * c.fcd
                ftxt = f"f_Rd = min(f_bed; 0,85·f_cd) = {MPa(fRd)}"
            b1 = sg.plate.width
            a1 = Vmax / (b1 * fRd) if fRd > 0 else math.inf
            rel = (Vmax / (sg.plate.length * b1)) / c.fcd
            col = 0 if rel <= 0.15 else (1 if rel <= 0.4 else 2)
            a1_min = TABLE_10_2[pc.support_type][col]
            a1_req = max(a1, a1_min)
            status = None if confirmed else CheckStatus.VERIFY
            out.append(make(f"PRECAST_BEARING_{sd}", "Połączenia prefabrykowane",
                            f"Długość oparcia netto a₁ elementu prefabrykowanego ({SIDE_NAME[sd]})",
                            "EN 1992-1-1 §10.9.5.2, wzór (10.6), tabl. 10.2", Basis.NORMATIVE,
                            "a₁ = F_Ed/(b₁·f_Rd) ≥ a₁,min (tabl. 10.2);  a₁ ≤ a_p",
                            {"b₁": "szerokość oparcia netto", "f_Rd": "obliczeniowa wytrzymałość na docisk"},
                            f"{ftxt}; a₁ = {kN(Vmax)}·10³/({n(b1, 0)}·{n(fRd)}) = {mm(a1, 1)}; σ_Ed/f_cd = {n(rel, 3)} → "
                            f"a₁,min = {mm(a1_min)}; a₁,req = {mm(a1_req, 1)}; a_p = {mm(sg.plate.length)}",
                            a1_req, sg.plate.length, Kind.LENGTH, "obwiednia SGN", f"node:A{sd}",
                            ["Wartości tabl. 10.2 i f_Rd wymagają potwierdzenia z treścią normy (parametry "
                             "'fRd_dry'/'fRd_other' w zakładce Parametry normowe). Odległości a₂, a₃ i tolerancje "
                             "Δa₂, Δa₃ (tabl. 10.3–10.5) — do sprawdzenia przez projektanta."],
                            status=status, E_label="a₁,req", R_label="a_p"))
        out.append(make("PRECAST_OTHER", "Połączenia prefabrykowane",
                        "Pozostałe wymagania połączeń prefabrykowanych (a₂, a₃, Δa, zabezpieczenie przed zsunięciem)",
                        "EN 1992-1-1 §10.9.4, §10.9.5", Basis.NORMATIVE, "—", {},
                        "Wymagania geometryczne oparcia (tabl. 10.3–10.5), przesunięcia i zabezpieczenia połączenia "
                        "wymagają osobnej weryfikacji.", None, None, Kind.NONE, "", "model", status=CheckStatus.VERIFY))
    else:
        out.append(make("PRECAST_BEARING", "Połączenia prefabrykowane", "Wymagania dla połączeń prefabrykowanych",
                        "EN 1992-1-1 §10.9.5", Basis.NORMATIVE, "—", {}, "Wspornik monolityczny.", None, None,
                        Kind.NONE, "", "model", status=CheckStatus.NA))
    if v.reinforcement.links.i_count == 0:
        out.append(make("J35_INCLINED", "Zbrojenie poprzeczne", "Strzemiona ukośne przy narożu wklęsłym (rysy)",
                        "EN 1992-1-1 zał. J.3(5)", Basis.INFORMATIVE, "—", {},
                        "Przy szczególnych wymaganiach ograniczenia rys skuteczne są strzemiona ukośne w narożu "
                        "wklęsłym — nie zastosowano (decyzja projektanta).", None, None, Kind.NONE, "", "rebar:links",
                        status=CheckStatus.NA))
    return out


def _interp(table: dict, sigma: float, col: int) -> float | None:
    keys = sorted(table)
    if sigma <= keys[0]:
        return table[keys[0]][col]
    if sigma > keys[-1]:
        return None
    for a, b in zip(keys, keys[1:]):
        if a <= sigma <= b:
            va, vb = table[a][col], table[b][col]
            if va is None or vb is None:
                return None
            return va + (vb - va) * (sigma - a) / (b - a)
    return None


def _sls_checks(v, res, gm, mats, ps, ml, cv, sls, gov: StmResult | None, side_inputs) -> list[Check]:
    out: list[Check] = []
    if not sls or gov is None:
        out.append(make("SLS_CRACK", "SGU", "Ograniczenie zarysowania cięgna", "EN 1992-1-1 §7.3", Basis.NORMATIVE,
                        "—", {}, "Brak kombinacji quasi-stałej SGU (obciążenia podane jako wartości obliczeniowe) "
                        "— kontrola rys nie została wykonana.", None, None, Kind.STRESS, "", "rebar:main",
                        status=CheckStatus.VERIFY))
        return out
    exp = v.materials.exposure
    wmax = ps.v("wmax_X0_XC1") if exp in ("X0", "XC1") else ps.v("wmax_other")
    col = {0.4: 0, 0.3: 1, 0.2: 2}.get(round(wmax, 1), 1)
    st_user = copy.deepcopy(v.stm)
    st_user.lever_arm = "user"
    for c in sls:
        si = {sd: {**side_inputs.get(sd, {}), "x_c_user": gov.sides[sd].state.x_c, "z0_user": None}
              for sd in gov.sides}
        r = build_corbel_model(gm, c, mats, ps, st_user, ml.c_t, ml.As, False, si)
        for sd, sm in r.sides.items():
            sig = sm.state.T / ml.As
            res.sls[f"{c.name}:{sd}"] = sig
            phi_max = _interp(TABLE_7_2N, sig, col)
            s_max = _interp(TABLE_7_3N, sig, col)
            ok_phi = phi_max is not None and ml.phi <= phi_max + 1e-9
            ok_s = s_max is not None and ml.s_cc <= s_max + 1e-9
            status = CheckStatus.OK if (ok_phi or ok_s) else CheckStatus.FAIL
            out.append(make(f"SLS_CRACK_{sd}", "SGU", f"Ograniczenie zarysowania — cięgno {SIDE_NAME[sd]} (uproszczone)",
                            "EN 1992-1-1 §7.3.3(2), tabl. 7.1N, 7.2N, 7.3N", Basis.NORMATIVE,
                            "φ ≤ φ*_s(σ_s) lub s ≤ s_max(σ_s);  σ_s = T_qp / A_s",
                            {"σ_s": "naprężenie w zbrojeniu w kombinacji quasi-stałej (x_c jak w SGN)"},
                            f"T_qp = {kN(sm.state.T)}; σ_s = {MPa(sig, 1)}; w_max = {n(wmax, 1)} mm → φ*_s = "
                            f"{'—' if phi_max is None else mm(phi_max, 1)} (φ = {mm(ml.phi)}), s_max = "
                            f"{'—' if s_max is None else mm(s_max, 0)} (s = {mm(ml.s_cc, 0)})",
                            None, None, Kind.STRESS, c.name, f"member:T{sd}", status=status,
                            notes=["Tablice zastosowano bez korekt (7.6N)/(7.7N) — kontrola orientacyjna; moduł "
                                   "o statusie 'nieweryfikowany'."]))
    return out


# ---------------------------------------------------------------------------
# Tryb ręczny
# ---------------------------------------------------------------------------
def _run_manual(v: Variant, res: AnalysisResult, ps: ParameterSet) -> None:
    man = v.stm.manual
    mats = res.materials
    res.model_type = "Model STM zdefiniowany ręcznie"
    res.assumptions.append("Model STM zdefiniowany ręcznie przez użytkownika — obciążenia węzłowe są wartościami "
                           "obliczeniowymi; kombinacje obciążeń projektu nie są stosowane do modelu ręcznego.")
    truss = build_manual_model(man)
    sol = ss.solve(truss)
    combo = "model ręczny"
    agg: dict[str, Check] = {}
    agg["MODEL_STABILITY"] = make("MODEL_STABILITY", "Model", "Stateczność / wyznaczalność modelu kratownicowego",
                                  "EN 1992-1-1 §5.6.4 — kontrola modelu", Basis.MODEL,
                                  "rank(A) = liczba równań", {},
                                  f"rank = {sol.rank}, równań {sol.n_equations}, niewiadomych {sol.n_unknowns}; "
                                  f"status: {sol.status}. " + " ".join(sol.messages),
                                  None, None, Kind.NONE, combo, "model",
                                  status=CheckStatus.OK if sol.stable else CheckStatus.FAIL)
    if sol.stable:
        resid = max(sol.max_residual, abs(sol.global_residual[0]), abs(sol.global_residual[1]))
        agg["MODEL_EQUILIBRIUM"] = make("MODEL_EQUILIBRIUM", "Model", "Residuum równowagi", "Kontrola numeryczna",
                                        Basis.MODEL, "max|A·f + P| ≤ tol", {},
                                        f"max residuum = {resid:.3e} N; tol = {sol.tolerance:.3e} N", resid,
                                        sol.tolerance, Kind.FORCE, combo, "model")
        for ck in manual_member_checks(truss, sol, man, mats, ps, v.stm, combo):
            agg[ck.id] = ck
        if sol.status == "indeterminate":
            res.messages.append(Message(Level.WARNING, "Model ręczny statycznie niewyznaczalny — siły zależą od "
                                                       "sztywności (EA krzyżulca = E·w·t, cięgna = E_s·A_s)."))
    else:
        res.messages.append(Message(Level.ERROR, "Model ręczny jest geometrycznie zmienny — " + " ".join(sol.messages)))
    agg["MANUAL_SCOPE"] = make("MANUAL_SCOPE", "Poza zakresem", "Sprawdzenia konstrukcyjne zbrojenia w trybie ręcznym",
                               "EN 1992-1-1 rozdz. 8, 9", Basis.NORMATIVE, "—", {},
                               "W trybie ręcznym zakotwienia, otulina, rozstaw i zbrojenie poprzeczne nie są "
                               "sprawdzane automatycznie.", None, None, Kind.NONE, combo, "model",
                               status=CheckStatus.VERIFY)
    from .stm_generator import StmResult as _SR
    res.stm = {combo: _SR(combo, "ręczny", truss, sol, {}, {}, [], [], {"max_rel_diff": 0.0})}
    res.governing = combo
    res.checks = sorted(agg.values(), key=lambda c: (c.group, c.id))
