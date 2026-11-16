"""Panel danych wejściowych — zakładki: Geometria, Materiały, Obciążenia, Model STM, Zbrojenie, Parametry normowe."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget, QLineEdit, QMessageBox)

from ..core.model import (Layout, Construction, LoadAction, LoadCombination, ManualNode, ManualMember,
                          ManualSupport, ManualLoad)
from ..core.units import Kind, DISPLAY, to_base, from_base
from ..load_engine import CATEGORIES, SOURCES, COMB_KINDS
from ..material_engine import CONCRETE_CLASSES, STEEL_GRADES, concrete_props, node_limits, strut_limit
from ..normative_parameters import EDITIONS, EXPOSURE_GROUP, STRUCTURAL_CLASSES, CATEGORY_LABEL, get_parameter_set
from .forms import Field, FormBinder
from .i18n import tr

L, F, S, M = Kind.LENGTH, Kind.FORCE, Kind.STRESS, Kind.MOMENT
DIAMS = [(d, f"φ{d:.0f}") for d in (6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0, 25.0, 28.0, 32.0, 40.0)]


def _scroll(widget: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(widget)
    sa.setFrameShape(QScrollArea.NoFrame)
    return sa


def _group(title: str, binder: FormBinder, fields: list[Field]) -> QGroupBox:
    g = QGroupBox(tr(title))
    form = QFormLayout(g)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    for f in fields:
        binder.add_to(form, f)
    return g


def _side_fields(prefix: str, enabled_if=None) -> list[Field]:
    return [
        Field(f"{prefix}.l_c", "Długość wysięgu l_c", "float", L, 50, 5000, enabled_if=enabled_if),
        Field(f"{prefix}.h_c", "Wysokość przy licu h_c", "float", L, 100, 5000, enabled_if=enabled_if),
        Field(f"{prefix}.h_e", "Wysokość na końcu h_e", "float", L, 50, 5000, enabled_if=enabled_if),
        Field(f"{prefix}.x_slope", "Początek skosu x_s (od lica)", "float", L, 0, 5000, enabled_if=enabled_if),
        Field(f"{prefix}.a_c", "Wysięg obciążenia a_c", "float", L, 1, 5000, enabled_if=enabled_if),
        Field(f"{prefix}.plate.kind", "Oparcie", "choice", choices=[("steel_plate", "Płyta stalowa"),
                                                                    ("elastomer", "Łożysko elastomerowe"),
                                                                    ("direct", "Oparcie bezpośrednie")],
              enabled_if=enabled_if),
        Field(f"{prefix}.plate.length", "Płyta: a_p (wzdłuż wysięgu)", "float", L, 10, 2000, enabled_if=enabled_if),
        Field(f"{prefix}.plate.width", "Płyta: b_p (w poprzek)", "float", L, 10, 3000, enabled_if=enabled_if),
        Field(f"{prefix}.plate.thickness", "Płyta: grubość t_p", "float", L, 0, 200, enabled_if=enabled_if),
        Field(f"{prefix}.plate.offset", "Przesunięcie płyty względem a_c", "float", L, -1000, 1000,
              enabled_if=enabled_if),
    ]


class InputPanel(QTabWidget):
    """Zakładki danych. Sygnał ``changed(path)`` przy każdej zmianie danych."""

    changed = Signal(str)
    requestCopyAutoModel = Signal()

    def __init__(self, variant_getter: Callable, parent=None):
        super().__init__(parent)
        self.vg = variant_getter
        self.binder = FormBinder(variant_getter, self)
        self.binder.changed.connect(self._on_changed)
        self._loading = False
        self.addTab(_scroll(self._geometry_tab()), tr("Geometria"))
        self.addTab(_scroll(self._materials_tab()), tr("Materiały"))
        self.addTab(self._loads_tab(), tr("Obciążenia"))
        self.addTab(_scroll(self._stm_tab()), tr("Model STM"))
        self.addTab(_scroll(self._rebar_tab()), tr("Zbrojenie"))
        self.addTab(self._norm_tab(), tr("Parametry normowe"))

    # ------------------------------------------------------------------
    def _on_changed(self, path: str) -> None:
        if path.startswith("materials"):
            self._update_material_info()
        if path.startswith("materials.steel_name"):
            v = self.vg()
            if v.materials.steel_name in STEEL_GRADES:
                fyk, cls = STEEL_GRADES[v.materials.steel_name]
                v.materials.steel_fyk, v.materials.steel_class = fyk, cls
                self.binder.load()
        self.changed.emit(path)

    def load(self) -> None:
        self._loading = True
        try:
            self.binder.load()
            self._load_actions()
            self._load_combos()
            self._load_manual()
            self._load_norm()
            self.load_diams()
            self._update_material_info()
        finally:
            self._loading = False

    def refresh_units(self) -> None:
        self.binder.refresh_units()
        self._set_action_headers()
        self._load_actions()

    # --- Geometria -----------------------------------------------------
    def _geometry_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        b = self.binder
        lay.addWidget(_group("Układ", b, [
            Field("geometry.layout", "Typ wspornika", "choice", choices=[(Layout.SINGLE, "Jednostronny"),
                                                                       (Layout.DOUBLE, "Dwustronny")]),
            Field("geometry.construction", "Wykonanie", "choice", choices=[(Construction.MONOLITHIC, "Monolityczny"),
                                                                          (Construction.PRECAST, "Prefabrykowany")]),
            Field("geometry.b", "Szerokość wspornika b", "float", L, 100, 5000),
        ]))
        lay.addWidget(_group("Słup", b, [
            Field("geometry.column.h_col", "Wymiar w płaszczyźnie h_col", "float", L, 150, 5000),
            Field("geometry.column.b_col", "Wymiar prostopadły b_col", "float", L, 150, 5000),
            Field("geometry.column.cover", "Otulina słupa", "float", L, 10, 100),
            Field("geometry.column.phi_long", "Pręty podłużne słupa φ", "float", L, 8, 40),
            Field("geometry.column.phi_link", "Strzemiona słupa φ", "float", L, 4, 16),
            Field("geometry.column.above", "Długość nad wspornikiem (rysunek)", "float", L, 0, 5000),
            Field("geometry.column.below", "Długość pod wspornikiem", "float", L, 100, 10000),
            Field("geometry.column.N_Ed", "Siła osiowa N_Ed (informacyjnie)", "float", F, -1e9, 1e9),
        ]))
        lay.addWidget(_group("Wspornik prawy (P)", b, _side_fields("geometry.right")))
        mirror = lambda v: v.geometry.layout == Layout.DOUBLE and not v.geometry.left_mirror  # noqa: E731
        lay.addWidget(_group("Wspornik lewy (L) — tylko układ dwustronny", b,
                             [Field("geometry.left_mirror", "Lustrzane odbicie prawego", "bool",
                                    enabled_if=lambda v: v.geometry.layout == Layout.DOUBLE)] +
                             _side_fields("geometry.left", mirror)))
        pre = lambda v: v.geometry.construction == Construction.PRECAST  # noqa: E731
        lay.addWidget(_group("Połączenie prefabrykowane (§10.9.5)", b, [
            Field("geometry.precast.support_type", "Rodzaj podparcia (tabl. 10.2)", "choice",
                  choices=[("concentrated", "Podparcie skupione (belki)"), ("line", "Liniowe (stropy, dachy)"),
                           ("ribbed", "Stropy żebrowe, płatwie")], enabled_if=pre),
            Field("geometry.precast.dry_connection", "Oparcie na sucho (f_Rd = 0,4 f_cd)", "bool", enabled_if=pre),
            Field("geometry.precast.f_bed", "Wytrzymałość podlewki f_bed", "float", S, 0, 200, enabled_if=pre),
            Field("geometry.precast.restraint_considered", "Uwzględniono siły od więzów (skurcz, temp.)", "bool",
                  enabled_if=pre),
        ]))
        lay.addStretch(1)
        return w

    # --- Materiały -----------------------------------------------------
    def _materials_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        b = self.binder
        lay.addWidget(_group("Beton", b, [
            Field("materials.concrete", "Klasa betonu", "choice", choices=[(c, c) for c in CONCRETE_CLASSES]),
            Field("materials.d_g", "Kruszywo d_g", "float", L, 4, 63),
            Field("materials.design_situation", "Sytuacja obliczeniowa", "choice",
                  choices=[("persistent", "Trwała / przejściowa"), ("accidental", "Wyjątkowa")]),
        ]))
        self.mat_info = QLabel()
        self.mat_info.setWordWrap(True)
        self.mat_info.setTextFormat(Qt.RichText)
        g = QGroupBox(tr("Parametry wyznaczone automatycznie"))
        QVBoxLayout(g).addWidget(self.mat_info)
        lay.addWidget(g)
        lay.addWidget(_group("Stal zbrojeniowa", b, [
            Field("materials.steel_name", "Gatunek", "choice", choices=[(k, k) for k in STEEL_GRADES]),
            Field("materials.steel_fyk", "f_yk", "float", S, 400, 600),
            Field("materials.steel_class", "Klasa ciągliwości", "choice", choices=[("A", "A"), ("B", "B"), ("C", "C")]),
            Field("materials.link_fyk", "f_yk strzemion", "float", S, 400, 600),
        ]))
        lay.addWidget(_group("Trwałość i otulina (§4.4.1)", b, [
            Field("materials.exposure", "Klasa ekspozycji", "choice", choices=[(k, k) for k in EXPOSURE_GROUP]),
            Field("materials.structural_class", "Klasa konstrukcji", "choice",
                  choices=[(k, k) for k in STRUCTURAL_CLASSES]),
            Field("materials.delta_c_dev", "Δc_dev", "float", L, 0, 20),
            Field("materials.c_nom_user", "Otulina nominalna c_nom", "optfloat", L, 5, 150),
        ]))
        lay.addStretch(1)
        return w

    def _update_material_info(self) -> None:
        v = self.vg()
        try:
            ps = get_parameter_set(v.normative)
            c = concrete_props(v.materials.concrete, ps, v.materials.design_situation)
            lim = node_limits(c, ps)
            s56 = strut_limit(c, ps, "6.56")[0]
            fyd = v.materials.steel_fyk / (ps.v("gamma_s") if v.materials.design_situation == "persistent"
                                           else ps.v("gamma_s_acc"))
            self.mat_info.setText(
                f"f<sub>ck</sub> = {c.fck:.0f} MPa; f<sub>cm</sub> = {c.fcm:.0f} MPa; f<sub>ctm</sub> = {c.fctm:.1f} MPa; "
                f"f<sub>ctk,0,05</sub> = {c.fctk005:.1f} MPa; E<sub>cm</sub> = {c.Ecm / 1000:.0f} GPa<br>"
                f"γ<sub>c</sub> = {c.gamma_c}; α<sub>cc</sub> = {c.alpha_cc}; <b>f<sub>cd</sub> = {c.fcd:.2f} MPa</b>; "
                f"f<sub>ctd</sub> = {c.fctd:.2f} MPa; ν' = {c.nu_prime:.3f}<br>"
                f"σ<sub>Rd,max</sub>: krzyżulec (6.56) = {s56:.2f} MPa; (6.55) = {c.fcd:.2f} MPa; "
                f"CCC = {lim['CCC']:.2f}; CCT = {lim['CCT']:.2f}; CTT = {lim['CTT']:.2f} MPa<br>"
                f"<b>f<sub>yd</sub> = {fyd:.1f} MPa</b>; E<sub>s</sub> = 200 GPa")
        except Exception as exc:  # noqa: BLE001
            self.mat_info.setText(f"<span style='color:#c62828'>{exc}</span>")

    # --- Obciążenia ----------------------------------------------------
    ACOLS = ["Nazwa", "Strona", "Kategoria", "Charakter", "Źródło", "V", "H", "M", "e_x", "e_y", "Opis"]

    def _loads_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        g = QGroupBox(tr("Oddziaływania (V w dół +, H od słupa +)"))
        gl = QVBoxLayout(g)
        self.tbl_actions = QTableWidget(0, len(self.ACOLS))
        self._set_action_headers()
        self.tbl_actions.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tbl_actions.horizontalHeader().setStretchLastSection(True)
        self.tbl_actions.verticalHeader().setVisible(False)
        self.tbl_actions.itemChanged.connect(self._actions_from_table)
        gl.addWidget(self.tbl_actions)
        row = QHBoxLayout()
        for txt, fn in ((tr("Dodaj"), self._add_action), (tr("Usuń"), self._del_action)):
            bt = QPushButton(txt)
            bt.clicked.connect(fn)
            row.addWidget(bt)
        self.btn_import = QPushButton(tr("Import…"))
        self.btn_export = QPushButton(tr("Eksport CSV…"))
        row.addWidget(self.btn_import)
        row.addWidget(self.btn_export)
        row.addStretch(1)
        gl.addLayout(row)
        lay.addWidget(g, 3)
        b = self.binder
        lay.addWidget(_group("Kombinacje SGN/SGU (EN 1990)", b, [
            Field("loads.combination_mode", "Tryb kombinacji", "choice",
                  choices=[("auto", "Automatyczne (EN 1990)"), ("manual", "Ręczne")]),
            Field("loads.settings.method", "Wzór SGN", "choice", choices=[("6.10ab", "(6.10a) i (6.10b)"),
                                                                        ("6.10", "(6.10)")]),
            Field("loads.settings.gamma_G_sup", "γ_G,sup", "float", None, 1.0, 2.0, 3),
            Field("loads.settings.gamma_Q", "γ_Q", "float", None, 1.0, 2.0, 3),
            Field("loads.settings.xi", "ξ", "float", None, 0.5, 1.0, 3),
            Field("loads.settings.include_sls", "Generuj kombinacje SGU", "bool"),
            Field("loads.settings.H_min_enabled", "Założenie H_Ed ≥ k·V_Ed", "bool"),
            Field("loads.settings.H_min_ratio", "k (H_min/V)", "float", None, 0.0, 1.0, 3,
                  enabled_if=lambda v: v.loads.settings.H_min_enabled),
            Field("loads.settings.H_min_source", "Źródło / uzasadnienie założenia", "text",
                  enabled_if=lambda v: v.loads.settings.H_min_enabled),
        ]))
        g2 = QGroupBox(tr("Kombinacje ręczne (mnożniki: nazwa=wartość; …)"))
        g2l = QVBoxLayout(g2)
        self.tbl_combos = QTableWidget(0, 3)
        self.tbl_combos.setHorizontalHeaderLabels([tr("Nazwa"), tr("Typ"), tr("Mnożniki")])
        self.tbl_combos.horizontalHeader().setStretchLastSection(True)
        self.tbl_combos.verticalHeader().setVisible(False)
        self.tbl_combos.itemChanged.connect(self._combos_from_table)
        g2l.addWidget(self.tbl_combos)
        r2 = QHBoxLayout()
        for txt, fn in ((tr("Dodaj"), self._add_combo), (tr("Usuń"), self._del_combo)):
            bt = QPushButton(txt)
            bt.clicked.connect(fn)
            r2.addWidget(bt)
        r2.addStretch(1)
        g2l.addLayout(r2)
        lay.addWidget(g2, 2)
        return w

    def _set_action_headers(self) -> None:
        u = DISPLAY
        heads = ["Nazwa", "Strona", "Kategoria", "Charakter", "Źródło", f"V [{u.force}]", f"H [{u.force}]",
                 f"M [{u.moment}]", f"e_x [{u.length}]", f"e_y [{u.length}]", "Opis"]
        self.tbl_actions.setHorizontalHeaderLabels([tr(h) for h in heads])

    def _combo_cell(self, items: list[tuple[str, str]], current: str, cb) -> QComboBox:
        box = QComboBox()
        for k, lab in items:
            box.addItem(lab, k)
        idx = next((i for i, (k, _) in enumerate(items) if k == current), 0)
        box.setCurrentIndex(idx)
        box.currentIndexChanged.connect(cb)
        return box

    def _load_actions(self) -> None:
        v = self.vg()
        t = self.tbl_actions
        t.blockSignals(True)
        t.setRowCount(len(v.loads.actions))
        for r, a in enumerate(v.loads.actions):
            t.setItem(r, 0, QTableWidgetItem(a.name))
            t.setCellWidget(r, 1, self._combo_cell([("R", "P (prawy)"), ("L", "L (lewy)")], a.side,
                                                   lambda _i, r=r: self._actions_from_table()))
            t.setCellWidget(r, 2, self._combo_cell(list(CATEGORIES.items()), a.category,
                                                   lambda _i, r=r: self._actions_from_table()))
            t.setCellWidget(r, 3, self._combo_cell([("characteristic", "charakterystyczne"),
                                                    ("design", "obliczeniowe")], a.nature,
                                                   lambda _i, r=r: self._actions_from_table()))
            t.setCellWidget(r, 4, self._combo_cell(list(SOURCES.items()), a.source,
                                                   lambda _i, r=r: self._actions_from_table()))
            vals = [from_base(a.V, F, DISPLAY.force), from_base(a.H, F, DISPLAY.force),
                    from_base(a.M, M, DISPLAY.moment), from_base(a.e_x, L, DISPLAY.length),
                    from_base(a.e_y, L, DISPLAY.length)]
            for k, val in enumerate(vals):
                it = QTableWidgetItem(f"{val:.4g}")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t.setItem(r, 5 + k, it)
            t.setItem(r, 10, QTableWidgetItem(a.note))
        t.blockSignals(False)
        t.resizeColumnsToContents()

    def _actions_from_table(self, *_):
        if self._loading:
            return
        v = self.vg()
        t = self.tbl_actions
        out = []
        for r in range(t.rowCount()):
            def txt(c):
                it = t.item(r, c)
                return it.text() if it else ""

            def num(c):
                try:
                    return float(txt(c).replace(",", "."))
                except ValueError:
                    return 0.0
            out.append(LoadAction(name=txt(0).strip() or f"A{r + 1}", side=t.cellWidget(r, 1).currentData(),
                                  category=t.cellWidget(r, 2).currentData(), nature=t.cellWidget(r, 3).currentData(),
                                  source=t.cellWidget(r, 4).currentData(),
                                  V=to_base(num(5), F, DISPLAY.force), H=to_base(num(6), F, DISPLAY.force),
                                  M=to_base(num(7), M, DISPLAY.moment), e_x=to_base(num(8), L, DISPLAY.length),
                                  e_y=to_base(num(9), L, DISPLAY.length), note=txt(10)))
        v.loads.actions = out
        self.changed.emit("loads.actions")

    def _add_action(self):
        v = self.vg()
        names = {a.name for a in v.loads.actions}
        k = len(v.loads.actions) + 1
        while f"Q{k}" in names:
            k += 1
        v.loads.actions.append(LoadAction(name=f"Q{k}", category="Q_B", V=50e3))
        self._load_actions()
        self.changed.emit("loads.actions")

    def _del_action(self):
        r = self.tbl_actions.currentRow()
        v = self.vg()
        if 0 <= r < len(v.loads.actions):
            del v.loads.actions[r]
            self._load_actions()
            self.changed.emit("loads.actions")

    def _load_combos(self) -> None:
        v = self.vg()
        t = self.tbl_combos
        t.blockSignals(True)
        t.setRowCount(len(v.loads.combinations))
        for r, c in enumerate(v.loads.combinations):
            t.setItem(r, 0, QTableWidgetItem(c.name))
            t.setCellWidget(r, 1, self._combo_cell(list(COMB_KINDS.items()), c.kind,
                                                   lambda _i: self._combos_from_table()))
            t.setItem(r, 2, QTableWidgetItem("; ".join(f"{k}={val:g}" for k, val in c.factors.items())))
        t.blockSignals(False)

    def _combos_from_table(self, *_):
        if self._loading:
            return
        v = self.vg()
        t = self.tbl_combos
        out = []
        for r in range(t.rowCount()):
            name = t.item(r, 0).text() if t.item(r, 0) else f"K{r + 1}"
            facs = {}
            raw = t.item(r, 2).text() if t.item(r, 2) else ""
            for part in raw.split(";"):
                if "=" in part:
                    k, val = part.split("=", 1)
                    try:
                        facs[k.strip()] = float(val.strip().replace(",", "."))
                    except ValueError:
                        pass
            out.append(LoadCombination(name, t.cellWidget(r, 1).currentData(), facs))
        v.loads.combinations = out
        self.changed.emit("loads.combinations")

    def _add_combo(self):
        v = self.vg()
        v.loads.combinations.append(LoadCombination(f"K{len(v.loads.combinations) + 1}", "ULS",
                                                    {a.name: (1.35 if a.category == "G" else 1.5)
                                                     for a in v.loads.actions if a.nature == "characteristic"}))
        self._load_combos()
        self.changed.emit("loads.combinations")

    def _del_combo(self):
        r = self.tbl_combos.currentRow()
        v = self.vg()
        if 0 <= r < len(v.loads.combinations):
            del v.loads.combinations[r]
            self._load_combos()
            self.changed.emit("loads.combinations")

    # --- Model STM -----------------------------------------------------
    def _stm_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        b = self.binder
        auto = lambda v: v.stm.mode == "auto"  # noqa: E731
        user = lambda v: v.stm.mode == "auto" and v.stm.lever_arm == "user"  # noqa: E731
        lay.addWidget(_group("Wybór modelu", b, [
            Field("stm.mode", "Model", "choice", choices=[("auto", "Automatyczny (J.3, rys. J.5)"),
                                                          ("manual", "Ręczny (edytor STM)")]),
            Field("stm.lever_arm", "Dobór strefy ściskanej x_c", "choice",
                  choices=[("optimal", "Optymalny (dolna ocena nośności)"),
                           ("node_limit", "Z warunku σ_Rd,max węzła"), ("user", "Wartość użytkownika")],
                  enabled_if=auto),
            Field("stm.node_b_position", "Położenie węzła B", "choice",
                  choices=[("in_column", "W słupie (konserwatywnie)"), ("face", "Na licu słupa (rys. J.5)")],
                  enabled_if=auto),
            Field("stm.strut_limit", "Nośność krzyżulca", "choice",
                  choices=[("6.56", "(6.56) 0,6·ν'·f_cd — strefa zarysowana"), ("6.55", "(6.55) f_cd")]),
            Field("stm.include_aH", "Uwzględnij ramię a_H siły H", "bool", enabled_if=auto),
            Field("stm.neglect_favourable_H", "Pomijaj korzystną siłę H (do słupa)", "bool", enabled_if=auto),
            Field("stm.node_10pct", "Zwiększenie σ_Rd,max węzłów o 10% (6.5.4(5))", "bool"),
            Field("stm.node_10pct_justification", "Uzasadnienie zwiększenia (warunki 6.5.4(5))", "text",
                  enabled_if=lambda v: v.stm.node_10pct),
        ]))
        lay.addWidget(_group("Korekty ręczne parametrów pochodnych — wspornik P", b, [
            Field("geometry.right.x_c_user", "Strefa ściskana x_c", "optfloat", L, 1, 3000, enabled_if=user),
            Field("geometry.right.z0_user", "Ramię z0 (gdy brak x_c)", "optfloat", L, 1, 3000, enabled_if=user),
            Field("geometry.right.a_H_user", "Ramię a_H siły H", "optfloat", L, 0, 1000, enabled_if=auto),
            Field("geometry.right.d_user", "Wysokość użyteczna d", "optfloat", L, 10, 5000, enabled_if=auto),
        ]))
        lay.addWidget(_group("Korekty ręczne — wspornik L", b, [
            Field("geometry.left.x_c_user", "Strefa ściskana x_c", "optfloat", L, 1, 3000,
                  enabled_if=lambda v: user(v) and v.geometry.layout == Layout.DOUBLE and not v.geometry.left_mirror),
            Field("geometry.left.z0_user", "Ramię z0", "optfloat", L, 1, 3000,
                  enabled_if=lambda v: user(v) and v.geometry.layout == Layout.DOUBLE and not v.geometry.left_mirror),
        ]))
        g = QGroupBox(tr("Edytor ręczny modelu STM (współrzędne globalne [mm], siły obliczeniowe [kN])"))
        gl = QVBoxLayout(g)
        self.btn_copy_auto = QPushButton(tr("Kopiuj z modelu automatycznego"))
        self.btn_copy_auto.clicked.connect(self.requestCopyAutoModel.emit)
        gl.addWidget(self.btn_copy_auto)
        self.man_tables = {}
        specs = {
            "nodes": (["Id", "x [mm]", "y [mm]"], ManualNode),
            "members": (["Id", "Węzeł 1", "Węzeł 2", "Typ (strut/tie)", "w [mm]", "t [mm]", "A_s [mm²]"], ManualMember),
            "supports": (["Węzeł", "u_x (1/0)", "u_y (1/0)", "szer. docisku [mm]"], ManualSupport),
            "loads": (["Węzeł", "F_x [kN]", "F_y [kN]"], ManualLoad),
        }
        titles = {"nodes": "Węzły", "members": "Pręty", "supports": "Podpory", "loads": "Obciążenia węzłowe"}
        for key, (cols, _cls) in specs.items():
            gl.addWidget(QLabel(f"<b>{tr(titles[key])}</b>"))
            t = QTableWidget(0, len(cols))
            t.setHorizontalHeaderLabels([tr(c) for c in cols])
            t.verticalHeader().setVisible(False)
            t.horizontalHeader().setStretchLastSection(True)
            t.setMinimumHeight(110)
            t.itemChanged.connect(lambda _it, key=key: self._manual_from_tables(key))
            gl.addWidget(t)
            rr = QHBoxLayout()
            for txt, fn in ((tr("Dodaj"), lambda _=False, key=key: self._manual_add(key)),
                            (tr("Usuń"), lambda _=False, key=key: self._manual_del(key))):
                bt = QPushButton(txt)
                bt.clicked.connect(fn)
                rr.addWidget(bt)
            rr.addStretch(1)
            gl.addLayout(rr)
            self.man_tables[key] = t
        lay.addWidget(g)
        lay.addStretch(1)
        return w

    def _load_manual(self) -> None:
        man = self.vg().stm.manual
        rows = {
            "nodes": [[n.id, f"{n.x:g}", f"{n.y:g}"] for n in man.nodes],
            "members": [[m.id, m.n1, m.n2, m.kind, f"{m.width:g}", f"{m.thickness:g}", f"{m.As:g}"] for m in man.members],
            "supports": [[s.node, "1" if s.ux else "0", "1" if s.uy else "0", f"{s.bearing_width:g}"]
                         for s in man.supports],
            "loads": [[ld.node, f"{ld.Fx / 1e3:g}", f"{ld.Fy / 1e3:g}"] for ld in man.loads],
        }
        for key, t in self.man_tables.items():
            t.blockSignals(True)
            t.setRowCount(len(rows[key]))
            for r, vals in enumerate(rows[key]):
                for c, val in enumerate(vals):
                    t.setItem(r, c, QTableWidgetItem(val))
            t.blockSignals(False)

    def _manual_from_tables(self, key: str) -> None:
        if self._loading:
            return
        man = self.vg().stm.manual
        t = self.man_tables[key]

        def cell(r, c, default=""):
            it = t.item(r, c)
            return it.text().strip() if it and it.text().strip() else default

        def num(r, c, default=0.0):
            try:
                return float(cell(r, c, str(default)).replace(",", "."))
            except ValueError:
                return default
        n = t.rowCount()
        if key == "nodes":
            man.nodes = [ManualNode(cell(r, 0, f"N{r + 1}"), num(r, 1), num(r, 2)) for r in range(n)]
        elif key == "members":
            man.members = [ManualMember(cell(r, 0, f"M{r + 1}"), cell(r, 1), cell(r, 2),
                                        "tie" if cell(r, 3, "strut").lower().startswith("t") else "strut",
                                        num(r, 4, 100.0), num(r, 5, 400.0), num(r, 6, 0.0)) for r in range(n)]
        elif key == "supports":
            man.supports = [ManualSupport(cell(r, 0), cell(r, 1, "1") != "0", cell(r, 2, "1") != "0",
                                          num(r, 3, 100.0)) for r in range(n)]
        else:
            man.loads = [ManualLoad(cell(r, 0), num(r, 1) * 1e3, num(r, 2) * 1e3) for r in range(n)]
        self.changed.emit(f"stm.manual.{key}")

    def _manual_add(self, key: str) -> None:
        man = self.vg().stm.manual
        if key == "nodes":
            man.nodes.append(ManualNode(f"N{len(man.nodes) + 1}", 0.0, 0.0))
        elif key == "members":
            ids = [x.id for x in man.nodes]
            man.members.append(ManualMember(f"M{len(man.members) + 1}", ids[0] if ids else "",
                                            ids[-1] if ids else "", "strut"))
        elif key == "supports":
            man.supports.append(ManualSupport(man.nodes[0].id if man.nodes else ""))
        else:
            man.loads.append(ManualLoad(man.nodes[0].id if man.nodes else "", 0.0, -100e3))
        self._load_manual()
        self.changed.emit(f"stm.manual.{key}")

    def _manual_del(self, key: str) -> None:
        t = self.man_tables[key]
        r = t.currentRow()
        lst = getattr(self.vg().stm.manual, key)
        if 0 <= r < len(lst):
            del lst[r]
            self._load_manual()
            self.changed.emit(f"stm.manual.{key}")

    # --- Zbrojenie -----------------------------------------------------
    def _rebar_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        b = self.binder
        man = lambda v: not v.reinforcement.main.auto  # noqa: E731
        lay.addWidget(_group("Zbrojenie główne (cięgno)", b, [
            Field("reinforcement.main.auto", "Dobór automatyczny", "bool"),
            Field("reinforcement.main.phi", "Średnica φ", "choice", choices=DIAMS, enabled_if=man),
            Field("reinforcement.main.n_per_layer", "Liczba prętów w warstwie", "int", None, 1, 30, enabled_if=man),
            Field("reinforcement.main.layers", "Liczba warstw", "int", None, 1, 3, enabled_if=man),
            Field("reinforcement.main.layer_gap", "Odstęp warstw w świetle", "optfloat", L, 10, 200),
            Field("reinforcement.main.anchor_load", "Zakotwienie przy końcu wspornika", "choice",
                  choices=[("loop", "Pętla pozioma"), ("bend_down", "Odgięcie 90° w dół"),
                           ("welded_bar", "Przyspawany pręt poprzeczny"), ("straight", "Pręt prosty"),
                           ("mechanical", "Zakotwienie mechaniczne (ETA)")]),
            Field("reinforcement.main.anchor_column", "Zakotwienie w słupie", "choice",
                  choices=[("bend_down", "Odgięcie 90° w dół"), ("straight", "Pręt prosty"),
                           ("continuous", "Pręt ciągły (dwustronne)"), ("mechanical", "Zakotwienie mechaniczne (ETA)")]),
            Field("reinforcement.main.mandrel_load", "Średnica trzpienia przy końcu φ_m", "optfloat", L, 10, 1000),
            Field("reinforcement.main.mandrel_column", "Średnica trzpienia w słupie φ_m", "optfloat", L, 10, 1000),
            Field("reinforcement.main.front_leg", "Ramię pionowe na końcu", "optfloat", L, 0, 2000),
            Field("reinforcement.main.column_leg", "Ramię pionowe w słupie", "optfloat", L, 0, 5000),
            Field("reinforcement.main.welded_bar_phi", "Średnica pręta przyspawanego φ_t", "optfloat", L, 6, 40),
            Field("reinforcement.main.bond", "Warunki przyczepności (rys. 8.2)", "choice",
                  choices=[("poor", "Słabe (η₁ = 0,7)"), ("good", "Dobre (η₁ = 1,0)")]),
            Field("reinforcement.main.alpha3_mode", "Współczynnik α₃", "choice",
                  choices=[("conservative", "α₃ = 1,0 (konserwatywnie)"), ("computed", "Obliczony (strzemiona)")]),
            Field("reinforcement.main.K_alpha3", "K (rys. 8.4)", "float", None, 0.0, 0.1, 3,
                  enabled_if=lambda v: v.reinforcement.main.alpha3_mode == "computed"),
        ]))
        ml = lambda v: not v.reinforcement.links.auto  # noqa: E731
        lay.addWidget(_group("Strzemiona i pręty dodatkowe", b, [
            Field("reinforcement.links.auto", "Dobór automatyczny", "bool"),
            Field("reinforcement.links.h_phi", "Strzemiona poziome φ", "choice", choices=DIAMS, enabled_if=ml),
            Field("reinforcement.links.h_count", "Strzemiona poziome — liczba", "int", None, 0, 30, enabled_if=ml),
            Field("reinforcement.links.h_zone", "Strefa strzemion poziomych", "optfloat", L, 10, 3000),
            Field("reinforcement.links.v_phi", "Strzemiona pionowe φ", "choice", choices=DIAMS, enabled_if=ml),
            Field("reinforcement.links.v_count", "Strzemiona pionowe — liczba", "int", None, 0, 30, enabled_if=ml),
            Field("reinforcement.links.i_phi", "Pręty ukośne (J.3(5)) φ", "choice", choices=DIAMS),
            Field("reinforcement.links.i_count", "Pręty ukośne — liczba", "int", None, 0, 10),
            Field("reinforcement.links.min_constructive_h", "Min. liczba strzemion poziomych (zalecenie)", "int",
                  None, 0, 10),
        ]))
        g = QGroupBox(tr("Średnice dopuszczone w doborze automatycznym"))
        hl = QHBoxLayout(g)
        self.diam_checks = {}
        for d in (10.0, 12.0, 14.0, 16.0, 20.0, 25.0, 28.0, 32.0):
            cb = QCheckBox(f"φ{d:.0f}")
            cb.toggled.connect(self._diams_changed)
            hl.addWidget(cb)
            self.diam_checks[d] = cb
        lay.addWidget(g)
        lay.addStretch(1)
        return w

    def _diams_changed(self, *_):
        if self._loading:
            return
        v = self.vg()
        v.reinforcement.allowed_diameters = [d for d, cb in self.diam_checks.items() if cb.isChecked()]
        self.changed.emit("reinforcement.allowed_diameters")

    # --- Parametry normowe ---------------------------------------------
    def _norm_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        b = self.binder
        lay.addWidget(_group("Edycja normy i status NDP", b, [
            Field("normative.edition", "Edycja", "choice", choices=[(k, e.title) for k, e in EDITIONS.items()]),
            Field("normative.ndp_confirmed", "Potwierdzam zgodność NDP z obowiązującym Załącznikiem Krajowym", "bool"),
            Field("normative.apply_engineering_recommendations", "Stosuj zalecenia inżynierskie (sprawdzenia "
                  "pomocnicze)", "bool"),
        ]))
        self.tbl_norm = QTableWidget(0, 8)
        self.tbl_norm.setHorizontalHeaderLabels([tr(h) for h in ("Parametr", "Symbol", "Wartość", "Jedn.", "Źródło",
                                                                  "Kategoria", "Status", "Potwierdzony")])
        self.tbl_norm.verticalHeader().setVisible(False)
        self.tbl_norm.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_norm.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tbl_norm.itemChanged.connect(self._norm_from_table)
        lay.addWidget(self.tbl_norm, 1)
        row = QHBoxLayout()
        bt = QPushButton(tr("Przywróć wartości domyślne"))
        bt.clicked.connect(self._norm_reset)
        row.addWidget(bt)
        row.addWidget(QLabel(tr("Zmiana wartości parametru wymaga wpisania uzasadnienia (kolumna Status).")))
        row.addStretch(1)
        lay.addLayout(row)
        return w

    def _load_norm(self) -> None:
        v = self.vg()
        t = self.tbl_norm
        t.blockSignals(True)
        ed = EDITIONS.get(v.normative.edition)
        params = list(ed.params.values()) if ed else []
        t.setRowCount(len(params))
        for r, p in enumerate(params):
            val = v.normative.overrides.get(p.key, p.value)
            items = [p.key, p.symbol, f"{val:g}", p.unit, p.clause, CATEGORY_LABEL[p.category],
                     v.normative.override_notes.get(p.key, p.status) if p.key in v.normative.overrides else p.status]
            for c, txt in enumerate(items):
                it = QTableWidgetItem(txt)
                if c != 2 and c != 6:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if c == 2 and not p.editable:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if c == 6 and p.key not in v.normative.overrides:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setToolTip(p.description + (f"\nNA: {p.na_note}" if p.na_note else "") +
                              (f"\nWartość zalecana EN: {p.recommended:g}" if p.recommended is not None else ""))
                t.setItem(r, c, it)
            chk = QTableWidgetItem("")
            if p.blocking:
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(Qt.Checked if p.key in v.normative.confirmed_params else Qt.Unchecked)
            else:
                chk.setFlags(Qt.ItemIsEnabled)
                chk.setText("—")
            t.setItem(r, 7, chk)
        t.blockSignals(False)
        t.resizeColumnsToContents()

    def _norm_from_table(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        v = self.vg()
        ed = EDITIONS.get(v.normative.edition)
        if ed is None:
            return
        r = item.row()
        key = self.tbl_norm.item(r, 0).text()
        p = ed.params[key]
        if item.column() == 2:
            try:
                val = float(item.text().replace(",", "."))
            except ValueError:
                self._load_norm()
                return
            if abs(val - p.value) < 1e-12:
                v.normative.overrides.pop(key, None)
                v.normative.override_notes.pop(key, None)
            else:
                v.normative.overrides[key] = val
                v.normative.override_notes.setdefault(key, "zmienione przez użytkownika — wpisz uzasadnienie")
        elif item.column() == 6 and key in v.normative.overrides:
            v.normative.override_notes[key] = item.text()
        elif item.column() == 7 and p.blocking:
            s = set(v.normative.confirmed_params)
            if item.checkState() == Qt.Checked:
                s.add(key)
            else:
                s.discard(key)
            v.normative.confirmed_params = sorted(s)
        self._loading = True
        self._load_norm()
        self._loading = False
        self.changed.emit("normative.params")

    def _norm_reset(self) -> None:
        v = self.vg()
        v.normative.overrides.clear()
        v.normative.override_notes.clear()
        self._load_norm()
        self.changed.emit("normative.params")

    def load_diams(self) -> None:
        v = self.vg()
        for d, cb in self.diam_checks.items():
            cb.blockSignals(True)
            cb.setChecked(d in v.reinforcement.allowed_diameters)
            cb.blockSignals(False)
