"""Zestaw przypadków kontrolnych (wymaganie §14) — pełna analiza bez GUI."""
import copy
import pytest

from kwst.analysis import run_analysis
from kwst.core.model import Variant, LoadAction, Layout, ManualNode, ManualMember, ManualSupport, ManualLoad
from kwst.core.results import CheckStatus
from tests.helpers import direct_variant, check


def _manual_bars(v, phi=20.0, n=4, layers=1, load="bend_down", col="bend_down"):
    m = v.reinforcement.main
    m.auto = False
    m.phi, m.n_per_layer, m.layers, m.anchor_load, m.anchor_column = phi, n, layers, load, col


def test_01_vertical_load():
    v = direct_variant(V=400e3)
    r = run_analysis(v)
    assert r.verdict.code == "PASS_SCOPE", [c.id for c in r.checks if c.status == CheckStatus.FAIL]
    assert check(r, "H_EFFECT").status == CheckStatus.NA
    s = r.governing_stm.sides["R"].state
    assert r.governing_stm.solution.equilibrium_ok
    assert s.T == pytest.approx(s.Fc)       # brak H
    assert check(r, "TIE_R").status == CheckStatus.OK


def test_02_vertical_and_horizontal():
    r0 = run_analysis(direct_variant(V=400e3))
    r1 = run_analysis(direct_variant(V=400e3, H=80e3))
    T0 = r0.governing_stm.sides["R"].state.T
    T1 = r1.governing_stm.sides["R"].state.T
    assert T1 > T0 + 80e3 * 0.99
    assert check(r1, "H_EFFECT").status == CheckStatus.OK


def test_03_very_short_corbel():
    v = direct_variant(V=300e3, a_c=40.0)
    v.geometry.right.plate.length = 60.0
    v.stm.node_b_position = "face"
    _manual_bars(v)
    r = run_analysis(v)
    assert r.verdict.code == "OUT_OF_SCOPE"
    assert check(r, "STRUT_R_TANMAX").status == CheckStatus.VERIFY
    assert not r.verdict.positive


def test_04_long_outstand():
    v = direct_variant(V=200e3, l_c=900.0, a_c=750.0, h_e=550.0)
    _manual_bars(v, 25.0, 6)
    r = run_analysis(v)
    assert r.verdict.code == "OUT_OF_SCOPE"
    assert check(r, "J3_SCOPE_R").status == CheckStatus.VERIFY
    assert any("belk" in n.lower() for n in check(r, "STRUT_R_TANMIN").notes)


def test_05_critical_strut():
    v = direct_variant(V=750e3)
    v.materials.concrete = "C25/30"
    r = run_analysis(v)
    crit = r.critical()
    assert crit.id.startswith("STRUT_R")
    assert crit.status == CheckStatus.FAIL
    assert r.verdict.code == "FAIL"


def test_06_critical_node():
    v = direct_variant(V=320e3)
    v.geometry.right.plate.length = 60.0
    v.geometry.right.plate.width = 150.0
    v.stm.strut_limit = "6.55"      # krzyżulec bez rozciągania poprzecznego → decyduje węzeł (k₂·ν'·f_cd)
    r = run_analysis(v)
    crit = r.critical()
    assert crit.id == "NODE_A_R_BEAR"
    assert crit.status == CheckStatus.FAIL


def test_07_insufficient_reinforcement():
    v = direct_variant(V=400e3)
    _manual_bars(v, 12.0, 2)
    r = run_analysis(v)
    assert check(r, "TIE_R").status == CheckStatus.FAIL
    assert r.verdict.code == "FAIL"


def test_08_insufficient_anchorage():
    v = direct_variant(V=300e3)
    _manual_bars(v, 25.0, 4, load="straight", col="straight")
    r = run_analysis(v)
    assert check(r, "TIE_R").status == CheckStatus.OK
    assert check(r, "ANCH_LOAD_R").status == CheckStatus.FAIL
    assert r.verdict.code == "FAIL"


