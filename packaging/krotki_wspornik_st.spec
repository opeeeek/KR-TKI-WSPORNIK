# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: budowa aplikacji KRÓTKI WSPORNIK ST (Windows: pyinstaller packaging\krotki_wspornik_st.spec)
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(ROOT, "kwst", "resources", "fonts"), os.path.join("kwst", "resources", "fonts")),
    (os.path.join(ROOT, "kwst", "resources", "library"), os.path.join("kwst", "resources", "library")),
    (os.path.join(ROOT, "kwst", "resources", "icon.png"), os.path.join("kwst", "resources")),
]

hiddenimports = [
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtPrintSupport",
    "reportlab.graphics.barcode", "openpyxl", "ezdxf",
]

excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.Qt3DCore",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "tkinter", "matplotlib", "IPython", "pytest", "lxml", "scipy", "pandas",
]

a = Analysis(
    [os.path.join(ROOT, "run_kwst.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)
icon = os.path.join(SPECPATH, "icon.ico")
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KrotkiWspornikST",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon if os.path.exists(icon) else None,
    version=os.path.join(SPECPATH, "version_info.txt") if os.name == "nt" else None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="KrotkiWspornikST")
