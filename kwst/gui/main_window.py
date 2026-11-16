"""Główne okno aplikacji KRÓTKI WSPORNIK ST."""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSettings, QByteArray
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QFileDialog, QInputDialog, QLabel,
                               QMainWindow, QMessageBox, QToolBar, QWidget, QSizePolicy)

from ..analysis import run_analysis
from ..core.model import Project, Variant, Layout
from ..core.serialization import to_dict, from_dict
from ..core.units import DISPLAY
from ..load_engine import import_actions_csv, import_actions_excel, export_actions_csv, LoadError
from ..project_io import (save_project, load_project, autosave, latest_autosave, load_library, ProjectFileError, EXT)
from ..stm_generator import manual_from_result
from ..validation_engine import hash_obj
from ..version import APP_NAME, __version__
from ..visualization_engine import build_scene, verify_scene, LAYERS, VIEW_NAMES
from .canvas import DrawingView
from .dialogs import (HelpDialog, model_info_dialog, module_status_dialog, about_dialog, schedule_dialog,
                      OptimizerDialog, LibraryDialog, PrintPreviewDialog, ProjectInfoDialog, SettingsDialog)
from .i18n import tr, set_language
from .input_panel import InputPanel
from .results_panel import ResultsPanel, ChecksPanel
from .themes import apply_theme

log = logging.getLogger("kwst.gui")
FILTER = f"Projekt KRÓTKI WSPORNIK ST (*{EXT});;Wszystkie pliki (*)"