def test_09_wrong_geometry():
    v = direct_variant(V=300e3, a_c=500.0)
    r = run_analysis(v)
    assert r.verdict.code == "BLOCKED"
    assert any("a_c" in m.text for m in r.errors)
    v = direct_variant(V=300e3, h_e=700.0)
    assert run_analysis(v).verdict.code == "BLOCKED"


def _manual_variant():
    v = direct_variant(V=400e3)
    v.stm.mode = "manual"
    m = v.stm.manual
    m.nodes = [ManualNode("A", 450, -50), ManualNode("B", 200, -500), ManualNode("C", -150, -50)]
    m.members = [ManualMember("S", "A", "B", "strut", 150, 400), ManualMember("T", "A", "C", "tie", 0, 400, 1000)]
    m.supports = [ManualSupport("B", True, True, 150), ManualSupport("C", True, True, 0)]
    m.loads = [ManualLoad("A", 0, -400e3)]
    return v


def test_10_unstable_stm():
    v = _manual_variant()
    ok = run_analysis(v)
    assert check(ok, "MODEL_STABILITY").status == CheckStatus.OK
    v.stm.manual.supports = [ManualSupport("B", True, False, 150), ManualSupport("C", True, False, 0)]
    r = run_analysis(v)
    assert check(r, "MODEL_STABILITY").status == CheckStatus.FAIL
    assert r.verdict.code == "BLOCKED" and not r.verdict.positive


def test_11_applicability_boundary():
    v = direct_variant(V=300e3, a_c=300.0, l_c=450.0)
    v.stm.lever_arm = "user"
    v.stm.node_b_position = "face"
    _manual_bars(v, 20.0, 5)
    v.geometry.right.z0_user = 300.0          # tan θ = z0/a_c = 1,000
    r = run_analysis(v)
    c = check(r, "STRUT_R_TANMIN")
    assert c.eta == pytest.approx(1.0, abs=1e-9)
    assert c.status == CheckStatus.OK
    v.geometry.right.z0_user = 295.0          # tan θ < 1
    r2 = run_analysis(v)
    assert r2.verdict.code == "OUT_OF_SCOPE"


def test_12_impossible_bar_layout():
    v = direct_variant(V=300e3)
    _manual_bars(v, 25.0, 10)
    r = run_analysis(v)
    assert check(r, "SPACING_MAIN").status == CheckStatus.FAIL
    v2 = direct_variant(V=900e3)
    v2.geometry.b = 160.0
    v2.geometry.right.plate.width = 150.0
    r2 = run_analysis(v2)
    assert r2.verdict.code == "BLOCKED"
    assert any("brak wykonalnego" in m.text for m in r2.errors)


def test_double_corbel_symmetric():
    v = direct_variant(V=300e3)
    v.geometry.layout = Layout.DOUBLE
    v.loads.actions.append(LoadAction(name="EdL", side="L", nature="design", category="G", V=300e3))
    r = run_analysis(v)
    gs = r.governing_stm
    assert gs.sides["R"].state.T == pytest.approx(gs.sides["L"].state.T, rel=1e-9)
    assert abs(gs.solution.reactions["C"][0]) < 1e-3       # tie forces balance in column
    assert r.verdict.code in ("PASS_SCOPE", "CONDITIONAL")


def test_precast_bearing_not_auto_applied():
    v = direct_variant(V=300e3)
    v.geometry.construction = v.geometry.construction.PRECAST
    r = run_analysis(v)
    assert check(r, "PRECAST_BEARING_R").status == CheckStatus.VERIFY
    v.normative.confirmed_params = ["fRd_dry", "table_10_2"]
    r2 = run_analysis(v)
    assert check(r2, "PRECAST_BEARING_R").status in (CheckStatus.OK, CheckStatus.FAIL)


def test_ndp_unconfirmed_never_positive():
    v = direct_variant(V=400e3)
    v.normative.ndp_confirmed = False
    r = run_analysis(v)
    assert not r.verdict.positive
    assert r.verdict.code == "CONDITIONAL"
