"""Panel wyników (prawy) i panel szczegółowych obliczeń (dolny)."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
                               QProgressBar, QTableWidget, QTableWidgetItem, QTextBrowser, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QGroupBox, QSplitter)

from ..core.results import CheckStatus, Level
from ..core.units import fmt, Kind
from .i18n import tr, tr_status
from .themes import STATUS_COLORS, VERDICT_COLORS


def _eta_txt(eta):
    if eta is None:
        return "—"
    if not math.isfinite(eta):
        return "∞"
    return f"{eta:.3f}"


class ResultsPanel(QWidget):
    checkSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "light"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.verdict = QLabel("—")
        self.verdict.setWordWrap(True)
        self.verdict.setAlignment(Qt.AlignCenter)
        self.verdict.setMinimumHeight(46)
        lay.addWidget(self.verdict)
        self.verdict_text = QLabel("")
        self.verdict_text.setWordWrap(True)
        lay.addWidget(self.verdict_text)
        sp = QSplitter(Qt.Vertical)
        g1 = QGroupBox(tr("Siły wewnętrzne"))
        l1 = QVBoxLayout(g1)
        self.forces = QTableWidget(0, 2)
        self.forces.horizontalHeader().setVisible(False)
        self.forces.verticalHeader().setVisible(False)
        self.forces.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.forces.horizontalHeader().setStretchLastSection(True)
        l1.addWidget(self.forces)
        sp.addWidget(g1)
        g2 = QGroupBox(tr("Wykorzystanie"))
        l2 = QVBoxLayout(g2)
        self.crit = QLabel("")
        self.crit.setWordWrap(True)
        l2.addWidget(self.crit)
        self.util = QTableWidget(0, 3)
        self.util.setHorizontalHeaderLabels([tr("Sprawdzenie"), "η", tr("Status")])
        self.util.verticalHeader().setVisible(False)
        self.util.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.util.setSelectionBehavior(QTableWidget.SelectRows)
        self.util.cellClicked.connect(self._util_clicked)
        l2.addWidget(self.util)
        sp.addWidget(g2)
        g3 = QGroupBox(tr("Komunikaty"))
        l3 = QVBoxLayout(g3)
        self.msgs = QListWidget()
        self.msgs.setWordWrap(True)
        l3.addWidget(self.msgs)
        sp.addWidget(g3)
        g4 = QGroupBox(tr("Szczegóły elementu"))
        l4 = QVBoxLayout(g4)
        self.details = QTextBrowser()
        self.details.setOpenLinks(False)
        l4.addWidget(self.details)
        sp.addWidget(g4)
        sp.setSizes([180, 260, 140, 200])
        lay.addWidget(sp, 1)
        self._ids: list[str] = []
        self.result = None

    def set_stale(self) -> None:
        bg, fg = VERDICT_COLORS["STALE"]
        self.verdict.setStyleSheet(f"background:{bg}; color:{fg}; font-weight:700; font-size:12pt; padding:6px;"
                                   "border-radius:4px;")
        self.verdict.setText(tr("Wyniki nieaktualne — uruchom obliczenia (F5)"))

    def show_result(self, res) -> None:
        self.result = res
        v = res.verdict
        bg, fg = VERDICT_COLORS.get(v.code, ("#444", "#fff"))
        self.verdict.setStyleSheet(f"background:{bg}; color:{fg}; font-weight:700; font-size:12pt; padding:6px;"
                                   "border-radius:4px;")
        self.verdict.setText(v.title)
        self.verdict_text.setText(v.text)
        # siły
        rows = []
        if res.model_type:
            rows.append(("Model", res.model_type))
        if res.governing:
            rows.append(("Kombinacja decydująca", res.governing))
        sr = res.governing_stm
        if sr is not None:
            for sd, sm in sr.sides.items():
                s, p = sm.state, sm.params
                tag = "P" if sd == "R" else "L"
                rows += [(f"[{tag}] V_Ed / H_Ed", f"{fmt(p.V, Kind.FORCE)} / {fmt(p.H_raw, Kind.FORCE)}"),
                         (f"[{tag}] T_Ed (cięgno)", fmt(s.T, Kind.FORCE)),
                         (f"[{tag}] C_Ed (krzyżulec)", fmt(s.C, Kind.FORCE)),
                         (f"[{tag}] θ / tan θ", f"{s.theta_deg:.2f}° / {s.tan_theta:.3f}"),
                         (f"[{tag}] d / z0 / x_c", f"{fmt(p.d, Kind.LENGTH)} / {fmt(s.z0, Kind.LENGTH)} / "
                                                   f"{fmt(s.x_c, Kind.LENGTH)}"),
                         (f"[{tag}] w_A / w_B", f"{fmt(s.w_A, Kind.LENGTH)} / {fmt(s.w_B, Kind.LENGTH)}"),
                         (f"[{tag}] A_s,req", fmt(s.T / p.fyd, Kind.AREA))]
            if sr.solution.reactions:
                for nid, (rx, ry) in sorted(sr.solution.reactions.items()):
                    rows.append((f"Reakcja {nid}", f"R_x = {fmt(rx, Kind.FORCE)}, R_y = {fmt(ry, Kind.FORCE)}"))
        if res.main is not None:
            rows.append(("Zbrojenie główne", f"{res.main.desc()} — A_s,prov = {fmt(res.main.As, Kind.AREA)}"))
            if res.main_input is not None:
                rows.append(("Zakotwienie", f"obciążenie: {res.main_input.anchor_load}; słup: "
                                            f"{res.main_input.anchor_column}"))
            for sd, ll in res.links.items():
                rows.append((f"Strzemiona [{'P' if sd == 'R' else 'L'}]", f"{ll.desc_h()}; {ll.desc_v()}"))
        if res.cover is not None:
            rows.append(("Otulina c_nom", fmt(res.cover.c_nom, Kind.LENGTH)))
        self.forces.setRowCount(len(rows))
        for r, (a, b) in enumerate(rows):
            self.forces.setItem(r, 0, QTableWidgetItem(a))
            self.forces.setItem(r, 1, QTableWidgetItem(b))
        # element krytyczny
        c = res.critical()
        self.crit.setText(f"<b>{tr('Element krytyczny')}:</b> {c.title} — η = {_eta_txt(c.eta)} "
                          f"({c.combination})" if c else "")
        # wykorzystanie
        cols = STATUS_COLORS.get(self.theme, STATUS_COLORS["light"])
        from ..analysis import STRENGTH_GROUPS

        def key(x):
            has = x.eta is not None
            e = x.eta if (has and math.isfinite(x.eta)) else (1e9 if has else -1.0)
            rank = {CheckStatus.FAIL: 0, CheckStatus.OK: 1, CheckStatus.VERIFY: 2}.get(x.status, 3)
            strength = x.group in STRENGTH_GROUPS and not x.id.endswith(("_T81", "_LEG"))
            if x.status == CheckStatus.FAIL:
                return (0, 0, -e)
            return (rank if has else 3 + rank, 0 if strength else 1, -e)
        checks = sorted([x for x in res.checks if x.status != CheckStatus.NA], key=key)
        self.util.setRowCount(len(checks))
        self._ids = []
        for r, ck in enumerate(checks):
            self._ids.append(ck.id)
            self.util.setItem(r, 0, QTableWidgetItem(ck.title))
            bar = QProgressBar()
            e = ck.eta if (ck.eta is not None and math.isfinite(ck.eta)) else None
            bar.setRange(0, 1000)
            bar.setValue(int(min(e, 1.0) * 1000) if e is not None else 0)
            bar.setFormat(_eta_txt(ck.eta))
            col = "#2e7d32" if e is not None and e <= 0.85 else ("#ef6c00" if e is not None and e <= 1.0 else "#c62828")
            if e is None:
                col = "#9e9e9e"
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {col}; }} QProgressBar {{ text-align: center; }}")
            self.util.setCellWidget(r, 1, bar)
            st = QTableWidgetItem(tr_status(ck.status.value))
            st.setForeground(QBrush(QColor(cols.get(ck.status.value, "#000"))))
            self.util.setItem(r, 2, st)
        self.util.setColumnWidth(1, 110)
        self.util.resizeColumnToContents(2)
        # komunikaty
        self.msgs.clear()
        for m in res.messages:
            it = QListWidgetItem(f"{m.level.value}: {m.text}")
            it.setForeground(QBrush(QColor({"BŁĄD": "#c62828", "OSTRZEŻENIE": "#b26a00"}.get(m.level.value, "#1565c0"))))
            self.msgs.addItem(it)
        for a in res.design_log[-6:]:
            self.msgs.addItem(QListWidgetItem("DOBÓR: " + a))

    def _util_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._ids):
            self.checkSelected.emit(self._ids[row])

    def show_element(self, ref: str, res) -> None:
        if res is None:
            self.details.setHtml(f"<i>{ref}</i>")
            return
        html = [f"<h3>{ref}</h3>"]
        sr = res.governing_stm
        if ref.startswith("member:") and sr is not None:
            mid = ref.split(":", 1)[1]
            for s in sr.struts:
                if s.id == mid:
                    html.append(f"<p><b>Krzyżulec {s.id}</b> ({s.shape}): C = {fmt(abs(s.force), Kind.FORCE)}, "
                                f"θ = {s.theta_deg:.2f}°, L = {s.length:.0f} mm, w₁ = {s.w1:.1f} mm, w₂ = {s.w2:.1f} mm, "
                                f"t₁/t₂ = {s.t1:.0f}/{s.t2:.0f} mm, b_dost = {s.b_avail:.0f} mm</p>")
            for t in sr.ties:
                if t.id == mid:
                    html.append(f"<p><b>Cięgno {t.id}</b>: T = {fmt(t.force, Kind.FORCE)}, A_s,prov = "
                                f"{fmt(t.As_prov or 0, Kind.AREA)}, u = {t.u:.0f} mm</p>")
        if ref.startswith("node:") and sr is not None:
            nid = ref.split(":", 1)[1]
            nz = sr.nodes.get(nid)
            if nz is not None:
                html.append(f"<p><b>Węzeł {nid}</b> — typ {nz.type}; położenie ({nz.center[0]:.1f}; {nz.center[1]:.1f}) mm"
                            "</p><ul>")
                for f in nz.faces:
                    html.append(f"<li>{f['name']}: F = {fmt(f['F'], Kind.FORCE)}, długość = {f['length']:.1f} mm, "
                                f"t = {f['t']:.0f} mm, σ = {f['sigma']:.2f} MPa</li>")
                html.append("</ul>")
            if nid in sr.solution.reactions:
                rx, ry = sr.solution.reactions[nid]
                html.append(f"<p>Reakcja: R_x = {fmt(rx, Kind.FORCE)}, R_y = {fmt(ry, Kind.FORCE)}; residuum węzła "
                            f"{sr.solution.node_residuals.get(nid, 0):.2e} N</p>")
        rel = [c for c in res.checks if c.element_ref == ref]
        if rel:
            html.append("<table border='1' cellspacing='0' cellpadding='3'><tr><th>Sprawdzenie</th><th>η</th>"
                        "<th>Status</th></tr>")
            for c in rel:
                html.append(f"<tr><td>{c.title}</td><td>{_eta_txt(c.eta)}</td><td>{c.status.value}</td></tr>")
            html.append("</table>")
        self.details.setHtml("".join(html))


class ChecksPanel(QWidget):
    checkSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "light"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("Filtr:")))
        self.filter = QComboBox()
        for key, lab in (("all", "Wszystkie"), ("fail", "Niespełnione"), ("verify", "Wymagające weryfikacji"),
                         ("ok", "Spełnione")):
            self.filter.addItem(tr(lab), key)
        self.filter.currentIndexChanged.connect(lambda _i: self._fill())
        top.addWidget(self.filter)
        self.summary = QLabel("")
        top.addWidget(self.summary, 1)
        lay.addLayout(top)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels([tr("Sprawdzenie"), tr("Podstawa"), "E_d", "R_d", "η", tr("Status")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.tree.setColumnWidth(0, 430)
        self.tree.setColumnWidth(1, 300)
        self.tree.setWordWrap(True)
        self.tree.itemClicked.connect(self._clicked)
        lay.addWidget(self.tree)
        self.result = None

    def show_result(self, res) -> None:
        self.result = res
        self._fill()

    def _fill(self) -> None:
        self.tree.clear()
        res = self.result
        if res is None:
            return
        flt = self.filter.currentData()
        want = {"all": None, "fail": CheckStatus.FAIL, "verify": CheckStatus.VERIFY, "ok": CheckStatus.OK}[flt]
        cols = STATUS_COLORS.get(self.theme, STATUS_COLORS["light"])
        counts = {s: 0 for s in CheckStatus}
        for c in res.checks:
            counts[c.status] += 1
        self.summary.setText("   ".join(f"{tr_status(s.value)}: {n}" for s, n in counts.items()))
        bold = QFont()
        bold.setBold(True)
        for grp, lst in res.checks_by_group().items():
            lst = [c for c in lst if want is None or c.status == want]
            if not lst:
                continue
            g = QTreeWidgetItem([f"{grp} ({len(lst)})"])
            g.setFont(0, bold)
            self.tree.addTopLevelItem(g)
            for c in lst:
                kind = c.kind
                ed = fmt(c.E_d, kind) if c.E_d is not None and kind != Kind.RATIO else (
                    f"{c.E_d:.3f}" if c.E_d is not None else "—")
                rd = fmt(c.R_d, kind) if c.R_d is not None and kind != Kind.RATIO else (
                    f"{c.R_d:.3f}" if c.R_d is not None else "—")
                it = QTreeWidgetItem([c.title, c.clause, f"{c.E_label} = {ed}", f"{c.R_label} = {rd}", _eta_txt(c.eta),
                                      tr_status(c.status.value)])
                it.setData(0, Qt.UserRole, c.id)
                it.setForeground(5, QBrush(QColor(cols.get(c.status.value, "#000"))))
                it.setToolTip(0, c.title)
                it.setToolTip(1, c.clause)
                g.addChild(it)
                for lab, txt in (("Charakter", c.basis.value), ("Wzór", c.formula), ("Podstawienie", c.substitution),
                                 ("Symbole", "; ".join(f"{k} — {v}" for k, v in c.symbols.items())),
                                 ("Kombinacja", c.combination), ("Uwagi", " | ".join(c.notes)),
                                 ("Wniosek", c.conclusion)):
                    if txt:
                        ch = QTreeWidgetItem([f"{lab}: {txt}"])
                        ch.setFirstColumnSpanned(True)
                        ch.setToolTip(0, txt)
                        ch.setData(0, Qt.UserRole, c.id)
                        it.addChild(ch)
                        ch.setFirstColumnSpanned(True)
            g.setExpanded(want is not None or grp in ("Krzyżulce", "Węzły", "Cięgna"))

    def _clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        cid = item.data(0, Qt.UserRole)
        if cid:
            self.checkSelected.emit(cid)

    def select(self, cid: str) -> None:
        it = self.tree.invisibleRootItem()
        for i in range(it.childCount()):
            g = it.child(i)
            for j in range(g.childCount()):
                c = g.child(j)
                if c.data(0, Qt.UserRole) == cid:
                    g.setExpanded(True)
                    c.setExpanded(True)
                    self.tree.setCurrentItem(c)
                    self.tree.scrollToItem(c)
                    return
