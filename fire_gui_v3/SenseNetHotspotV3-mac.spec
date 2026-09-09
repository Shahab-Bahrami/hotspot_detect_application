# macOS build specification for SenseNet Hotspot Intelligence Version 3.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project = Path(SPECPATH).resolve().parents[1]
gui = project / "apps" / "fire_gui_v3"

datas = [
    (str(gui / "templates"), "apps/fire_gui_v3/templates"),
    (str(gui / "static"), "apps/fire_gui_v3/static"),
    (str(gui / "data"), "apps/fire_gui_v3/data"),
    (str(gui / "models"), "apps/fire_gui_v3/models"),
    (str(project / "data" / "hotspot" / "hotspot_master_2013_2023_2025_2026.xlsx"), "data/hotspot"),
]

a = Analysis(
    [str(gui / "app.py")],
    pathex=[str(gui), str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=(
        collect_submodules("sklearn")
        + collect_submodules("openpyxl")
        + collect_submodules("scipy._external.array_api_compat")
    ),
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["tensorflow", "torch", "matplotlib", "notebook", "IPython"],
    noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="SenseNetHotspotV3", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
app_bundle = BUNDLE(
    exe,
    name="SenseNetHotspotV3.app",
    icon=None,
    bundle_identifier="ai.sensenet.hotspot.v3",
)
