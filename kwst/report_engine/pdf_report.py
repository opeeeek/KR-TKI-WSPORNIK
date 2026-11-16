"""Raport obliczeniowy PDF (A4) — pełna dokumentacja sprawdzeń z wzorami i podstawieniami.

Raport NIE zawiera pozytywnego wniosku ogólnego, jeżeli werdykt analizy nie jest pozytywny
(błędy krytyczne, niespełnione warunki, model poza zakresem, niepotwierdzone NDP).
"""
from __future__ import annotations

import datetime as _dt
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from xml.sax.saxutils import escape

from ..core.results import CheckStatus
from ..core.units import fmt, Kind
from ..palette import STATUS_COLORS, VERDICT_COLORS
from ..validation_engine import MODULE_STATUS
from ..version import APP_NAME, __version__
from ..visualization_engine import build_scene
from .drawing_pdf import scene_to_drawing

FONT_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"
_FONTS_OK = False


def register_fonts() -> None:
    global _FONTS_OK
    if _FONTS_OK:
        return
    pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSansMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold", italic="DejaVuSans",
                       boldItalic="DejaVuSans-Bold")
    _FONTS_OK = True


def _styles():
    base = dict(fontName="DejaVuSans", leading=11.5, fontSize=8.6)
    return {
        "title": ParagraphStyle("t", fontName="DejaVuSans-Bold", fontSize=17, leading=21, alignment=TA_CENTER,
                                spaceAfter=6),
        "sub": ParagraphStyle("s", fontName="DejaVuSans", fontSize=10, leading=13, alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", fontName="DejaVuSans-Bold", fontSize=12.5, leading=16, spaceBefore=8, spaceAfter=4,
                             textColor=colors.HexColor("#123a6b")),
        "h2": ParagraphStyle("h2", fontName="DejaVuSans-Bold", fontSize=10, leading=13, spaceBefore=6, spaceAfter=3,
                             textColor=colors.HexColor("#1b4f8a")),
        "body": ParagraphStyle("b", **base),
        "small": ParagraphStyle("sm", fontName="DejaVuSans", fontSize=7.2, leading=9.2),
        "cell": ParagraphStyle("c", fontName="DejaVuSans", fontSize=7.4, leading=9.2, alignment=TA_LEFT),
        "cellb": ParagraphStyle("cb", fontName="DejaVuSans-Bold", fontSize=7.4, leading=9.2),
        "mono": ParagraphStyle("m", fontName="DejaVuSansMono", fontSize=7.0, leading=9.0),
        "verdict": ParagraphStyle("v", fontName="DejaVuSans-Bold", fontSize=12, leading=15, alignment=TA_CENTER,
                                  textColor=colors.white),
    }


def P(txt: str, st) -> Paragraph:
    return Paragraph(escape(str(txt)).replace("\n", "<br/>"), st)


def _table(rows, widths, st, header=True, zebra=True):
    data = [[c if isinstance(c, Paragraph) else P(c, st["cellb"] if (header and i == 0) else st["cell"])
             for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9aa4b1")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
             ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe6ef")))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f7fa")))
    t.setStyle(TableStyle(style))
    return t


def _eta(e):
    if e is None:
        return "—"
    return "∞" if not math.isfinite(e) else f"{e:.3f}"


def _val(v, kind):
    if v is None:
        return "—"
    if kind == Kind.RATIO:
        return f"{v:.3f}"
    return fmt(v, kind)


class _Doc(SimpleDocTemplate):
    def __init__(self, path, meta, **kw):
        super().__init__(path, **kw)
        self.meta = meta

    def afterPage(self):  # noqa: N802
        c = self.canv
        c.saveState()
        c.setFont("DejaVuSans", 6.8)
        c.setFillColor(colors.HexColor("#555555"))
        w, h = A4
        c.line(16 * mm, h - 13 * mm, w - 16 * mm, h - 13 * mm)
        c.drawString(16 * mm, h - 11.5 * mm, f"{APP_NAME} {__version__} — {self.meta['project']}")
        c.drawRightString(w - 16 * mm, h - 11.5 * mm, f"{self.meta['element']} | wariant: {self.meta['variant']}")
        c.line(16 * mm, 12 * mm, w - 16 * mm, 12 * mm)
        c.drawString(16 * mm, 8.5 * mm, f"{self.meta['edition']} | dane: {self.meta['hash']} | wyniki: "
                                        f"{self.meta['fp']} | {self.meta['date']}")
        c.drawRightString(w - 16 * mm, 8.5 * mm, f"Strona {c.getPageNumber()}")
        c.drawCentredString(w / 2, 4.8 * mm, "Dokument obliczeniowy wymaga weryfikacji przez uprawnionego projektanta.")
        c.restoreState()


