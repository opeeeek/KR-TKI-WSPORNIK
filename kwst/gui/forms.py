"""Generyczne formularze powiązane z modelem danych (ścieżki atrybutów) z konwersją jednostek."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit,
                               QSpinBox, QWidget, QLabel)

from ..core.units import DISPLAY, Kind, UNITS, from_base, to_base
from .help_texts import help_for
from .i18n import tr


def get_path(obj: Any, path: str) -> Any:
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else getattr(obj, part)
    return obj


def set_path(obj: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj[int(part)] if isinstance(obj, list) else getattr(obj, part)
    last = parts[-1]
    if isinstance(obj, list):
        obj[int(last)] = value
    else:
        setattr(obj, last, value)


@dataclass
class Field:
    path: str
    label: str
    kind: str = "float"            # float | optfloat | int | bool | choice | text
    unit: Kind | None = None       # rodzaj wielkości (konwersja jednostek)
    lo: float = 0.0
    hi: float = 1e9
    decimals: int | None = None
    choices: list[tuple[Any, str]] = field(default_factory=list)
    help: str = ""
    step: float | None = None
    enabled_if: Callable[[Any], bool] | None = None


class _NoWheelDouble(QDoubleSpinBox):
    """Spinbox niereagujący na kółko myszy bez fokusu (ochrona przed przypadkową zmianą danych)."""

    def wheelEvent(self, e):  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class _NoWheelInt(QSpinBox):
    def wheelEvent(self, e):  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class _NoWheelCombo(QComboBox):
    def wheelEvent(self, e):  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class FormBinder(QObject):
    """Wiąże listę pól z obiektem danych (``root_getter`` zwraca bieżący wariant)."""

    changed = Signal(str)

    def __init__(self, root_getter: Callable[[], Any], parent=None):
        super().__init__(parent)
        self.root_getter = root_getter
        self.items: list[tuple[Field, QWidget, Any]] = []
        self._loading = False

    # --- budowa ---------------------------------------------------------------
    def add_to(self, form: QFormLayout, f: Field) -> QWidget:
        w, extra = self._make(f)
        lab = QLabel(tr(f.label))
        lab.setWordWrap(True)
        lab.setMinimumWidth(120)
        tip = f.help or help_for(f.path)
        if tip:
            lab.setToolTip(tip)
            w.setToolTip(tip)
        form.addRow(lab, w)
        self.items.append((f, w, extra))
        return w

    def _unit(self, f: Field) -> str:
        return DISPLAY.unit_for(f.unit) if f.unit is not None else ""

    def _decimals(self, f: Field) -> int:
        if f.decimals is not None:
            return f.decimals
        u = self._unit(f)
        if f.unit == Kind.LENGTH:
            return {"mm": 1, "cm": 2, "m": 4}.get(u, 2)
        if f.unit == Kind.FORCE:
            return {"N": 0, "kN": 2, "MN": 5}.get(u, 2)
        if f.unit == Kind.MOMENT:
            return 3
        return 3

    def _spin(self, f: Field) -> QDoubleSpinBox:
        sb = _NoWheelDouble()
        sb.setFocusPolicy(Qt.StrongFocus)
        sb.setKeyboardTracking(False)
        self._configure_spin(sb, f)
        sb.valueChanged.connect(lambda _v, f=f: self._commit(f))
        return sb

    def _configure_spin(self, sb: QDoubleSpinBox, f: Field) -> None:
        u = self._unit(f)
        lo, hi = f.lo, f.hi
        if f.unit is not None and f.unit in UNITS and u in UNITS[f.unit]:
            lo, hi = from_base(lo, f.unit, u), from_base(hi, f.unit, u)
        sb.blockSignals(True)
        sb.setDecimals(self._decimals(f))
        sb.setRange(lo, hi)
        sb.setSuffix(f" {u}" if u and u != "-" else "")
        if f.step is not None:
            st = from_base(f.step, f.unit, u) if (f.unit is not None and u in UNITS.get(f.unit, {})) else f.step
            sb.setSingleStep(st)
        else:
            sb.setSingleStep(10.0 if (f.unit == Kind.LENGTH and u == "mm") else 1.0)
        sb.blockSignals(False)

    def _make(self, f: Field):
        if f.kind == "float":
            return self._spin(f), None
        if f.kind == "optfloat":
            box = QWidget()
            lay = QHBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox(tr("ręcznie"))
            sb = self._spin(f)
            auto = QLabel("")
            auto.setStyleSheet("color: #888;")
            lay.addWidget(cb)
            lay.addWidget(sb, 1)
            lay.addWidget(auto)
            cb.toggled.connect(lambda on, sb=sb, f=f: (sb.setEnabled(on), self._commit(f)))
            return box, (cb, sb, auto)
        if f.kind == "int":
            sb = _NoWheelInt()
            sb.setFocusPolicy(Qt.StrongFocus)
            sb.setKeyboardTracking(False)
            sb.setRange(int(f.lo), int(min(f.hi, 1e6)))
            sb.valueChanged.connect(lambda _v, f=f: self._commit(f))
            return sb, None
        if f.kind == "bool":
            cb = QCheckBox()
            cb.toggled.connect(lambda _v, f=f: self._commit(f))
            return cb, None
        if f.kind == "choice":
            cb = _NoWheelCombo()
            cb.setFocusPolicy(Qt.StrongFocus)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(14)
            for val, lab in f.choices:
                cb.addItem(tr(lab), val)
            cb.currentIndexChanged.connect(lambda _i, f=f: self._commit(f))
            return cb, None
        le = QLineEdit()
        le.editingFinished.connect(lambda f=f: self._commit(f))
        return le, None

    # --- synchronizacja --------------------------------------------------------
    def _to_display(self, f: Field, v: float) -> float:
        u = self._unit(f)
        if f.unit is not None and u in UNITS.get(f.unit, {}):
            return from_base(v, f.unit, u)
        return v

    def _to_base(self, f: Field, v: float) -> float:
        u = self._unit(f)
        if f.unit is not None and u in UNITS.get(f.unit, {}):
            return to_base(v, f.unit, u)
        return v

    def load(self) -> None:
        root = self.root_getter()
        self._loading = True
        try:
            for f, w, extra in self.items:
                try:
                    val = get_path(root, f.path)
                except (AttributeError, IndexError, KeyError):
                    continue
                if f.kind == "float":
                    w.blockSignals(True)
                    w.setValue(self._to_display(f, float(val)))
                    w.blockSignals(False)
                elif f.kind == "optfloat":
                    cb, sb, _ = extra
                    cb.blockSignals(True)
                    sb.blockSignals(True)
                    cb.setChecked(val is not None)
                    sb.setEnabled(val is not None)
                    if val is not None:
                        sb.setValue(self._to_display(f, float(val)))
                    cb.blockSignals(False)
                    sb.blockSignals(False)
                elif f.kind == "int":
                    w.blockSignals(True)
                    w.setValue(int(val))
                    w.blockSignals(False)
                elif f.kind == "bool":
                    w.blockSignals(True)
                    w.setChecked(bool(val))
                    w.blockSignals(False)
                elif f.kind == "choice":
                    w.blockSignals(True)
                    key = val.value if hasattr(val, "value") else val
                    idx = next((i for i in range(w.count()) if (w.itemData(i).value if hasattr(w.itemData(i), "value")
                                                                 else w.itemData(i)) == key), -1)
                    if idx >= 0:
                        w.setCurrentIndex(idx)
                    w.blockSignals(False)
                else:
                    w.blockSignals(True)
                    w.setText(str(val))
                    w.blockSignals(False)
            self.update_enabled()
        finally:
            self._loading = False

    def update_enabled(self) -> None:
        root = self.root_getter()
        for f, w, _ in self.items:
            if f.enabled_if is not None:
                try:
                    w.setEnabled(bool(f.enabled_if(root)))
                except Exception:  # noqa: BLE001
                    pass

    def refresh_units(self) -> None:
        for f, w, extra in self.items:
            if f.kind == "float":
                self._configure_spin(w, f)
            elif f.kind == "optfloat":
                self._configure_spin(extra[1], f)
        self.load()

    def set_auto_hint(self, path: str, text: str) -> None:
        for f, w, extra in self.items:
            if f.path == path and f.kind == "optfloat":
                extra[2].setText(text)

    def _commit(self, f: Field) -> None:
        if self._loading:
            return
        root = self.root_getter()
        w, extra = next((w, e) for ff, w, e in self.items if ff is f)
        if f.kind == "float":
            val = self._to_base(f, w.value())
        elif f.kind == "optfloat":
            cb, sb, _ = extra
            val = self._to_base(f, sb.value()) if cb.isChecked() else None
        elif f.kind == "int":
            val = int(w.value())
        elif f.kind == "bool":
            val = bool(w.isChecked())
        elif f.kind == "choice":
            val = w.currentData()
        else:
            val = w.text()
        try:
            cur = get_path(root, f.path)
            if hasattr(cur, "value") and not hasattr(val, "value"):
                val = type(cur)(val)
            set_path(root, f.path, val)
        except (AttributeError, ValueError, TypeError):
            return
        self.update_enabled()
        self.changed.emit(f.path)
