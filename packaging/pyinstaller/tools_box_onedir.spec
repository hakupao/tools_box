# -*- mode: python ; coding: utf-8 -*-
# DataForge Studio v3 onedir build. Run via packaging/scripts/build_onedir.ps1.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
APP_ICON = PROJECT_ROOT / "assets" / "icons" / "favicon.ico"

block_cipher = None

# Pages are loaded lazily via importlib ("module:Class" in the registry), and the EDC
# automation libraries are imported inside functions, so declare them explicitly.
hidden_imports = (
    collect_submodules("dataforge")
    + collect_submodules("keyboard")
    + collect_submodules("mouse")
    + [
        "pythoncom",
        "pywintypes",
        "win32com.client",
        "win32gui",
        "win32process",
        "win32api",
        "win32con",
    ]
)


a = Analysis(
    [str(SRC_DIR / "dataforge" / "__main__.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[(str(APP_ICON), "assets/icons")],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "PySide2",
        "IPython",
        "jedi",
        "matplotlib",
        "numpy.distutils",
        "PIL.ImageTk",
        "scipy",
        "sympy",
        "tornado",
        "zmq",
        "docutils",
        "pytest",
        "tkinter",
        "pandas",
        "numpy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=2,
)


def filter_binaries(binaries):
    excluded_patterns = [
        "api-ms-win-",
        "ucrtbase.dll",
        "msvcp140.dll",
        "vcruntime140.dll",
    ]
    filtered = []
    for binary in binaries:
        include = True
        for pattern in excluded_patterns:
            if pattern in binary[0].lower():
                include = False
                break
        if include:
            filtered.append(binary)
    return filtered


a.binaries = filter_binaries(a.binaries)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DataForgeStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_ICON),
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DataForgeStudio",
)