def generate_pdf(project, variant, result, path: str) -> str:
    register_fonts()
    st = _styles()
    info = project.info
    meta = {"project": info.name, "element": info.element, "variant": variant.name,
            "edition": result.edition_id or variant.normative.edition, "hash": result.input_hash,
            "fp": result.fingerprint, "date": _dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    doc = _Doc(path, meta, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=17 * mm,
               bottomMargin=17 * mm, title=f"Obliczenia wspornika — {info.element}", author=info.designer or APP_NAME,
               subject="Krótki wspornik żelbetowy — model Strut-and-Tie", creator=f"{APP_NAME} {__version__}")
    W = A4[0] - 32 * mm
    E: list = []
    # --- strona tytułowa -------------------------------------------------
    E += [Spacer(1, 18 * mm), P("OBLICZENIA STATYCZNE", st["title"]),
          P("Krótki wspornik żelbetowy — metoda Strut-and-Tie (EN 1992-1-1 §6.5, zał. J.3)", st["sub"]),
          Spacer(1, 10 * mm)]
    E.append(_table([["Projekt", info.name], ["Numer", info.number or "—"], ["Obiekt", info.object or "—"],
                     ["Element", info.element], ["Wariant obliczeniowy", variant.name],
                     ["Projektant", info.designer or "—"], ["Sprawdzający", info.checker or "—"],
                     ["Data", meta["date"]], ["Program", f"{APP_NAME} {__version__}"],
                     ["Podstawa normowa", result.edition_title or variant.normative.edition],
                     ["Model obliczeniowy", result.model_type or "—"]],
                    [45 * mm, W - 45 * mm], st, header=False))
    E.append(Spacer(1, 8 * mm))
    v = result.verdict
    bg = VERDICT_COLORS.get(v.code, ("#444444", "#ffffff"))[0]
    vt = Table([[P(f"WYNIK: {v.title}", st["verdict"])], [P(v.text, ParagraphStyle(
        "vt", parent=st["body"], textColor=colors.white, alignment=TA_CENTER))]], colWidths=[W])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    E.append(vt)
    E.append(Spacer(1, 6 * mm))
    E.append(P("Uwaga: wynik dotyczy lokalnego modelu STM wspornika i sprawdzeń wymienionych w raporcie. Nie stanowi "
               "potwierdzenia nośności słupa, połączenia ani całej konstrukcji. Pozycje oznaczone 'WYMAGA OSOBNEJ "
               "WERYFIKACJI' należy sprawdzić odrębnie.", st["small"]))
    if info.notes:
        E += [Spacer(1, 4 * mm), P("Uwagi projektanta: " + info.notes, st["body"])]
    E.append(PageBreak())
    # --- spis treści --------------------------------------------------------
    E.append(P("Spis treści", st["h1"]))
    for t in ("1. Dane wejściowe", "2. Podstawa normowa, parametry i założenia", "3. Model obliczeniowy STM",
              "4. Sprawdzenia nośności i warunków konstrukcyjnych", "5. Zestawienie zbrojenia",
              "6. Kontrola numeryczna i status walidacji", "7. Wnioski"):
        E.append(P(t, st["body"]))
    # --- 1. dane -----------------------------------------------------------
    E.append(P("1. Dane wejściowe", st["h1"]))
    g = variant.geometry
    E.append(P("1.1 Geometria", st["h2"]))
    rows = [["Parametr", "Wartość"],
            ["Układ / wykonanie", f"{'dwustronny' if g.layout.value == 'double' else 'jednostronny'} / "
                                  f"{'prefabrykowany' if g.construction.value == 'precast' else 'monolityczny'}"],
            ["Szerokość wspornika b", fmt(g.b, Kind.LENGTH)],
            ["Słup h_col × b_col", f"{fmt(g.column.h_col, Kind.LENGTH)} × {fmt(g.column.b_col, Kind.LENGTH)}; "
                                    f"otulina {fmt(g.column.cover, Kind.LENGTH)}; φ_podł = {g.column.phi_long:.0f} mm"]]
    if result.geometry is not None:
        for sd, sg in result.geometry.sides.items():
            tag = "P" if sd == "R" else "L"
            rows += [[f"[{tag}] l_c / h_c / h_e / x_s", f"{sg.l_c:.0f} / {sg.h_c:.0f} / {sg.h_e:.0f} / {sg.x_slope:.0f} mm "
                                                         f"({sg.shape})"],
                     [f"[{tag}] a_c; płyta a_p × b_p × t_p", f"{sg.a_c:.0f} mm; {sg.plate.length:.0f} × {sg.plate.width:.0f}"
                                                              f" × {sg.plate.thickness:.0f} mm ({sg.plate.kind})"]]
    E.append(_table(rows, [60 * mm, W - 60 * mm], st))
    E.append(P("1.2 Materiały i trwałość", st["h2"]))
    if result.materials is not None:
        c, s = result.materials.concrete, result.materials.steel
        rows = [["Parametr", "Wartość", "Źródło"],
                ["Beton", f"{c.cls}: f_ck = {c.fck:.0f} MPa, f_ctm = {c.fctm:.1f} MPa, f_ctk,0,05 = {c.fctk005:.1f} MPa, "
                          f"E_cm = {c.Ecm / 1000:.0f} GPa", "tabl. 3.1"],
                ["Wartości obliczeniowe", f"γ_c = {c.gamma_c}; α_cc = {c.alpha_cc}; f_cd = {c.fcd:.2f} MPa; "
                                          f"f_ctd = {c.fctd:.3f} MPa; ν' = {c.nu_prime:.3f}", "(3.15), (3.16), (6.57N)"],
                ["Stal", f"{s.name}: f_yk = {s.fyk:.0f} MPa, klasa {s.ductility}, γ_s = {s.gamma_s}, f_yd = {s.fyd:.1f} MPa, "
                         f"E_s = {s.Es / 1000:.0f} GPa", "§3.2, zał. C"],
                ["Trwałość", f"ekspozycja {variant.materials.exposure}, klasa {variant.materials.structural_class}, "
                             f"Δc_dev = {variant.materials.delta_c_dev:.0f} mm, d_g = {variant.materials.d_g:.0f} mm",
                 "§4.4.1"]]
        if result.cover is not None:
            cv = result.cover
            rows.append(["Otulina", f"c_min,dur = {cv.c_min_dur:.0f} mm; c_nom = {cv.c_nom:.0f} mm "
                                    f"({'przyjęta' if cv.user else 'wyznaczona'}); pręty główne: góra {cv.c_top_main:.0f} mm,"
                                    f" bok {cv.c_side_main:.0f} mm", "tabl. 4.4N, (4.1), (4.2)"])
        E.append(_table(rows, [32 * mm, W - 32 * mm - 32 * mm, 32 * mm], st))
    E.append(P("1.3 Oddziaływania", st["h2"]))
    rows = [["Nazwa", "Strona", "Kat.", "Charakter", "V", "H", "M", "e_x / e_y", "Opis"]]
    for a in variant.loads.actions:
        rows.append([a.name, a.side, a.category, "obl." if a.nature == "design" else "char.", fmt(a.V, Kind.FORCE),
                     fmt(a.H, Kind.FORCE), fmt(a.M, Kind.MOMENT), f"{a.e_x:.0f} / {a.e_y:.0f} mm", a.note])
    E.append(_table(rows, [14 * mm, 11 * mm, 11 * mm, 14 * mm, 19 * mm, 17 * mm, 17 * mm, 20 * mm,
                           W - 123 * mm], st))
    E.append(P("1.4 Kombinacje obciążeń (wartości obliczeniowe na wsporniku)", st["h2"]))
    rows = [["Kombinacja", "Typ", "Mnożniki", "Strona: V_Ed; H_Ed; e_x; e_y"]]
    for cmb in result.combinations:
        sides = "; ".join(f"{sd}: {fmt(sa.V, Kind.FORCE)}, {fmt(sa.H, Kind.FORCE)}, {sa.e_x:.1f} mm, {sa.e_y:.1f} mm"
                          + (" (H_min)" if sa.H_min_applied else "") for sd, sa in cmb.sides.items())
        rows.append([cmb.name, cmb.kind, ", ".join(f"{k}·{v:g}" for k, v in cmb.factors.items()), sides])
    E.append(_table(rows, [36 * mm, 20 * mm, 50 * mm, W - 106 * mm], st))
    # --- 2. podstawa normowa ----------------------------------------------
    E.append(PageBreak())
    E.append(P("2. Podstawa normowa, parametry i założenia", st["h1"]))
    E.append(P(f"Edycja normy: {result.edition_title}. Parametry krajowe (NDP) "
               f"{'POTWIERDZONE' if variant.normative.ndp_confirmed else 'NIEPOTWIERDZONE'} przez projektanta.",
               st["body"]))
    rows = [["Parametr", "Wartość", "Źródło", "Kategoria", "Status"]]
    for d in result.params_used:
        rows.append([f"{d['symbol']} ({d['key']})", f"{d['value']:g} {d['unit'] if d['unit'] != '-' else ''}",
                     d["clause"], d["category"], d["status"] + ("" if d["confirmed"] else " — NIEPOTWIERDZONY")])
    E.append(_table(rows, [42 * mm, 18 * mm, 50 * mm, 30 * mm, W - 140 * mm], st))
    E.append(P("2.1 Założenia obliczeniowe", st["h2"]))
    for a in result.assumptions:
        E.append(P("• " + a, st["body"]))
    E.append(P("2.2 Ograniczenia zakresu", st["h2"]))
    for a in result.limitations:
        E.append(P("• " + a, st["body"]))
    # --- 3. model STM ------------------------------------------------------
    E.append(PageBreak())
    E.append(P("3. Model obliczeniowy STM", st["h1"]))
    sr = result.governing_stm
    E.append(P(f"Model: {result.model_type}. Kombinacja decydująca: {result.governing or '—'}.", st["body"]))
    try:
        for mode, title in (("geometry", "Rys. 1. Geometria wspornika"), ("stm", "Rys. 2. Model Strut-and-Tie "
                                                                                 "(krzyżulce — czerwone, cięgna — niebieskie)"),
                            ("rebar", "Rys. 3. Zbrojenie")):
            sc = build_scene(variant, result, mode)
            dr = scene_to_drawing(sc, W, 118 * mm)
            E.append(KeepTogether([dr, P(title, st["small"]), Spacer(1, 3 * mm)]))
    except Exception as exc:  # noqa: BLE001
        E.append(P(f"Rysunek niedostępny: {exc}", st["small"]))
    if sr is not None and sr.solution.status != "error":
        E.append(P("3.1 Węzły i siły w prętach", st["h2"]))
        rows = [["Węzeł", "x [mm]", "y [mm]", "Typ", "Reakcja R_x", "Reakcja R_y"]]
        for n in sr.truss.nodes:
            rx, ry = sr.solution.reactions.get(n.id, (None, None))
            nz = sr.nodes.get(n.id)
            rows.append([n.id, f"{n.x:.1f}", f"{n.y:.1f}", nz.type if nz else "—",
                         fmt(rx, Kind.FORCE) if rx is not None else "—", fmt(ry, Kind.FORCE) if ry is not None else "—"])
        E.append(_table(rows, [18 * mm, 22 * mm, 22 * mm, 34 * mm, 30 * mm, W - 126 * mm], st))
        rows = [["Pręt", "Węzły", "Rodzaj", "Siła N (+ rozciąganie)"]]
        for m in sr.truss.members:
            N = sr.solution.forces.get(m.id, 0.0)
            rows.append([m.id, f"{m.n1}–{m.n2}", "krzyżulec" if m.kind == "strut" else "cięgno", fmt(N, Kind.FORCE)])
        E.append(_table(rows, [18 * mm, 30 * mm, 30 * mm, W - 78 * mm], st))
        for sd, sm in sr.sides.items():
            s_, p_ = sm.state, sm.params
            E.append(P(f"Parametry geometryczne modelu — strona {'prawa' if sd == 'R' else 'lewa'}", st["h2"]))
            rows = [["Wielkość", "Wartość", "Opis"],
                    ["c_t / d", f"{p_.c_t:.1f} / {p_.d:.1f} mm", "oś cięgna od góry / wysokość użyteczna"],
                    ["ξ_A", f"{s_.xi_A:.1f} mm", "węzeł A: a_c + M/V + H·a_H/V (a_H = %.1f mm)" % p_.a_H],
                    ["x_c / z0", f"{s_.x_c:.1f} / {s_.z0:.1f} mm", f"strefa ściskana węzła B / ramię — {sm.search.get('method', '')}"],
                    ["ξ_B / a_B", f"{s_.xi_B:.1f} / {s_.a_B:.1f} mm", "położenie i szerokość węzła B"],
                    ["θ / tan θ", f"{s_.theta_deg:.2f}° / {s_.tan_theta:.3f}", "nachylenie krzyżulca (J.3(1): 1,0–2,5)"],
                    ["w_A / w_B", f"{s_.w_A:.1f} / {s_.w_B:.1f} mm", "szerokości krzyżulca przy węzłach"],
                    ["t_A / t_B", f"{p_.t_A:.0f} / {p_.t_B:.0f} mm", "grubości efektywne"],
                    ["F_c / T / C", f"{fmt(s_.Fc, Kind.FORCE)} / {fmt(s_.T, Kind.FORCE)} / {fmt(s_.C, Kind.FORCE)}",
                     "siły w modelu"]]
            E.append(_table(rows, [26 * mm, 50 * mm, W - 76 * mm], st))
    # --- 4. sprawdzenia ----------------------------------------------------
    E.append(PageBreak())
    E.append(P("4. Sprawdzenia nośności i warunków konstrukcyjnych", st["h1"]))
    E.append(P("Dla każdego kryterium: E_d / R_d = η. Status: SPEŁNIONO | NIE SPEŁNIONO | WYMAGA OSOBNEJ WERYFIKACJI "
               "| NIE DOTYCZY.", st["small"]))
    rows = [["Sprawdzenie", "E_d", "R_d", "η", "Status"]]
    for c in result.checks:
        rows.append([c.title, _val(c.E_d, c.kind), _val(c.R_d, c.kind), _eta(c.eta), c.status.value])
    t = _table(rows, [W - 102 * mm, 26 * mm, 26 * mm, 14 * mm, 36 * mm], st)
    sc_ = STATUS_COLORS["light"]
    ts = []
    for i, c in enumerate(result.checks, start=1):
        ts.append(("TEXTCOLOR", (4, i), (4, i), colors.HexColor(sc_.get(c.status.value, "#000000"))))
    t.setStyle(TableStyle(ts))
    E.append(t)
    for grp, lst in result.checks_by_group().items():
        E.append(P(f"4.x {grp}", st["h2"]))
        for c in lst:
            col = colors.HexColor(sc_.get(c.status.value, "#000000"))
            rows = [[P(f"<b>{escape(c.title)}</b>", st["cell"]), P(f"<b>{c.status.value}</b>", ParagraphStyle(
                "st", parent=st["cell"], textColor=col))],
                    ["Podstawa", f"{c.clause} — {c.basis.value}"],
                    ["Wzór", c.formula or "—"]]
            if c.symbols:
                rows.append(["Symbole", "; ".join(f"{k} — {v}" for k, v in c.symbols.items())])
            rows.append(["Podstawienie", c.substitution or "—"])
            rows.append(["Wynik", f"{c.E_label} = {_val(c.E_d, c.kind)};  {c.R_label} = {_val(c.R_d, c.kind)};  "
                                  f"η = {_eta(c.eta)}" + (f";  kombinacja: {c.combination}" if c.combination else "")])
            if c.notes:
                rows.append(["Uwagi", " | ".join(c.notes)])
            rows.append(["Wniosek", c.conclusion])
            tb = _table(rows, [24 * mm, W - 24 * mm], st, header=False, zebra=False)
            tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                                    ("SPAN", (0, 0), (0, 0))]))
            E.append(KeepTogether([tb, Spacer(1, 2.5 * mm)]))
    # --- 5. zbrojenie ------------------------------------------------------
    E.append(PageBreak())
    E.append(P("5. Zestawienie zbrojenia", st["h1"]))
    if result.main is not None:
        E.append(P(f"Zbrojenie główne: {result.main.desc()}, A_s,prov = {result.main.As:.0f} mm², zakotwienie: "
                   f"{result.main_input.anchor_load} (koniec) / {result.main_input.anchor_column} (słup).", st["body"]))
        for sd, ll in result.links.items():
            E.append(P(f"Strzemiona ({'P' if sd == 'R' else 'L'}): {ll.desc_h()}; {ll.desc_v()}"
                       + (f"; pręty ukośne {ll.i_count}×φ{ll.i_phi:.0f}" if ll.i_count else ""), st["body"]))
    if result.schedule:
        rows = [["Poz.", "Opis", "Kształt", "φ [mm]", "Szt.", "Dł. 1 szt. [m]", "Dł. całk. [m]", "Masa [kg]"]]
        tot: dict[float, float] = {}
        for b in result.schedule:
            rows.append([b.mark, b.description, b.shape, f"{b.phi:.0f}", str(b.count), f"{b.length / 1000:.2f}",
                         f"{b.total_length / 1000:.2f}", f"{b.mass:.1f}"])
            tot[b.phi] = tot.get(b.phi, 0.0) + b.mass
        rows.append(["", "RAZEM", "", "", "", "", "", f"{sum(tot.values()):.1f}"])
        E.append(_table(rows, [10 * mm, 50 * mm, W - 136 * mm, 13 * mm, 11 * mm, 18 * mm, 18 * mm, 16 * mm], st))
        E.append(P("Masa wg średnic: " + ", ".join(f"φ{k:.0f}: {v:.1f} kg" for k, v in sorted(tot.items())) +
                   ". Długości orientacyjne (osiowe, bez naddatków na zakłady) — do weryfikacji w dokumentacji "
                   "wykonawczej.", st["small"]))
    for line in result.design_log[-10:]:
        E.append(P("• " + line, st["small"]))
    # --- 6. walidacja --------------------------------------------------------
    E.append(P("6. Kontrola numeryczna i status walidacji", st["h1"]))
    rows = [["Kontrola automatyczna", "Wynik", "Szczegóły"]]
    for it in result.validation:
        rows.append([it.name, "OK" if it.ok else "BŁĄD", it.detail])
    E.append(_table(rows, [60 * mm, 14 * mm, W - 74 * mm], st))
    rows = [["Moduł", "Status walidacji", "Opis"]]
    for k, (s_, d_) in MODULE_STATUS.items():
        rows.append([k, s_, d_])
    E.append(_table(rows, [36 * mm, 30 * mm, W - 66 * mm], st))
    # --- 7. wnioski ------------------------------------------------------------
    E.append(P("7. Wnioski", st["h1"]))
    E.append(P(f"Werdykt: {v.title}. {v.text}", st["body"]))
    fails = [c for c in result.checks if c.status == CheckStatus.FAIL]
    ver = [c for c in result.checks if c.status == CheckStatus.VERIFY]
    if result.errors:
        E.append(P("Błędy krytyczne:", st["h2"]))
        for m in result.errors:
            E.append(P("• " + m.text, st["body"]))
    if fails:
        E.append(P("Sprawdzenia niespełnione:", st["h2"]))
        for c in fails:
            E.append(P(f"• {c.title} (η = {_eta(c.eta)}) — {c.clause}", st["body"]))
    if ver:
        E.append(P("Pozycje wymagające osobnej weryfikacji:", st["h2"]))
        for c in ver:
            E.append(P(f"• {c.title} — {c.conclusion}", st["body"]))
    if not v.positive:
        E.append(Spacer(1, 3 * mm))
        E.append(P("Raport nie zawiera pozytywnego wniosku ogólnego.", st["h2"]))
    E.append(Spacer(1, 10 * mm))
    E.append(_table([["Opracował:", "Sprawdził:"], [info.designer or "", info.checker or ""],
                     ["podpis / data", "podpis / data"]], [W / 2, W / 2], st, header=False, zebra=False))
    doc.build(E)
    return path
