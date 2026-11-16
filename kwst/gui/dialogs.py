"""Okna dialogowe: pomoc, model i ograniczenia, status walidacji, o programie, zestawienie stali,
optymalizacja, biblioteka, podgląd wydruku, ustawienia, dane projektu."""
from __future__ import annotations

import os
import tempfile

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPainter, QPageLayout
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget, QFileDialog)

from ..design_optimizer import OBJECTIVES, OptSettings, optimize
from ..material_engine import CONCRETE_CLASSES
from ..normative_parameters import EDITIONS
from ..validation_engine import MODULE_STATUS
from ..version import APP_NAME, __version__
from .help_texts import HELP
from .i18n import tr


def _table_dialog(parent, title: str, headers: list[str], rows: list[list], size=(900, 520), extra: str = ""):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    if extra:
        lab = QLabel(extra)
        lab.setWordWrap(True)
        lay.addWidget(lab)
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            it = QTableWidgetItem(str(val))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            t.setItem(r, c, it)
    t.resizeColumnsToContents()
    t.horizontalHeader().setStretchLastSection(True)
    lay.addWidget(t)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)
    dlg.resize(*size)
    return dlg


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Pomoc — parametry"))
        lay = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Szukaj parametru…"))
        lay.addWidget(self.search)
        self.list = QListWidget()
        self.view = QTextBrowser()
        h = QHBoxLayout()
        h.addWidget(self.list, 1)
        h.addWidget(self.view, 2)
        lay.addLayout(h)
        for k in sorted(HELP):
            self.list.addItem(k)
        self.list.currentTextChanged.connect(lambda k: self.view.setHtml(f"<h3>{k}</h3><p>{HELP.get(k, '')}</p>"))
        self.search.textChanged.connect(self._filter)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(860, 520)

    def _filter(self, txt: str):
        t = txt.lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(t not in it.text().lower() and t not in HELP.get(it.text(), "").lower())


MODEL_INFO = """
<h2>Model obliczeniowy</h2>
<p><b>Podstawa:</b> PN-EN 1992-1-1 (EN 1992-1-1:2004 + AC:2010) z polskim Załącznikiem Krajowym — §5.6.4, §6.5
(krzyżulce 6.5.2, cięgna 6.5.3, węzły 6.5.4), zał. J.3 (krótkie wsporniki), rozdz. 8 (zakotwienia, gięcie), §4.4.1
(otulina), §6.2.2 (V<sub>Rd,c</sub>, warunek (6.5)), §6.7 (docisk), §7.3.3 (rysy — uproszczenie), §10.9.5 (oparcia
prefabrykatów).</p>
<h3>Model STM wspornika (rys. J.5)</h3>
<ul>
<li>Węzeł A (CCT) — przecięcie linii działania wypadkowej (V, H, M) z osią cięgna: ξ<sub>A</sub> = a<sub>c</sub> + M/V +
H·a<sub>H</sub>/V. Zapewnia to dokładnie równowagę F<sub>td</sub> = F<sub>Ed</sub>·a<sub>c</sub>/z<sub>0</sub> +
H<sub>Ed</sub>·(a<sub>H</sub>+z<sub>0</sub>)/z<sub>0</sub>.</li>
<li>Węzeł B (CCC) — hydrostatyczna strefa ściskana o wysokości x<sub>c</sub> przy licu; z<sub>0</sub> = d − x<sub>c</sub>/2.</li>
<li>x<sub>c</sub> jest parametrem swobodnym pola naprężeń (twierdzenie o dolnej ocenie). Program dobiera go jawnie
(optymalnie, z warunku naprężenia lub wartość użytkownika) z ograniczeniami 1,0 ≤ tan θ ≤ 2,5 (J.3(1)), mieszczenia się
węzłów oraz nośności cięgna, zakotwień i gięcia.</li>
<li>Rozwiązanie zamknięte jest w każdym obliczeniu weryfikowane niezależnym solverem macierzowym (rząd macierzy
równowagi, residua węzłowe, równowaga globalna).</li>
</ul>
<h3>Zakres stosowania</h3>
<ul>
<li>a<sub>c</sub> &lt; z<sub>0</sub> oraz 1,0 ≤ tan θ ≤ 2,5 — w przeciwnym razie wynik „MODEL POZA ZAKRESEM STOSOWANIA”,
z zaleceniem metody alternatywnej (belka wspornikowa 6.1/6.2, analiza nieliniowa / MES) — NIE wykonywanej przez program.</li>
<li>Wspornik o zmiennej wysokości / ukośnej dolnej krawędzi — kontrola, czy pole naprężeń (krzyżulec, węzły) mieści się
w obrysie betonu.</li>
<li>Wsporniki dwustronne — cięgno ciągłe przez słup; różnica sił przekazywana przyczepnością (sprawdzane).</li>
<li>Prefabrykowane — dodatkowo §10.9.5 (wartości tablicowe wymagają potwierdzenia), siły od więzów.</li>
<li>Model ręczny — dowolna kratownica płaska; kontrola stateczności (rząd macierzy) blokuje wynik dla mechanizmów.</li>
</ul>
<h3>Rozróżnienie podstaw sprawdzeń</h3>
<p><b>normatywne</b> — wymagania EN 1992-1-1; <b>informacyjne</b> — zał. J (status w PL do potwierdzenia z NA);
<b>zalecenie inżynierskie</b> — niewymagane przez EC2, niespełnienie daje status „wymaga osobnej weryfikacji”;
<b>kontrola modelu</b> — spójność i poprawność numeryczna.</p>
"""


