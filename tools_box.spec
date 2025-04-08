# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from pathlib import Path
import tkinterdnd2
import platform

# 获取平台特定的目录名
if platform.system() == 'Windows':
    platform_dir = 'win64' if platform.machine().endswith('64') else 'win32'
else:
    platform_dir = platform.system().lower()

# 准备tkdnd文件
tkdnd_source = Path(tkinterdnd2.__file__).parent / 'tkdnd'
tkdnd_target = Path('temp_tkdnd/tkdnd')

# 确保目标目录存在
if not tkdnd_target.exists():
    tkdnd_target.mkdir(parents=True, exist_ok=True)

# 复制所有tkdnd文件
for item in tkdnd_source.glob('*'):
    if item.is_file():
        shutil.copy2(item, tkdnd_target)
    elif item.is_dir():
        if item.name == platform_dir:
            # 如果是平台特定目录，复制到根目录
            for platform_file in item.glob('*'):
                shutil.copy2(platform_file, tkdnd_target)
        else:
            shutil.copytree(item, tkdnd_target / item.name, dirs_exist_ok=True)

block_cipher = None

# 收集所有Python源文件
src_files = []
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            # 计算相对于src的路径
            rel_path = os.path.relpath(file_path, 'src')
            # 添加到数据文件列表
            src_files.append((file_path, os.path.join('src', os.path.dirname(rel_path))))

a = Analysis(
    ['src/main.py'],
    pathex=['src'],  # 添加src目录到Python路径
    binaries=[],
    datas=[
        ('temp_tkdnd/tkdnd', 'tkdnd'),  # tkdnd文件
        *src_files,  # 添加所有Python源文件
    ],
    hiddenimports=['tkinter', 'tkinterdnd2', 'tkinterdnd2.TkinterDnD'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide6', 'IPython', 'jedi', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    workpath='./build',  # 使用当前目录下的build目录
    distpath='./dist',   # 使用当前目录下的dist目录
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='工具箱',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 关闭调试控制台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
) 