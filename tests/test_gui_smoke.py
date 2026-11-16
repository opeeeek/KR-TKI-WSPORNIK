"""Test dymny GUI (Qt offscreen) — wymaga PySide6 i bibliotek systemowych Qt."""
import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QFileDialog, QMessageBox  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from kwst.gui.app import create_app
    return create_app([])


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    from kwst.gui.main_window import MainWindow
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: pytest.fail(f"critical dialog: {a[2] if len(a) > 2 else a}"))
    s = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    w = MainWindow(settings=s)
    w.resize(1400, 900)
    w.show()
    app.processEvents()
    yield w
    w.dirty = False
    w.close()


def test_window_calculates_and_draws(win):
    assert win.result is not None
    assert win.result.verdict is not None
    assert win.canvas.scene_data is not None and not win.canvas.scene_data.stale
    for mode in ("geometry", "stm", "stress", "rebar"):
        win.set_view(mode)
        assert len(win.canvas.scene().items()) > 10


def test_input_change_recalculates(win, app):
    v = win._variant()
    old = win.result.fingerprint
    v.geometry.right.h_c = 650.0
    win._commit_change()
    assert win._is_fresh()
    assert win.result.fingerprint != old
    assert win.result.geometry.sides["R"].h_c == 650.0


def test_handle_drag_and_undo(win):
    v = win._variant()
    a0 = v.geometry.right.a_c
    x_face = v.geometry.column.h_col / 2
    win._on_handle_moved("handle:a_c:R", x_face + a0 - 40.0, 0.0)
    assert win._variant().geometry.right.a_c == pytest.approx(a0 - 40.0)
    assert win.result.geometry.sides["R"].a_c == pytest.approx(a0 - 40.0)    # rysunek = obliczenia
    win.undo()
    assert win._variant().geometry.right.a_c == pytest.approx(a0)
    win.redo()
    assert win._variant().geometry.right.a_c == pytest.approx(a0 - 40.0)


def test_xc_handle_switches_to_user(win):
    sm = win.result.governing_stm.sides["R"]
    win._on_handle_moved("handle:x_c:R", 0.0, sm.state.y_B + 10.0)
    v = win._variant()
    assert v.stm.lever_arm == "user" and v.geometry.right.x_c_user is not None


def test_variants(win):
    n = len(win.project.variants)
    win.duplicate_variant()
    assert len(win.project.variants) == n + 1
    win._switch_variant(0)
    assert win.project.active == 0
    win.project.active = len(win.project.variants) - 1
    win.delete_variant()
    assert len(win.project.variants) == n


def test_exports(win, tmp_path, monkeypatch):
    for ext, fn in ((".pdf", win.export_pdf), (".xlsx", win.export_excel), (".csv", win.export_csv),
                    (".json", win.export_json), (".dxf", win.export_dxf)):
        target = str(tmp_path / f"out{ext}")
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (target, ""))
        fn()
        assert os.path.getsize(target) > 500, ext


def test_save_open_roundtrip(win, tmp_path, monkeypatch):
    target = str(tmp_path / "proj.kwst")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (target, ""))
    assert win.save_project_as()
    fp = win.result.fingerprint
    win.open_project(target)
    assert win.result.fingerprint == fp


def test_apply_rebar_and_manual_copy(win):
    win.apply_designed_rebar()
    assert not win._variant().reinforcement.main.auto
    win._copy_auto_model()
    assert win._variant().stm.mode == "manual"
    assert win.result.model_type.startswith("Model STM zdefiniowany ręcznie")


def test_dialogs_construct(win):
    from kwst.gui.dialogs import OptimizerDialog, HelpDialog, model_info_dialog, module_status_dialog, schedule_dialog
    OptimizerDialog(win._variant(), win).close()
    HelpDialog(win).close()
    model_info_dialog(win, win.result).close()
    module_status_dialog(win).close()
    schedule_dialog(win, win.result).close()


def test_theme_toggle(win):
    win._toggle_theme(True)
    assert win.canvas.theme == "dark"
    win._toggle_theme(False)
