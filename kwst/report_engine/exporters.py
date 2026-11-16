"""Eksport danych i wyników: Excel (xlsx), CSV, JSON, DXF."""
from __future__ import annotations

import csv
import datetime as _dt
import json
import math

from ..core.serialization import to_dict
from ..core.units import Kind, fmt
from ..version import APP_NAME, __version__
from ..visualization_engine import build_scene, Scene, VIEW_LAYERS


def _num(v):
    if v is None:
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def checks_rows(result) -> list[list]:
    rows = [["Id", "Grupa", "Sprawdzenie", "Podstawa", "Charakter", "Wzór", "Podstawienie", "E_d", "R_d",
             "Jednostka bazowa", "eta", "Status", "Kombinacja", "Wniosek", "Uwagi"]]
    from ..core.units import BASE_UNIT
    for c in result.checks:
        rows.append([c.id, c.group, c.title, c.clause, c.basis.value, c.formula, c.substitution, _num(c.E_d),
                     _num(c.R_d), BASE_UNIT.get(c.kind, ""), _num(c.eta), c.status.value, c.combination,
                     c.conclusion, " | ".join(c.notes)])
    return rows


def export_csv_checks(result, path: str) -> str:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        for r in checks_rows(result):
            w.writerow(["" if v is None else (f"{v:.6g}".replace(".", ",") if isinstance(v, float) else v) for v in r])
    return path


def result_dict(result) -> dict:
    out = {
        "program": f"{APP_NAME} {__version__}", "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "edition": result.edition_id, "input_hash": result.input_hash, "fingerprint": result.fingerprint,
        "model_type": result.model_type, "governing_combination": result.governing,
        "verdict": {"code": result.verdict.code, "title": result.verdict.title, "text": result.verdict.text,
                    "positive": result.verdict.positive} if result.verdict else None,
        "checks": [to_dict(c) for c in result.checks],
        "messages": [{"level": m.level.value, "text": m.text, "ref": m.ref} for m in result.messages],
        "assumptions": result.assumptions, "limitations": result.limitations,
        "validation": [{"name": i.name, "ok": i.ok, "detail": i.detail} for i in result.validation],
        "params_used": result.params_used, "design_log": result.design_log,
        "units": {"force": "N", "length": "mm", "stress": "MPa", "moment": "N·mm", "area": "mm²"},
        "stm": {},
    }
    for name, sr in result.stm.items():
        d = {"nodes": [{"id": n.id, "x": n.x, "y": n.y} for n in sr.truss.nodes],
             "members": [{"id": m.id, "n1": m.n1, "n2": m.n2, "kind": m.kind,
                          "N": _num(sr.solution.forces.get(m.id))} for m in sr.truss.members],
             "reactions": {k: list(v) for k, v in sr.solution.reactions.items()},
             "status": sr.solution.status, "max_residual": sr.solution.max_residual, "sides": {}}
        for sd, sm in sr.sides.items():
            s, p = sm.state, sm.params
            d["sides"][sd] = {"V": p.V, "H": p.H, "x_c": s.x_c, "z0": s.z0, "xi_A": s.xi_A, "xi_B": s.xi_B,
                              "a_B": s.a_B, "theta_deg": s.theta_deg, "T": s.T, "C": s.C, "Fc": s.Fc,
                              "w_A": s.w_A, "w_B": s.w_B, "eta": {k: _num(v) for k, v in s.eta.items()},
                              "feasible": sm.feasible, "lever_arm_method": sm.search.get("method")}
        out["stm"][name] = d
    if result.main is not None:
        out["reinforcement"] = {
            "main": {"phi": result.main.phi, "n_per_layer": result.main.n, "layers": result.main.layers,
                     "As": result.main.As, "c_t": result.main.c_t,
                     "anchor_load": result.main_input.anchor_load, "anchor_column": result.main_input.anchor_column},
            "links": {sd: {"h_phi": ll.h_phi, "h_depths": ll.h_depths, "v_phi": ll.v_phi,
                           "v_positions": ll.v_positions, "i_count": ll.i_count} for sd, ll in result.links.items()},
            "schedule": [{"mark": b.mark, "description": b.description, "shape": b.shape, "phi": b.phi,
                          "count": b.count, "length_mm": b.length, "mass_kg": b.mass} for b in result.schedule],
        }
    return out


