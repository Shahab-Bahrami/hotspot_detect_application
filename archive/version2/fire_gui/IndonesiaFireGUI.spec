# Build from the project root with: pyinstaller apps\fire_gui\IndonesiaFireGUI.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project = Path(SPECPATH).resolve().parents[1]
gui = project / "apps" / "fire_gui"

tf_datas, tf_binaries, tf_hiddenimports = collect_all("tensorflow")

datas = tf_datas + [
    (str(gui / "templates"), "apps/fire_gui/templates"),
    (str(gui / "static"), "apps/fire_gui/static"),
    (str(gui / "data"), "apps/fire_gui/data"),
    (str(gui / "models"), "apps/fire_gui/models"),
    (str(project / "data" / "hotspot" / "hotspot_master_2013_2023_2025_2026.xlsx"), "data/hotspot"),
]

a = Analysis(
    [str(gui / "app.py")],
    pathex=[str(gui), str(project)],
    binaries=tf_binaries,
    datas=datas,
    hiddenimports=tf_hiddenimports + collect_submodules("sklearn") + collect_submodules("openpyxl"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "notebook", "IPython"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="IndonesiaFireGUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
