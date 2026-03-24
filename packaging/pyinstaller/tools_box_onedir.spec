# -*- mode: python ; coding: utf-8 -*-
import platform
import shutil
from pathlib import Path

import tkinterdnd2


PROJECT_ROOT = Path.cwd()
TEMP_TKDND_DIR = PROJECT_ROOT / "temp_tkdnd" / "tkdnd"
APP_ICON = PROJECT_ROOT / "assets" / "icons" / "favicon.ico"


def get_platform_dirs():
    if platform.system() == "Windows":
        arch = platform.architecture()[0]
        machine = platform.machine().lower()
        is_64 = "64" in arch or machine.endswith("64")
        return [
            "win-x64" if is_64 else "win-x86",
            "win64" if is_64 else "win32",
            "windows-x64" if is_64 else "windows-x86",
        ]
    return [platform.system().lower()]


def setup_tkdnd_files():
    possible_platform_dirs = set(get_platform_dirs())
    tkdnd_source = Path(tkinterdnd2.__file__).parent / "tkdnd"

    if TEMP_TKDND_DIR.exists():
        shutil.rmtree(TEMP_TKDND_DIR)
    TEMP_TKDND_DIR.mkdir(parents=True, exist_ok=True)

    print(f"正在查找 tkdnd 源目录: {tkdnd_source}")
    if not tkdnd_source.exists():
        print(f"警告: tkdnd 源目录不存在: {tkdnd_source}")
        return

    for item in tkdnd_source.glob("*"):
        if item.is_file():
            shutil.copy2(item, TEMP_TKDND_DIR)
            continue

        if item.name in possible_platform_dirs:
            print(f"找到平台目录: {item.name}")
            for platform_file in item.glob("*"):
                if platform_file.is_file():
                    shutil.copy2(platform_file, TEMP_TKDND_DIR)
            continue

        shutil.copytree(item, TEMP_TKDND_DIR / item.name, dirs_exist_ok=True)


def collect_data_files():
    return [
        (str(TEMP_TKDND_DIR), "tkdnd"),
    ]


setup_tkdnd_files()
block_cipher = None


a = Analysis(
    [str(PROJECT_ROOT / "src/main.py")],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=collect_data_files(),
    hiddenimports=[
        "tkinter",
        "tkinterdnd2",
        "tkinterdnd2.TkinterDnD",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "qfluentwidgets",
        "pandas",
        "numpy",
        "openpyxl",
        "pyautogui",
        "pygetwindow",
        "pygetwindow._pygetwindow_win",
        "pywintypes",
        "pythoncom",
        "win32api",
        "win32con",
        "win32com",
        "win32com.client",
        "win32gui",
        "mouse",
        "mouse._winmouse",
        "keyboard",
        "requests",
        "bs4",
        "json",
        "pathlib",
        "shutil",
        "backports.tarfile",
        "pkg_resources",
        "jaraco.text",
        "platformdirs",
        # 懒加载页面模块（importlib 动态导入，需显式声明）
        "src.gui.widgets.date_converter_page",
        "src.gui.widgets.file_format_converter_page",
        "src.gui.widgets.spec_workflow_page",
        "src.gui.widgets.file_field_extractor_page",
        "src.gui.widgets.dead_link_checker_page",
        "src.gui.widgets.data_masking_page",
        "src.gui.widgets.edc_site_adder_page",
        "src.gui.widgets.fullwidth_halfwidth_converter_page",
        "src.gui.widgets.xlsx_sheet_splitter_page",
    ],
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
        "unittest",
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