def export_json(project, variant, result, path: str) -> str:
    data = {"format": "KROTKI_WSPORNIK_ST_RESULTS", "project": to_dict(project), "variant": variant.name,
            "results": result_dict(result)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return path


def export_excel(project, variant, result, path: str) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    hdr_font = Font(bold=True)
    hdr_fill = PatternFill("solid", fgColor="DFE6EF")

    def sheet(ws, rows, widths=None):
        for r in rows:
            ws.append(r)
        for c in ws[1]:
            c.font = hdr_font
            c.fill = hdr_fill
        ws.freeze_panes = "A2"
        for i, w in enumerate(widths or [], start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")

    ws = wb.active
    ws.title = "Projekt"
    info = project.info
    v = result.verdict
    sheet(ws, [["Pozycja", "Wartość"], ["Program", f"{APP_NAME} {__version__}"], ["Projekt", info.name],
               ["Numer", info.number], ["Obiekt", info.object], ["Element", info.element], ["Wariant", variant.name],
               ["Projektant", info.designer], ["Sprawdzający", info.checker], ["Edycja normy", result.edition_title],
               ["NDP potwierdzone", "TAK" if variant.normative.ndp_confirmed else "NIE"],
               ["Model", result.model_type], ["Kombinacja decydująca", result.governing],
               ["Werdykt", v.title if v else ""], ["Opis werdyktu", v.text if v else ""],
               ["Odcisk danych", result.input_hash], ["Odcisk wyników", result.fingerprint]], [28, 100])
    ws = wb.create_sheet("Dane")
    rows = [["Ścieżka", "Wartość", "Jednostka"]]

    def walk(prefix, obj):
        d = to_dict(obj)

        def rec(pfx, val):
            if isinstance(val, dict):
                for k, x in val.items():
                    rec(f"{pfx}.{k}" if pfx else k, x)
            elif isinstance(val, list):
                rows.append([pfx, json.dumps(val, ensure_ascii=False)[:30000], ""])
            else:
                rows.append([pfx, val, ""])
        rec(prefix, d)
    for name in ("geometry", "materials", "reinforcement", "stm", "normative"):
        walk(name, getattr(variant, name))
    sheet(ws, rows, [50, 40, 12])
    ws = wb.create_sheet("Obciążenia")
    rows = [["Nazwa", "Strona", "Kategoria", "Charakter", "Źródło", "V [kN]", "H [kN]", "M [kNm]", "e_x [mm]",
             "e_y [mm]", "Opis"]]
    for a in variant.loads.actions:
        rows.append([a.name, a.side, a.category, a.nature, a.source, a.V / 1e3, a.H / 1e3, a.M / 1e6, a.e_x, a.e_y,
                     a.note])
    sheet(ws, rows, [12, 8, 10, 15, 22, 10, 10, 10, 10, 10, 50])
    ws = wb.create_sheet("Kombinacje")
    rows = [["Kombinacja", "Typ", "Mnożniki", "Strona", "V_Ed [kN]", "H_Ed [kN]", "e_x [mm]", "e_y [mm]"]]
    for c in result.combinations:
        for sd, sa in c.sides.items():
            rows.append([c.name, c.kind, ", ".join(f"{k}·{x:g}" for k, x in c.factors.items()), sd, sa.V / 1e3,
                         sa.H / 1e3, sa.e_x, sa.e_y])
    sheet(ws, rows, [30, 12, 40, 8, 12, 12, 10, 10])
    ws = wb.create_sheet("Model STM")
    rows = [["Kombinacja", "Element", "Id", "Dane", "Siła N [kN] (+rozc.)"]]
    for name, sr in result.stm.items():
        for n in sr.truss.nodes:
            rx, ry = sr.solution.reactions.get(n.id, (None, None))
            rows.append([name, "węzeł", n.id, f"x = {n.x:.2f} mm, y = {n.y:.2f} mm" +
                         (f"; R_x = {rx / 1e3:.2f} kN, R_y = {ry / 1e3:.2f} kN" if rx is not None else ""), None])
        for m in sr.truss.members:
            rows.append([name, "krzyżulec" if m.kind == "strut" else "cięgno", m.id, f"{m.n1}–{m.n2}",
                         _num(sr.solution.forces.get(m.id, 0.0) / 1e3)])
    sheet(ws, rows, [30, 12, 8, 60, 18])
    ws = wb.create_sheet("Sprawdzenia")
    sheet(ws, checks_rows(result), [16, 16, 50, 36, 22, 40, 70, 14, 14, 10, 8, 26, 20, 40, 40])
    from openpyxl.styles import Font as F2
    colors_ = {"SPEŁNIONO": "1E7E34", "NIE SPEŁNIONO": "C62828", "WYMAGA OSOBNEJ WERYFIKACJI": "B26A00",
               "NIE DOTYCZY": "6C757D"}
    for row in ws.iter_rows(min_row=2):
        st = row[11].value
        if st in colors_:
            row[11].font = F2(bold=True, color=colors_[st])
    ws = wb.create_sheet("Zbrojenie")
    rows = [["Poz.", "Opis", "Kształt", "φ [mm]", "Liczba", "Długość 1 szt. [m]", "Długość całk. [m]", "Masa [kg]"]]
    for b in result.schedule:
        rows.append([b.mark, b.description, b.shape, b.phi, b.count, round(b.length / 1000, 3),
                     round(b.total_length / 1000, 3), round(b.mass, 2)])
    if result.schedule:
        rows.append(["", "RAZEM", "", "", "", "", "", round(sum(b.mass for b in result.schedule), 2)])
    sheet(ws, rows, [6, 40, 36, 8, 8, 16, 16, 12])
    ws = wb.create_sheet("Parametry normowe")
    rows = [["Klucz", "Symbol", "Wartość", "Jednostka", "Źródło", "Kategoria", "Status", "Potwierdzony"]]
    for d in result.params_used:
        rows.append([d["key"], d["symbol"], d["value"], d["unit"], d["clause"], d["category"], d["status"],
                     "TAK" if d["confirmed"] else "NIE"])
    sheet(ws, rows, [18, 22, 10, 8, 40, 28, 40, 12])
    ws = wb.create_sheet("Założenia")
    rows = [["Rodzaj", "Treść"]] + [["Założenie", a] for a in result.assumptions] + \
        [["Ograniczenie", a] for a in result.limitations] + \
        [[m.level.value, m.text] for m in result.messages]
    sheet(ws, rows, [16, 140])
    wb.save(path)
    return path


# ---------------------------------------------------------------------------
# DXF
# ---------------------------------------------------------------------------
DXF_LAYERS = {
    "column": ("KWST_SLUP", 8), "outline": ("KWST_KONTUR", 7), "axes": ("KWST_OSIE", 9), "cover": ("KWST_OTULINA", 3),
    "plate": ("KWST_PLYTA", 8), "loads": ("KWST_OBCIAZENIA", 3), "dims": ("KWST_WYMIARY", 2),
    "rebar_main": ("KWST_ZBROJENIE_GL", 30), "links": ("KWST_STRZEMIONA", 82), "marks": ("KWST_OPISY", 7),
    "stm_struts": ("KWST_STM_KRZYZULCE", 1), "stm_ties": ("KWST_STM_CIEGNA", 5), "stm_nodes": ("KWST_STM_WEZLY", 7),
    "stm_zones": ("KWST_STM_STREFY", 6), "forces": ("KWST_STM_SILY", 7), "angles": ("KWST_STM_KATY", 30),
    "reactions": ("KWST_REAKCJE", 6), "stress": ("KWST_WYKORZYSTANIE", 4),
}


def export_dxf(variant, result, path: str, modes: tuple[str, ...] = ("geometry", "stm", "rebar")) -> str:
    """Eksport rysunków do DXF (R2010). Każdy widok jest przesunięty w poziomie; warstwy wg DXF_LAYERS."""
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for name, (lname, color) in DXF_LAYERS.items():
        if lname not in doc.layers:
            doc.layers.add(lname, color=color)
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[10.0, 6.0, -4.0])
    dx = 0.0
    for mode in modes:
        sc = build_scene(variant, result, mode)
        layers = set(VIEW_LAYERS[mode]) - {"handles"}
        x0, y0, x1, y1 = sc.bounds
        off = dx - x0
        _scene_to_dxf(msp, sc, layers, off)
        msp.add_text({"geometry": "GEOMETRIA", "stm": "MODEL STM", "rebar": "ZBROJENIE", "stress": "WYKORZYSTANIE"}
                     .get(mode, mode), height=30, dxfattribs={"layer": "KWST_OPISY"}).set_placement(
            (x0 + off, y1 + 40))
        dx += (x1 - x0) + 300.0
    doc.saveas(path)
    return path


def _scene_to_dxf(msp, sc: Scene, layers: set[str], off: float) -> None:
    from ezdxf.enums import TextEntityAlignment

    def P(p):
        return (p[0] + off, p[1])

    for pr in sc.prims:
        if pr.layer not in layers or pr.layer not in DXF_LAYERS:
            continue
        lay = DXF_LAYERS[pr.layer][0]
        att = {"layer": lay}
        if pr.dash:
            att["linetype"] = "DASHED"
        if pr.kind in ("line", "polyline") and len(pr.pts) >= 2:
            msp.add_lwpolyline([P(q) for q in pr.pts], dxfattribs=att)
        elif pr.kind == "polygon" and len(pr.pts) >= 3:
            msp.add_lwpolyline([P(q) for q in pr.pts], close=True, dxfattribs=att)
        elif pr.kind == "circle":
            msp.add_circle(P(pr.pts[0]), max(pr.radius, 1.0), dxfattribs=att)
        elif pr.kind == "arc":
            a0, da = pr.angles
            msp.add_arc(P(pr.pts[0]), pr.radius, a0, a0 + da, dxfattribs=att)
        elif pr.kind == "arrow":
            (ax, ay), (bx, by) = P(pr.pts[0]), P(pr.pts[1])
            msp.add_line((ax, ay), (bx, by), dxfattribs=att)
            L = math.hypot(bx - ax, by - ay) or 1.0
            ux, uy = (bx - ax) / L, (by - ay) / L
            hl = min(0.3 * L, 40.0)
            hw = hl * 0.4
            msp.add_solid([(bx, by), (bx - ux * hl - uy * hw, by - uy * hl + ux * hw),
                           (bx - ux * hl + uy * hw, by - uy * hl - ux * hw)], dxfattribs={"layer": lay})
        elif pr.kind == "text" and pr.text:
            t = msp.add_text(pr.text, height=max(8.0, pr.size * 2.2), dxfattribs={"layer": lay})
            align = {"c": TextEntityAlignment.MIDDLE_CENTER, "l": TextEntityAlignment.MIDDLE_LEFT,
                     "r": TextEntityAlignment.MIDDLE_RIGHT}.get(pr.anchor, TextEntityAlignment.MIDDLE_CENTER)
            t.set_placement(P(pr.pts[0]), align=align)
        elif pr.kind == "dim":
            (xa, ya), (xb, yb) = pr.pts
            dxv, dyv = xb - xa, yb - ya
            L = math.hypot(dxv, dyv) or 1.0
            nx, ny = -dyv / L, dxv / L
            o = pr.offset
            base = P((xa + nx * o, ya + ny * o))
            angle = math.degrees(math.atan2(dyv, dxv))
            dim = msp.add_linear_dim(base=base, p1=P((xa, ya)), p2=P((xb, yb)), angle=angle,
                                     dimstyle="EZDXF", override={"dimtxt": 14, "dimasz": 8},
                                     dxfattribs={"layer": lay})
            dim.render()