class MainWindow(QMainWindow):
    def __init__(self, project: Project | None = None, settings: QSettings | None = None):
        super().__init__()
        self.settings = settings or QSettings("KrotkiWspornikST", "KWST")
        self.project = project or Project()
        self.path: str | None = None
        self.dirty = False
        self.result = None
        self.theme = self.settings.value("theme", "light")
        self.auto_calc = self.settings.value("auto_calc", "true") in (True, "true", "1")
        self._undo: list[str] = []
        self._undo_idx = -1
        self._selected_combo: str | None = None
        self.setWindowTitle(APP_NAME)
        # --- widgety
        self.canvas = DrawingView(self)
        self.canvas.theme = self.theme
        self.setCentralWidget(self.canvas)
        self.inputs = InputPanel(self._variant, self)
        self.results = ResultsPanel(self)
        self.results.theme = self.theme
        self.checks = ChecksPanel(self)
        self.checks.theme = self.theme
        self.dock_in = self._dock(tr("Dane wejściowe"), self.inputs, Qt.LeftDockWidgetArea, "dock_inputs")
        self.dock_res = self._dock(tr("Wyniki"), self.results, Qt.RightDockWidgetArea, "dock_results")
        self.dock_chk = self._dock(tr("Szczegółowe obliczenia"), self.checks, Qt.BottomDockWidgetArea, "dock_checks")
        self.resizeDocks([self.dock_in, self.dock_res], [430, 420], Qt.Horizontal)
        self.resizeDocks([self.dock_chk], [240], Qt.Vertical)
        # --- akcje i menu
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        self.coord_label = QLabel()
        self.statusBar().addWidget(self.coord_label)
        # --- sygnały
        self.inputs.changed.connect(self._on_input_changed)
        self.inputs.requestCopyAutoModel.connect(self._copy_auto_model)
        self.inputs.btn_import.clicked.connect(self.import_loads)
        self.inputs.btn_export.clicked.connect(self.export_loads)
        self.canvas.elementClicked.connect(self._on_element_clicked)
        self.canvas.handleMoved.connect(self._on_handle_moved)
        self.canvas.cursorMoved.connect(lambda x, y: self.coord_label.setText(f"x = {x:.0f} mm, y = {y:.0f} mm"))
        self.canvas.measured.connect(lambda d: self.statusBar().showMessage(f"Odległość: {d:.1f} mm", 8000))
        self.results.checkSelected.connect(self._on_check_selected)
        self.checks.checkSelected.connect(self._on_check_selected)
        # --- timery
        self._calc_timer = QTimer(self, singleShot=True, interval=350, timeout=self.calculate)
        self._snap_timer = QTimer(self, singleShot=True, interval=500, timeout=self._push_undo)
        self._auto_timer = QTimer(self, timeout=self._autosave)
        self._apply_autosave_interval()
        # --- start
        geo = self.settings.value("geometry")
        if isinstance(geo, QByteArray):
            self.restoreGeometry(geo)
        else:
            self.resize(1600, 980)
        st = self.settings.value("state")
        if isinstance(st, QByteArray):
            self.restoreState(st)
        self._load_project_into_ui()
        self._push_undo()
        self.calculate()
        if not isinstance(st, QByteArray):
            QTimer.singleShot(0, self._default_dock_sizes)

    def _default_dock_sizes(self) -> None:
        w = max(self.width(), 1200)
        self.resizeDocks([self.dock_in, self.dock_res], [int(w * 0.25), int(w * 0.24)], Qt.Horizontal)
        self.resizeDocks([self.dock_chk], [int(self.height() * 0.27)], Qt.Vertical)
        self.canvas.fit()

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        if not getattr(self, "_shown_once", False):
            self._shown_once = True
            if not isinstance(self.settings.value("state"), QByteArray):
                self._default_dock_sizes()

    # ------------------------------------------------------------------
    def _variant(self) -> Variant:
        return self.project.current

    def _dock(self, title, widget, area, name) -> QDockWidget:
        d = QDockWidget(title, self)
        d.setObjectName(name)
        d.setWidget(widget)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(area, d)
        return d

    def _act(self, text, slot=None, shortcut=None, checkable=False, checked=False, tip="") -> QAction:
        a = QAction(tr(text), self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if checkable:
            a.setCheckable(True)
            a.setChecked(checked)
        if slot:
            a.triggered.connect(slot)
        if tip:
            a.setStatusTip(tip)
        return a

    def _build_actions(self) -> None:
        A = self._act
        self.a_new = A("Nowy projekt", self.new_project, QKeySequence.New)
        self.a_open = A("Otwórz…", self.open_project, QKeySequence.Open)
        self.a_save = A("Zapisz", self.save_project, QKeySequence.Save)
        self.a_saveas = A("Zapisz jako…", self.save_project_as, QKeySequence.SaveAs)
        self.a_info = A("Dane projektu…", self.edit_project_info)
        self.a_lib = A("Biblioteka typowych wsporników…", self.open_library)
        self.a_import = A("Import obciążeń (CSV/Excel)…", self.import_loads)
        self.a_pdf = A("Raport PDF…", self.export_pdf, "Ctrl+P")
        self.a_xlsx = A("Arkusz Excel…", self.export_excel)
        self.a_csv = A("Sprawdzenia CSV…", self.export_csv)
        self.a_json = A("Dane i wyniki JSON…", self.export_json)
        self.a_dxf = A("Rysunek DXF…", self.export_dxf)
        self.a_preview = A("Podgląd wydruku…", self.print_preview, "Ctrl+Shift+P")
        self.a_recover = A("Odzyskaj autozapis…", self.recover_autosave)
        self.a_quit = A("Zakończ", self.close, QKeySequence.Quit)
        self.a_undo = A("Cofnij", self.undo, QKeySequence.Undo)
        self.a_redo = A("Ponów", self.redo, QKeySequence.Redo)
        self.a_dup = A("Kopiuj wariant", self.duplicate_variant, "Ctrl+D")
        self.a_delv = A("Usuń wariant", self.delete_variant)
        self.a_renv = A("Zmień nazwę wariantu…", self.rename_variant)
        self.a_settings = A("Ustawienia…", self.open_settings)
        self.a_calc = A("Oblicz", self.calculate, "F5")
        self.a_auto = A("Obliczenia automatyczne", self._toggle_auto, checkable=True, checked=self.auto_calc)
        self.a_apply_rebar = A("Przenieś dobrane zbrojenie do danych", self.apply_designed_rebar)
        self.a_opt = A("Optymalizacja…", self.open_optimizer)
        self.a_sched = A("Zestawienie stali…", self.show_schedule)
        self.a_fit = A("Dopasuj widok", self.canvas.fit, "F")
        self.a_crit = A("Podświetl element krytyczny", self._toggle_crit, checkable=True, checked=True)
        self.a_handles = A("Edycja uchwytami", self._toggle_handles, checkable=True, checked=True)
        self.a_measure = A("Narzędzie pomiaru", self._toggle_measure, "M", checkable=True)
        self.a_dark = A("Motyw ciemny", self._toggle_theme, checkable=True, checked=self.theme == "dark")
        self.a_help = A("Pomoc — parametry", lambda: HelpDialog(self).exec(), QKeySequence.HelpContents)
        self.a_model = A("Model obliczeniowy i ograniczenia", lambda: model_info_dialog(self, self.result).exec())
        self.a_status = A("Status walidacji modułów", lambda: module_status_dialog(self).exec())
        self.a_about = A("O programie", lambda: about_dialog(self))
        self.view_group = QActionGroup(self)
        self.view_actions = {}
        for i, (key, name) in enumerate(VIEW_NAMES.items()):
            a = A(name, lambda _=False, k=key: self.set_view(k), f"Ctrl+{i + 1}", checkable=True, checked=(key == "stm"))
            self.view_group.addAction(a)
            self.view_actions[key] = a

    def _build_menus(self) -> None:
        mb = self.menuBar()
        m = mb.addMenu(tr("&Plik"))
        for a in (self.a_new, self.a_open, self.a_save, self.a_saveas, None, self.a_info, self.a_lib, self.a_import):
            m.addSeparator() if a is None else m.addAction(a)
        ex = m.addMenu(tr("Eksport"))
        for a in (self.a_pdf, self.a_xlsx, self.a_csv, self.a_json, self.a_dxf):
            ex.addAction(a)
        m.addAction(self.a_preview)
        m.addSeparator()
        self.recent_menu = m.addMenu(tr("Ostatnie pliki"))
        self._update_recent()
        m.addAction(self.a_recover)
        m.addSeparator()
        m.addAction(self.a_quit)
        m = mb.addMenu(tr("&Edycja"))
        for a in (self.a_undo, self.a_redo, None, self.a_dup, self.a_renv, self.a_delv, None, self.a_settings):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu(tr("&Obliczenia"))
        for a in (self.a_calc, self.a_auto, None, self.a_apply_rebar, self.a_opt, self.a_sched):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu(tr("&Widok"))
        for a in self.view_actions.values():
            m.addAction(a)
        lm = m.addMenu(tr("Warstwy"))
        self.layer_actions = {}
        for key, name in LAYERS.items():
            a = QAction(name, self, checkable=True)
            a.setChecked(key in self.canvas.visible_layers)
            a.toggled.connect(lambda on, k=key: self.canvas.set_layer(k, on))
            lm.addAction(a)
            self.layer_actions[key] = a
        for a in (None, self.a_fit, self.a_crit, self.a_handles, self.a_measure, None, self.a_dark):
            m.addSeparator() if a is None else m.addAction(a)
        dm = m.addMenu(tr("Panele"))
        for d in (self.dock_in, self.dock_res, self.dock_chk):
            dm.addAction(d.toggleViewAction())
        m = mb.addMenu(tr("&Pomoc"))
        for a in (self.a_help, self.a_model, self.a_status, None, self.a_about):
            m.addSeparator() if a is None else m.addAction(a)

    def _build_toolbar(self) -> None:
        tb = QToolBar(tr("Narzędzia"), self)
        tb.setObjectName("toolbar_main")
        self.addToolBar(tb)
        for a in (self.a_new, self.a_open, self.a_save, None, self.a_undo, self.a_redo, None, self.a_calc, self.a_auto,
                  None, self.a_pdf, self.a_preview):
            tb.addSeparator() if a is None else tb.addAction(a)
        tb.addSeparator()
        tb.addWidget(QLabel(" " + tr("Wariant:") + " "))
        self.variant_combo = QComboBox()
        self.variant_combo.setMinimumWidth(170)
        self.variant_combo.activated.connect(self._switch_variant)
        tb.addWidget(self.variant_combo)
        tb.addAction(self.a_dup)
        tb.addSeparator()
        tb.addWidget(QLabel(" " + tr("Widok:") + " "))
        self.view_combo = QComboBox()
        for k, n in VIEW_NAMES.items():
            self.view_combo.addItem(n, k)
        self.view_combo.setCurrentIndex(1)
        self.view_combo.activated.connect(lambda i: self.set_view(self.view_combo.itemData(i)))
        tb.addWidget(self.view_combo)
        tb.addWidget(QLabel(" " + tr("Kombinacja:") + " "))
        self.combo_combo = QComboBox()
        self.combo_combo.setMinimumWidth(190)
        self.combo_combo.activated.connect(self._switch_combo)
        tb.addWidget(self.combo_combo)
        tb.addAction(self.a_fit)
        tb.addAction(self.a_measure)

    # ------------------------------------------------------------------
    # Synchronizacja danych i obliczeń
    # ------------------------------------------------------------------
    def _load_project_into_ui(self) -> None:
        self.variant_combo.blockSignals(True)
        self.variant_combo.clear()
        for v in self.project.variants:
            self.variant_combo.addItem(v.name)
        self.variant_combo.setCurrentIndex(self.project.active)
        self.variant_combo.blockSignals(False)
        self.inputs.load()
        self._update_title()

    def _update_title(self) -> None:
        name = Path(self.path).name if self.path else tr("(nowy projekt)")
        self.setWindowTitle(f"{APP_NAME} {__version__} — {self.project.info.name} [{name}]{' *' if self.dirty else ''}")

    def _on_input_changed(self, path: str) -> None:
        self.dirty = True
        self._update_title()
        self._snap_timer.start()
        if self.auto_calc:
            self._calc_timer.start()
        else:
            self._mark_stale()

    def _is_fresh(self) -> bool:
        return self.result is not None and self.result.input_hash == hash_obj(self._variant())

    def _mark_stale(self) -> None:
        self.results.set_stale()
        self.refresh_view()
        self._update_status()

    def calculate(self) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.result = run_analysis(self._variant())
        except Exception as exc:  # noqa: BLE001
            log.exception("Błąd analizy")
            QMessageBox.critical(self, APP_NAME, f"Błąd obliczeń:\n{exc}\n\n{traceback.format_exc()[-1500:]}")
            self.result = None
        finally:
            QApplication.restoreOverrideCursor()
        if self.result is not None:
            self.results.show_result(self.result)
            self.checks.show_result(self.result)
            self._fill_combos()
            self._update_auto_hints()
        self.refresh_view()
        self._update_status()

    def _fill_combos(self) -> None:
        self.combo_combo.blockSignals(True)
        self.combo_combo.clear()
        names = list(self.result.stm.keys()) if self.result else []
        for nme in names:
            self.combo_combo.addItem(nme + ("  ★" if nme == self.result.governing else ""), nme)
        sel = self._selected_combo if self._selected_combo in names else (self.result.governing if self.result else "")
        idx = names.index(sel) if sel in names else 0
        self.combo_combo.setCurrentIndex(idx)
        self.combo_combo.blockSignals(False)

    def _switch_combo(self, i: int) -> None:
        self._selected_combo = self.combo_combo.itemData(i)
        self.refresh_view()

    def refresh_view(self, refit: bool = False) -> None:
        fresh = self._is_fresh()
        try:
            sc = build_scene(self._variant(), self.result if fresh else None, self.canvas.mode,
                             self._selected_combo, stale=not fresh)
        except Exception as exc:  # noqa: BLE001
            log.exception("Błąd rysunku")
            self.statusBar().showMessage(f"Błąd rysunku: {exc}", 10000)
            return
        issues = verify_scene(sc, self.result if fresh else None)
        if issues:
            log.error("Niezgodność rysunku z modelem: %s", issues)
            QMessageBox.critical(self, APP_NAME, "Wykryto niezgodność rysunku z modelem obliczeniowym:\n" +
                                 "\n".join(issues))
        self.canvas.set_scene_data(sc, refit)

    def _update_status(self) -> None:
        r = self.result
        ed = self._variant().normative.edition
        fresh = self._is_fresh()
        txt = f"Norma: {ed} | Jednostki: {DISPLAY.force}, {DISPLAY.length}, {DISPLAY.stress} | "
        txt += (f"Wynik: {r.verdict.title}" if (r and fresh) else "Wyniki nieaktualne")
        txt += f" | Auto: {'wł.' if self.auto_calc else 'wył.'}"
        self.status_label.setText(txt)

    def _update_auto_hints(self) -> None:
        r = self.result
        if r is None or r.governing_stm is None:
            return
        for sd, sm in r.governing_stm.sides.items():
            pre = "geometry.right" if sd == "R" else "geometry.left"
            s, p = sm.state, sm.params
            self.inputs.binder.set_auto_hint(f"{pre}.x_c_user", f"auto: {s.x_c:.1f} mm")
            self.inputs.binder.set_auto_hint(f"{pre}.z0_user", f"auto: {s.z0:.1f} mm")
            self.inputs.binder.set_auto_hint(f"{pre}.a_H_user", f"auto: {p.a_H:.1f} mm")
            self.inputs.binder.set_auto_hint(f"{pre}.d_user", f"auto: {p.d:.1f} mm")
        if r.cover is not None:
            self.inputs.binder.set_auto_hint("materials.c_nom_user", f"auto: {r.cover.c_nom:.0f} mm")

    # ------------------------------------------------------------------
    # Cofnij / ponów
    # ------------------------------------------------------------------
    def _snapshot(self) -> str:
        return json.dumps(to_dict(self.project), ensure_ascii=False)

    def _push_undo(self) -> None:
        snap = self._snapshot()
        if self._undo and self._undo_idx >= 0 and self._undo[self._undo_idx] == snap:
            return
        self._undo = self._undo[: self._undo_idx + 1]
        self._undo.append(snap)
        if len(self._undo) > 300:
            self._undo = self._undo[-300:]
        self._undo_idx = len(self._undo) - 1
        self._update_undo_actions()

    def _restore(self, snap: str) -> None:
        self.project = from_dict(Project, json.loads(snap))
        self._load_project_into_ui()
        self.dirty = True
        self._update_title()
        self.calculate()

    def undo(self) -> None:
        if self._snap_timer.isActive():
            self._snap_timer.stop()
            self._push_undo()
        if self._undo_idx > 0:
            self._undo_idx -= 1
            self._restore(self._undo[self._undo_idx])
        self._update_undo_actions()

    def redo(self) -> None:
        if self._undo_idx < len(self._undo) - 1:
            self._undo_idx += 1
            self._restore(self._undo[self._undo_idx])
        self._update_undo_actions()

    def _update_undo_actions(self) -> None:
        self.a_undo.setEnabled(self._undo_idx > 0)
        self.a_redo.setEnabled(self._undo_idx < len(self._undo) - 1)

    def _commit_change(self) -> None:
        """Zmiana danych spoza formularzy (uchwyty, dialogi): odśwież formularze, zapamiętaj stan, przelicz."""
        self.inputs.load()
        self.dirty = True
        self._update_title()
        self._push_undo()
        if self.auto_calc:
            self.calculate()
        else:
            self._mark_stale()

    # ------------------------------------------------------------------
    # Interakcja z rysunkiem
    # ------------------------------------------------------------------
    def _on_element_clicked(self, ref: str) -> None:
        self.results.show_element(ref, self.result if self._is_fresh() else None)
        if self.result:
            rel = [c for c in self.result.checks if c.element_ref == ref]
            if rel:
                worst = max(rel, key=lambda c: (c.eta or 0))
                self.checks.select(worst.id)

    def _on_check_selected(self, cid: str) -> None:
        if not self.result:
            return
        c = next((x for x in self.result.checks if x.id == cid), None)
        if c is None:
            return
        self.checks.select(cid)
        if c.element_ref:
            self.canvas.select_ref(c.element_ref)
            self.results.show_element(c.element_ref, self.result)

    def _on_handle_moved(self, ref: str, x: float, y: float) -> None:
        v = self._variant()
        g = v.geometry
        parts = ref.split(":")
        kind = parts[1]
        try:
            if kind == "node":
                nid = parts[2]
                for nd in v.stm.manual.nodes:
                    if nd.id == nid:
                        nd.x, nd.y = round(x, 1), round(y, 1)
            else:
                sd = parts[2]
                s = 1 if sd == "R" else -1
                si = g.right if (sd == "R" or g.left_mirror) else g.left
                xi = s * (x - s * g.column.h_col / 2.0)
                if kind == "a_c":
                    si.a_c = max(10.0, min(round(xi / 5) * 5, si.l_c - si.plate.length / 2 - 5))
                elif kind == "l_c":
                    si.l_c = max(round(xi / 5) * 5, si.a_c + si.plate.length / 2 + 10)
                elif kind == "h_e":
                    si.h_e = max(50.0, min(round(-y / 5) * 5, si.h_c))
                elif kind == "h_c":
                    si.h_c = max(round(-y / 5) * 5, si.h_e, 100.0)
                elif kind == "x_c":
                    v.stm.lever_arm = "user"
                    si.x_c_user = max(1.0, round(2.0 * (si.h_c + y), 1))
                    si.z0_user = None
        except Exception as exc:  # noqa: BLE001
            log.exception("Błąd edycji uchwytem")
            self.statusBar().showMessage(f"Nie można zastosować zmiany: {exc}", 8000)
        self._commit_change()

    def set_view(self, key: str) -> None:
        self.canvas.set_mode(key)
        for k, a in self.view_actions.items():
            a.setChecked(k == key)
        idx = self.view_combo.findData(key)
        self.view_combo.setCurrentIndex(idx)
        for lk, a in self.layer_actions.items():
            a.blockSignals(True)
            a.setChecked(lk in self.canvas.visible_layers)
            a.blockSignals(False)

    def _toggle_crit(self, on: bool) -> None:
        self.canvas.highlight_critical = on
        self.canvas.render()

    def _toggle_handles(self, on: bool) -> None:
        self.canvas.handles_enabled = on
        self.canvas.render()

    def _toggle_measure(self, on: bool) -> None:
        self.canvas.measure_mode = on
        self.statusBar().showMessage("Pomiar: kliknij dwa punkty na rysunku." if on else "", 6000)

    def _toggle_auto(self, on: bool) -> None:
        self.auto_calc = on
        self.settings.setValue("auto_calc", "true" if on else "false")
        if on:
            self.calculate()
        self._update_status()

    def _toggle_theme(self, on: bool) -> None:
        self.theme = "dark" if on else "light"
        self.settings.setValue("theme", self.theme)
        apply_theme(QApplication.instance(), self.theme, float(self.settings.value("scale", 1.0)))
        self.canvas.theme = self.results.theme = self.checks.theme = self.theme
        self.canvas.render()
        if self.result:
            self.results.show_result(self.result)
            self.checks.show_result(self.result)

    # ------------------------------------------------------------------
    # Warianty
    # ------------------------------------------------------------------
    def _switch_variant(self, i: int) -> None:
        self.project.active = i
        self._selected_combo = None
        self.inputs.load()
        self.calculate()
        self.refresh_view(refit=True)
        self._push_undo()

    def duplicate_variant(self) -> None:
        v = copy.deepcopy(self._variant())
        v.name = self._unique_name(v.name + " (kopia)")
        self.project.variants.append(v)
        self.project.active = len(self.project.variants) - 1
        self._load_project_into_ui()
        self._commit_change()

    def _unique_name(self, base: str) -> str:
        names = {v.name for v in self.project.variants}
        name, k = base, 2
        while name in names:
            name = f"{base} {k}"
            k += 1
        return name

    def delete_variant(self) -> None:
        if len(self.project.variants) <= 1:
            QMessageBox.information(self, APP_NAME, "Projekt musi zawierać co najmniej jeden wariant.")
            return
        if QMessageBox.question(self, APP_NAME, f"Usunąć wariant '{self._variant().name}'?") != QMessageBox.Yes:
            return
        del self.project.variants[self.project.active]
        self.project.active = max(0, self.project.active - 1)
        self._load_project_into_ui()
        self._commit_change()

    def rename_variant(self) -> None:
        name, ok = QInputDialog.getText(self, APP_NAME, "Nazwa wariantu:", text=self._variant().name)
        if ok and name.strip():
            self._variant().name = self._unique_name(name.strip()) if name.strip() != self._variant().name else name
            self._load_project_into_ui()
            self._commit_change()

    def _add_variant(self, v: Variant) -> None:
        v.name = self._unique_name(v.name)
        self.project.variants.append(v)
        self.project.active = len(self.project.variants) - 1
        self._load_project_into_ui()
        self._commit_change()
        self.refresh_view(refit=True)

    # ------------------------------------------------------------------
    # Pliki
    # ------------------------------------------------------------------
    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        r = QMessageBox.question(self, APP_NAME, "Projekt zawiera niezapisane zmiany. Zapisać?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save_project()
        return r == QMessageBox.Discard

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self.project = Project()
        self.path = None
        self.dirty = False
        self._undo, self._undo_idx = [], -1
        self._load_project_into_ui()
        self._push_undo()
        self.calculate()
        self.refresh_view(refit=True)

    def open_project(self, path: str | None = None) -> None:
        if not self._confirm_discard():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("Otwórz…"), self._last_dir(), FILTER)
        if not path:
            return
        try:
            self.project = load_project(path)
        except ProjectFileError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        self.path = path
        self.dirty = False
        self._add_recent(path)
        self._undo, self._undo_idx = [], -1
        self._load_project_into_ui()
        self._push_undo()
        self.calculate()
        self.refresh_view(refit=True)

    def save_project(self) -> bool:
        if not self.path:
            return self.save_project_as()
        try:
            save_project(self.project, self.path)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"Błąd zapisu: {exc}")
            return False
        self.dirty = False
        self._update_title()
        self._add_recent(self.path)
        self.statusBar().showMessage(f"Zapisano: {self.path}", 5000)
        return True

    def save_project_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, tr("Zapisz jako…"), os.path.join(self._last_dir(),
                                              self.project.info.name + EXT), FILTER)
        if not path:
            return False
        if not path.endswith(EXT):
            path += EXT
        self.path = path
        return self.save_project()

    def _last_dir(self) -> str:
        return str(self.settings.value("last_dir", str(Path.home())))

    def _add_recent(self, path: str) -> None:
        rec = self.settings.value("recent", []) or []
        if isinstance(rec, str):
            rec = [rec]
        rec = [path] + [p for p in rec if p != path]
        self.settings.setValue("recent", rec[:10])
        self.settings.setValue("last_dir", str(Path(path).parent))
        self._update_recent()

    def _update_recent(self) -> None:
        self.recent_menu.clear()
        rec = self.settings.value("recent", []) or []
        if isinstance(rec, str):
            rec = [rec]
        for p in rec:
            a = self.recent_menu.addAction(p)
            a.triggered.connect(lambda _=False, p=p: self.open_project(p))
        self.recent_menu.setEnabled(bool(rec))

    def _apply_autosave_interval(self) -> None:
        m = int(self.settings.value("autosave_min", 3))
        self._auto_timer.stop()
        if m > 0:
            self._auto_timer.start(m * 60 * 1000)

    def _autosave(self) -> None:
        if not self.dirty:
            return
        try:
            p = autosave(self.project, Path(self.path).stem if self.path else "nowy_projekt")
            self.statusBar().showMessage(f"Autozapis: {p}", 4000)
        except OSError as exc:
            log.warning("Autozapis nieudany: %s", exc)

    def recover_autosave(self) -> None:
        p = latest_autosave()
        if p is None:
            QMessageBox.information(self, APP_NAME, "Brak plików autozapisu.")
            return
        if QMessageBox.question(self, APP_NAME, f"Otworzyć autozapis?\n{p}") == QMessageBox.Yes:
            self.open_project(str(p))
            self.path = None
            self.dirty = True
            self._update_title()

    def edit_project_info(self) -> None:
        dlg = ProjectInfoDialog(self.project.info, self)
        if dlg.exec():
            dlg.apply()
            self._commit_change()

    def open_library(self) -> None:
        items = load_library()
        if not items:
            QMessageBox.information(self, APP_NAME, "Biblioteka jest pusta.")
            return
        dlg = LibraryDialog(items, self)
        if dlg.exec() and dlg.selected():
            v = copy.deepcopy(dlg.selected().variant)
            v.name = dlg.selected().title
            self._add_variant(v)

    def import_loads(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Import obciążeń (CSV/Excel)…"), self._last_dir(),
                                              "CSV / Excel (*.csv *.xlsx);;Wszystkie (*)")
        if not path:
            return
        try:
            acts = import_actions_excel(path) if path.lower().endswith(".xlsx") else \
                import_actions_csv(Path(path).read_text(encoding="utf-8-sig"))
        except (LoadError, ValueError, OSError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Błąd importu: {exc}")
            return
        r = QMessageBox.question(self, APP_NAME, f"Wczytano {len(acts)} oddziaływań. Zastąpić istniejące "
                                                 "(Tak) czy dopisać (Nie)?",
                                 QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if r == QMessageBox.Cancel:
            return
        v = self._variant()
        v.loads.actions = acts if r == QMessageBox.Yes else v.loads.actions + acts
        self._commit_change()

    def export_loads(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, tr("Eksport CSV…"), "obciazenia.csv", "CSV (*.csv)")
        if path:
            Path(path).write_text(export_actions_csv(self._variant().loads.actions), encoding="utf-8-sig")

    # ------------------------------------------------------------------
    # Raport i eksport
    # ------------------------------------------------------------------
    def _ensure_result(self) -> bool:
        if not self._is_fresh():
            self.calculate()
        if self.result is None:
            QMessageBox.critical(self, APP_NAME, "Brak wyników obliczeń.")
            return False
        return True

    def _save_dialog(self, title, default, flt) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, title, os.path.join(self._last_dir(), default), flt)
        return path or None

    def _export(self, fn, title, ext, flt) -> None:
        if not self._ensure_result():
            return
        path = self._save_dialog(title, f"{self.project.info.element or 'wspornik'}{ext}", flt)
        if not path:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            fn(path)
            self.statusBar().showMessage(f"Zapisano: {path}", 6000)
        except Exception as exc:  # noqa: BLE001
            log.exception("Błąd eksportu")
            QMessageBox.critical(self, APP_NAME, f"Błąd eksportu: {exc}")
        finally:
            QApplication.restoreOverrideCursor()

    def export_pdf(self) -> None:
        from ..report_engine.pdf_report import generate_pdf
        self._export(lambda p: generate_pdf(self.project, self._variant(), self.result, p), tr("Raport PDF…"), ".pdf",
                     "PDF (*.pdf)")

    def export_excel(self) -> None:
        from ..report_engine.exporters import export_excel
        self._export(lambda p: export_excel(self.project, self._variant(), self.result, p), tr("Arkusz Excel…"),
                     ".xlsx", "Excel (*.xlsx)")

    def export_csv(self) -> None:
        from ..report_engine.exporters import export_csv_checks
        self._export(lambda p: export_csv_checks(self.result, p), tr("Sprawdzenia CSV…"), ".csv", "CSV (*.csv)")

    def export_json(self) -> None:
        from ..report_engine.exporters import export_json
        self._export(lambda p: export_json(self.project, self._variant(), self.result, p), tr("Dane i wyniki JSON…"),
                     ".json", "JSON (*.json)")

    def export_dxf(self) -> None:
        from ..report_engine.exporters import export_dxf
        self._export(lambda p: export_dxf(self._variant(), self.result, p), tr("Rysunek DXF…"), ".dxf", "DXF (*.dxf)")

    def print_preview(self) -> None:
        if not self._ensure_result():
            return
        from ..report_engine.pdf_report import generate_pdf
        fd, path = tempfile.mkstemp(suffix=".pdf", prefix="kwst_")
        os.close(fd)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            generate_pdf(self.project, self._variant(), self.result, path)
        finally:
            QApplication.restoreOverrideCursor()
        PrintPreviewDialog(path, self).exec()

    # ------------------------------------------------------------------
    # Obliczenia dodatkowe
    # ------------------------------------------------------------------
    def apply_designed_rebar(self) -> None:
        if not self._ensure_result() or self.result.main_input is None:
            QMessageBox.information(self, APP_NAME, "Brak dobranego zbrojenia.")
            return
        v = self._variant()
        mi = copy.deepcopy(self.result.main_input)
        mi.auto = False
        if v.geometry.layout != Layout.DOUBLE and mi.anchor_column == "continuous":
            mi.anchor_column = "bend_down"
        li = copy.deepcopy(self.result.links_input)
        li.auto = False
        v.reinforcement.main = mi
        v.reinforcement.links = li
        self._commit_change()
        self.statusBar().showMessage("Dobrane zbrojenie przeniesiono do danych (tryb ręczny).", 6000)

    def _copy_auto_model(self) -> None:
        if not self._ensure_result() or self.result.governing_stm is None or not self.result.governing_stm.sides:
            QMessageBox.information(self, APP_NAME, "Brak automatycznego modelu STM do skopiowania.")
            return
        v = self._variant()
        v.stm.manual = manual_from_result(self.result.governing_stm, v.geometry.b)
        v.stm.mode = "manual"
        self._commit_change()

    def open_optimizer(self) -> None:
        dlg = OptimizerDialog(copy.deepcopy(self._variant()), self)
        dlg.applyVariant.connect(lambda v: self._add_variant(copy.deepcopy(v)))
        dlg.exec()

    def show_schedule(self) -> None:
        if self._ensure_result():
            schedule_dialog(self, self.result).exec()

    def open_settings(self) -> None:
        cur = {"force": DISPLAY.force, "length": DISPLAY.length, "stress": DISPLAY.stress, "moment": DISPLAY.moment,
               "autosave_min": self.settings.value("autosave_min", 3), "scale": self.settings.value("scale", 1.0),
               "lang": self.settings.value("lang", "pl")}
        dlg = SettingsDialog(cur, self)
        if not dlg.exec():
            return
        vals = dlg.values()
        for k in ("force", "length", "stress", "moment"):
            setattr(DISPLAY, k, vals[k])
            self.settings.setValue(f"unit_{k}", vals[k])
        self.settings.setValue("autosave_min", vals["autosave_min"])
        self._apply_autosave_interval()
        if abs(float(vals["scale"]) - float(cur["scale"])) > 1e-6:
            self.settings.setValue("scale", vals["scale"])
            apply_theme(QApplication.instance(), self.theme, float(vals["scale"]))
            self.canvas.text_scale = float(vals["scale"])
        if vals["lang"] != cur["lang"]:
            self.settings.setValue("lang", vals["lang"])
            QMessageBox.information(self, APP_NAME, "Zmiana języka zostanie zastosowana po ponownym uruchomieniu.")
        self.inputs.refresh_units()
        if self.result:
            self.results.show_result(self.result)
            self.checks.show_result(self.result)
        self.refresh_view()
        self._update_status()

    # ------------------------------------------------------------------
    def closeEvent(self, e):  # noqa: N802
        if not self._confirm_discard():
            e.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("state", self.saveState())
        super().closeEvent(e)
