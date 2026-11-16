import json
import os

import pytest

from kwst.analysis import run_analysis
from kwst.core.model import Project, Layout, LoadAction
from kwst.design_optimizer import optimize, OptSettings
from kwst.project_io import save_project, load_project, load_library
from kwst.report_engine.exporters import export_excel, export_csv_checks, export_json, export_dxf
from kwst.report_engine.pdf_report import generate_pdf
from kwst.visualization_engine import build_scene, verify_scene, VIEW_LAYERS
from tests.helpers import direct_variant


@pytest.fixture(scope="module")
def pr():
    p = Project()
    return p, p.current, run_analysis(p.current)


def test_pdf_report(pr, tmp_path):
    p, v, r = pr
    out = str(tmp_path / "r.pdf")
    generate_pdf(p, v, r, out)
    data = open(out, "rb").read()
    assert data[:4] == b"%PDF" and len(data) > 30_000


def test_pdf_negative_result_has_no_positive_conclusion(tmp_path):
    v = direct_variant(V=900e3)
    p = Project(variants=[v])
    r = run_analysis(v)
    assert not r.verdict.positive
    out = str(tmp_path / "neg.pdf")
    generate_pdf(p, v, r, out)
    import subprocess
    try:
        txt = subprocess.run(["pdftotext", out, "-"], capture_output=True, text=True, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("pdftotext niedostępny")
    assert "nie zawiera pozytywnego wniosku" in txt
    assert "SPEŁNIONO W ZAKRESIE PROGRAMU" not in txt


def test_exports(pr, tmp_path):
    p, v, r = pr
    export_excel(p, v, r, str(tmp_path / "a.xlsx"))
    export_csv_checks(r, str(tmp_path / "a.csv"))
    export_json(p, v, r, str(tmp_path / "a.json"))
    export_dxf(v, r, str(tmp_path / "a.dxf"))
    from openpyxl import load_workbook
    wb = load_workbook(str(tmp_path / "a.xlsx"))
    assert "Sprawdzenia" in wb.sheetnames and wb["Sprawdzenia"].max_row == len(r.checks) + 1
    d = json.load(open(tmp_path / "a.json", encoding="utf-8"))
    assert d["results"]["fingerprint"] == r.fingerprint
    import ezdxf
    doc = ezdxf.readfile(str(tmp_path / "a.dxf"))
    layers = {e.dxf.layer for e in doc.modelspace()}
    assert {"KWST_KONTUR", "KWST_STM_KRZYZULCE", "KWST_STM_CIEGNA", "KWST_ZBROJENIE_GL"} <= layers


def test_drawing_matches_model(pr):
    p, v, r = pr
    for mode in VIEW_LAYERS:
        sc = build_scene(v, r, mode)
        assert verify_scene(sc, r) == []
    # scena dla danych zmienionych po obliczeniach jest oznaczona jako nieaktualna i nie zawiera STM
    v2 = direct_variant(V=400e3)
    sc = build_scene(v2, None, "stm", stale=True)
    assert sc.stale and not any(pp.layer.startswith("stm_") for pp in sc.prims)


def test_drawing_detects_mismatch(pr):
    p, v, r = pr
    sc = build_scene(v, r, "stm")
    sc.node_coords["AR"] = (sc.node_coords["AR"][0] + 5.0, sc.node_coords["AR"][1])
    assert verify_scene(sc, r)


def test_double_corbel_drawing():
    v = direct_variant(V=300e3)
    v.geometry.layout = Layout.DOUBLE
    v.loads.actions.append(LoadAction(name="EdL", side="L", nature="design", category="G", V=200e3))
    r = run_analysis(v)
    sc = build_scene(v, r, "stm")
    assert verify_scene(sc, r) == []
    assert sc.bounds[0] < -v.geometry.column.h_col / 2 - v.geometry.right.l_c * 0.9


def test_project_file_roundtrip(tmp_path):
    p = Project()
    path = tmp_path / "x.kwst"
    save_project(p, path)
    q = load_project(path)
    assert run_analysis(q.current).fingerprint == run_analysis(p.current).fingerprint


def test_library_presets_valid():
    items = load_library()
    assert len(items) >= 4
    for it in items:
        r = run_analysis(it.variant)
        assert r.verdict.code in ("PASS_SCOPE", "CONDITIONAL"), (it.key, r.verdict.code,
                                                                 [m.text for m in r.errors][:2],
                                                                 [c.id for c in r.checks if c.status.value == "NIE SPEŁNIONO"])


def test_optimizer_variants_satisfy_all_checks():
    res = optimize(Project().current, OptSettings(objective="steel", h_c=(450, 650, 100), concretes=["C30/37"]))
    feas = [o for o in res if o.feasible]
    assert feas
    for o in feas:
        r = run_analysis(o.variant)
        assert not [c for c in r.checks if c.status.value == "NIE SPEŁNIONO"]
    objs = [o.objective for o in feas]
    assert objs == sorted(objs)