def model_info_dialog(parent, result) -> QDialog:
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("Model obliczeniowy i ograniczenia"))
    lay = QVBoxLayout(dlg)
    tb = QTextBrowser()
    html = MODEL_INFO
    if result is not None:
        html += "<h3>Założenia bieżącej analizy</h3><ul>" + "".join(f"<li>{a}</li>" for a in result.assumptions) + "</ul>"
        html += "<h3>Ograniczenia</h3><ul>" + "".join(f"<li>{a}</li>" for a in result.limitations) + "</ul>"
    tb.setHtml(html)
    lay.addWidget(tb)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)
    dlg.resize(900, 640)
    return dlg


def module_status_dialog(parent) -> QDialog:
    rows = [[k, s, d] for k, (s, d) in MODULE_STATUS.items()]
    eds = "; ".join(f"{e.id}: {'zaimplementowana' if e.implemented else 'NIEZAIMPLEMENTOWANA'}" for e in EDITIONS.values())
    return _table_dialog(parent, tr("Status walidacji modułów"), ["Moduł", "Status", "Opis weryfikacji"], rows,
                         extra=f"Edycje normy: {eds}. Klasyfikacja: zweryfikowany / częściowo zweryfikowany / "
                               "nieweryfikowany.")


def about_dialog(parent) -> None:
    QMessageBox.about(parent, tr("O programie"),
                      f"<h3>{APP_NAME} {__version__}</h3><p>Projektowanie i sprawdzanie krótkich wsporników "
                      "żelbetowych metodą Strut-and-Tie wg PN-EN 1992-1-1 (zał. J.3).</p>"
                      "<p>Obliczenia deterministyczne, jawne i audytowalne. Wyniki wymagają weryfikacji przez "
                      "uprawnionego projektanta.</p><p>Fonty: DejaVu (licencja Bitstream Vera).</p>")


def schedule_dialog(parent, result) -> QDialog:
    rows = []
    tot = {}
    for b in result.schedule:
        rows.append([b.mark, b.description, b.shape, f"{b.phi:.0f}", b.count, f"{b.length / 1000:.3f}",
                     f"{b.total_length / 1000:.3f}", f"{b.mass:.2f}"])
        tot[b.phi] = tot.get(b.phi, 0) + b.mass
    rows.append(["", "RAZEM", "", "", "", "", "", f"{sum(tot.values()):.2f}"])
    extra = ("Masa wg średnic: " + ", ".join(f"φ{k:.0f}: {v:.2f} kg" for k, v in sorted(tot.items())) +
             ". Długości osiowe orientacyjne (bez naddatków na zakłady/haki) — do weryfikacji wykonawczej.")
    return _table_dialog(parent, tr("Zestawienie stali"), ["Poz.", "Opis", "Kształt", "φ [mm]", "Szt.",
                                                           "Dł. 1 szt. [m]", "Dł. całk. [m]", "Masa [kg]"], rows,
                         extra=extra)


class _OptWorker(QThread):
    progress = Signal(int, int)
    done = Signal(list)

    def __init__(self, base, settings):
        super().__init__()
        self.base, self.settings = base, settings
        self._cancel = False

    def run(self):
        res = optimize(self.base, self.settings, lambda a, b: self.progress.emit(a, b), lambda: self._cancel)
        self.done.emit(res)

    def cancel(self):
        self._cancel = True


class OptimizerDialog(QDialog):
    applyVariant = Signal(object)

    def __init__(self, base_variant, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Optymalizacja wspornika"))
        self.base = base_variant
        lay = QVBoxLayout(self)
        g = QGroupBox(tr("Cel i zmienne optymalizacji"))
        f = QFormLayout(g)
        self.obj = QComboBox()
        for k, v in OBJECTIVES.items():
            self.obj.addItem(v, k)
        f.addRow(tr("Cel"), self.obj)
        r = base_variant.geometry.right

        def rng(lo, hi, st):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            sbs = []
            for val in (lo, hi, st):
                sb = QDoubleSpinBox()
                sb.setRange(0, 10000)
                sb.setDecimals(0)
                sb.setValue(val)
                sb.setSuffix(" mm")
                h.addWidget(sb)
                sbs.append(sb)
            cb = QCheckBox(tr("zmienna"))
            h.addWidget(cb)
            return w, sbs, cb
        w1, self.hc, self.hc_on = rng(max(200, r.h_c - 150), r.h_c + 250, 50)
        self.hc_on.setChecked(True)
        f.addRow("h_c (min / max / krok)", w1)
        w2, self.lc, self.lc_on = rng(max(r.a_c + r.plate.length / 2 + 40, r.l_c - 100), r.l_c + 200, 50)
        f.addRow("l_c (min / max / krok)", w2)
        w3, self.bb, self.b_on = rng(max(200, base_variant.geometry.b - 100), base_variant.geometry.b + 100, 50)
        f.addRow("b (min / max / krok)", w3)
        cw = QWidget()
        ch = QHBoxLayout(cw)
        ch.setContentsMargins(0, 0, 0, 0)
        self.cls = {}
        for c in CONCRETE_CLASSES[2:9]:
            cb = QCheckBox(c)
            cb.setChecked(c in ("C25/30", "C30/37", "C35/45", "C40/50"))
            ch.addWidget(cb)
            self.cls[c] = cb
        f.addRow(tr("Klasy betonu"), cw)
        dw = QWidget()
        dh = QHBoxLayout(dw)
        dh.setContentsMargins(0, 0, 0, 0)
        self.dia = {}
        for d in (12.0, 14.0, 16.0, 20.0, 25.0, 28.0, 32.0):
            cb = QCheckBox(f"φ{d:.0f}")
            cb.setChecked(d <= 25)
            dh.addWidget(cb)
            self.dia[d] = cb
        f.addRow(tr("Średnice prętów głównych"), dw)
        self.steel_price = QDoubleSpinBox()
        self.steel_price.setRange(0, 100)
        self.steel_price.setValue(5.5)
        self.steel_price.setSuffix(" zł/kg")
        f.addRow(tr("Cena stali"), self.steel_price)
        self.conc_price = QDoubleSpinBox()
        self.conc_price.setRange(0, 5000)
        self.conc_price.setValue(0)
        self.conc_price.setSuffix(" zł/m³ (0 = cennik domyślny wg klas)")
        f.addRow(tr("Cena betonu"), self.conc_price)
        lay.addWidget(g)
        hb = QHBoxLayout()
        self.run_btn = QPushButton(tr("Uruchom optymalizację"))
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn = QPushButton(tr("Przerwij"))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        self.prog = QProgressBar()
        hb.addWidget(self.run_btn)
        hb.addWidget(self.cancel_btn)
        hb.addWidget(self.prog, 1)
        lay.addLayout(hb)
        self.tbl = QTableWidget(0, 12)
        self.tbl.setHorizontalHeaderLabels(["OK", "h_c", "h_e", "l_c", "b", "Beton", "Zbrojenie główne", "Stal [kg]",
                                            "Beton [m³]", "Koszt [zł]", "η_max", "Uwagi"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.tbl, 1)
        bb = QHBoxLayout()
        self.apply_btn = QPushButton(tr("Zastosuj wybrany wariant (nowy wariant projektu)"))
        self.apply_btn.clicked.connect(self._apply)
        close = QPushButton(tr("Zamknij"))
        close.clicked.connect(self.reject)
        bb.addWidget(self.apply_btn)
        bb.addStretch(1)
        bb.addWidget(close)
        lay.addLayout(bb)
        self.results = []
        self.worker = None
        self.resize(1150, 700)

    def settings(self) -> OptSettings:
        s = OptSettings(objective=self.obj.currentData())
        if self.hc_on.isChecked():
            s.h_c = tuple(x.value() for x in self.hc)
        if self.lc_on.isChecked():
            s.l_c = tuple(x.value() for x in self.lc)
        if self.b_on.isChecked():
            s.b = tuple(x.value() for x in self.bb)
        s.concretes = [c for c, cb in self.cls.items() if cb.isChecked()]
        s.diameters = [d for d, cb in self.dia.items() if cb.isChecked()]
        s.steel_price = self.steel_price.value()
        if self.conc_price.value() > 0:
            s.concrete_price = {c: self.conc_price.value() for c in CONCRETE_CLASSES}
        return s

    def _run(self):
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker = _OptWorker(self.base, self.settings())
        self.worker.progress.connect(lambda a, b: (self.prog.setMaximum(b), self.prog.setValue(a)))
        self.worker.done.connect(self._done)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()

    def _done(self, res):
        self.results = res
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.tbl.setRowCount(len(res))
        for r, o in enumerate(res):
            vals = ["TAK" if o.feasible else "NIE", f"{o.h_c:.0f}", f"{o.h_e:.0f}", f"{o.l_c:.0f}", f"{o.b:.0f}",
                    o.concrete, o.main, f"{o.steel_kg:.1f}", f"{o.concrete_m3:.3f}", f"{o.cost:.0f}",
                    f"{o.eta_max:.3f}", o.reason]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if not o.feasible:
                    it.setForeground(Qt.gray)
                self.tbl.setItem(r, c, it)
        self.tbl.resizeColumnsToContents()

    def _apply(self):
        r = self.tbl.currentRow()
        if 0 <= r < len(self.results):
            o = self.results[r]
            if not o.feasible:
                QMessageBox.warning(self, APP_NAME, tr("Wariant niedopuszczalny — nie spełnia wszystkich kryteriów."))
                return
            self.applyVariant.emit(o.variant)
            self.accept()

    def closeEvent(self, e):  # noqa: N802
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(5000)
        super().closeEvent(e)


class LibraryDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Biblioteka typowych wsporników"))
        self.items = items
        lay = QHBoxLayout(self)
        self.list = QListWidget()
        for it in items:
            self.list.addItem(it.title)
        self.view = QTextBrowser()
        lay.addWidget(self.list, 1)
        right = QVBoxLayout()
        right.addWidget(self.view, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Wstaw jako nowy wariant"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        lay.addLayout(right, 2)
        self.list.currentRowChanged.connect(self._show)
        if items:
            self.list.setCurrentRow(0)
        self.resize(820, 420)

    def _show(self, i):
        if 0 <= i < len(self.items):
            it = self.items[i]
            g = it.variant.geometry
            self.view.setHtml(f"<h3>{it.title}</h3><p>{it.description}</p><p>b = {g.b:.0f} mm, l_c = {g.right.l_c:.0f} mm, "
                              f"h_c = {g.right.h_c:.0f} mm, h_e = {g.right.h_e:.0f} mm, a_c = {g.right.a_c:.0f} mm; "
                              f"beton {it.variant.materials.concrete}; układ {g.layout.value}, {g.construction.value}.</p>")

    def selected(self):
        i = self.list.currentRow()
        return self.items[i] if 0 <= i < len(self.items) else None


class PrintPreviewDialog(QDialog):
    """Podgląd wydruku raportu PDF z możliwością druku i zapisu."""

    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
        self.setWindowTitle(tr("Podgląd wydruku"))
        self.pdf_path = pdf_path
        lay = QVBoxLayout(self)
        self.doc = QPdfDocument(self)
        self.doc.load(pdf_path)
        self.view = QPdfView(self)
        self.view.setDocument(self.doc)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        lay.addWidget(self.view, 1)
        hb = QHBoxLayout()
        pr = QPushButton(tr("Drukuj…"))
        pr.clicked.connect(self._print)
        sv = QPushButton(tr("Zapisz PDF…"))
        sv.clicked.connect(self._save)
        cl = QPushButton(tr("Zamknij"))
        cl.clicked.connect(self.reject)
        hb.addWidget(QLabel(f"{self.doc.pageCount()} str."))
        hb.addStretch(1)
        hb.addWidget(pr)
        hb.addWidget(sv)
        hb.addWidget(cl)
        lay.addLayout(hb)
        self.resize(900, 1000)

    def _print(self):
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.Accepted:
            return
        painter = QPainter(printer)
        try:
            for i in range(self.doc.pageCount()):
                if i:
                    printer.newPage()
                rect = printer.pageLayout().paintRectPixels(printer.resolution())
                img = self.doc.render(i, QSize(rect.width(), rect.height()))
                painter.drawImage(0, 0, img)
        finally:
            painter.end()

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("Zapisz PDF"), "raport.pdf", "PDF (*.pdf)")
        if path:
            import shutil
            shutil.copyfile(self.pdf_path, path)


class ProjectInfoDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Dane projektu"))
        self.info = info
        f = QFormLayout(self)
        self.edits = {}
        for key, lab in (("name", "Nazwa projektu"), ("number", "Numer"), ("object", "Obiekt"), ("element", "Element"),
                         ("designer", "Projektant"), ("checker", "Sprawdzający")):
            e = QLineEdit(getattr(info, key))
            f.addRow(tr(lab), e)
            self.edits[key] = e
        self.notes = QPlainTextEdit(info.notes)
        f.addRow(tr("Uwagi"), self.notes)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.resize(520, 360)

    def apply(self):
        for k, e in self.edits.items():
            setattr(self.info, k, e.text())
        self.info.notes = self.notes.toPlainText()


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Ustawienia"))
        f = QFormLayout(self)
        self.force = QComboBox()
        for u in ("kN", "N", "MN"):
            self.force.addItem(u)
        self.force.setCurrentText(settings.get("force", "kN"))
        self.length = QComboBox()
        for u in ("mm", "cm", "m"):
            self.length.addItem(u)
        self.length.setCurrentText(settings.get("length", "mm"))
        self.stress = QComboBox()
        for u in ("MPa", "kN/cm²"):
            self.stress.addItem(u)
        self.stress.setCurrentText(settings.get("stress", "MPa"))
        self.moment = QComboBox()
        for u in ("kN·m", "N·mm", "kN·cm"):
            self.moment.addItem(u)
        self.moment.setCurrentText(settings.get("moment", "kN·m"))
        self.autosave = QSpinBox()
        self.autosave.setRange(0, 120)
        self.autosave.setSuffix(" min (0 = wył.)")
        self.autosave.setValue(int(settings.get("autosave_min", 3)))
        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.7, 2.5)
        self.scale.setSingleStep(0.1)
        self.scale.setValue(float(settings.get("scale", 1.0)))
        self.lang = QComboBox()
        self.lang.addItem("Polski", "pl")
        self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(1 if settings.get("lang") == "en" else 0)
        f.addRow(tr("Jednostka siły"), self.force)
        f.addRow(tr("Jednostka długości"), self.length)
        f.addRow(tr("Jednostka naprężeń"), self.stress)
        f.addRow(tr("Jednostka momentu"), self.moment)
        f.addRow(tr("Autozapis co"), self.autosave)
        f.addRow(tr("Skala interfejsu"), self.scale)
        f.addRow(tr("Język (po ponownym uruchomieniu)"), self.lang)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self) -> dict:
        return {"force": self.force.currentText(), "length": self.length.currentText(),
                "stress": self.stress.currentText(), "moment": self.moment.currentText(),
                "autosave_min": self.autosave.value(), "scale": self.scale.value(), "lang": self.lang.currentData()}
