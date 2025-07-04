# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from pathlib import Path
import tkinterdnd2
import platform

# 获取平台特定的目录名
def get_platform_dir():
    if platform.system() == 'Windows':
        return 'win64' if platform.machine().endswith('64') else 'win32'
    return platform.system().lower()

# 准备tkdnd文件
def setup_tkdnd_files():
    platform_dir = get_platform_dir()
    tkdnd_source = Path(tkinterdnd2.__file__).parent / 'tkdnd'
    tkdnd_target = Path('temp_tkdnd/tkdnd')
    
    # 确保目标目录存在
    tkdnd_target.mkdir(parents=True, exist_ok=True)
    
    # 清理旧文件
    if tkdnd_target.exists():
        shutil.rmtree(tkdnd_target)
        tkdnd_target.mkdir(parents=True, exist_ok=True)
    
    # 复制所有tkdnd文件
    for item in tkdnd_source.glob('*'):
        if item.is_file():
            shutil.copy2(item, tkdnd_target)
        elif item.is_dir():
            if item.name == platform_dir:
                # 如果是平台特定目录，复制到根目录
                for platform_file in item.glob('*'):
                    if platform_file.is_file():
                        shutil.copy2(platform_file, tkdnd_target)
            else:
                shutil.copytree(item, tkdnd_target / item.name, dirs_exist_ok=True)

# 收集数据文件
def collect_data_files():
    data_files = [
        ('temp_tkdnd/tkdnd', 'tkdnd'),  # tkdnd文件
    ]
    
    # 添加配置文件
    config_files = [
        'src/gui/widgets/edc_site_adder_config.json'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            data_files.append((config_file, os.path.dirname(config_file)))
    
    return data_files

# 设置 tkdnd
setup_tkdnd_files()

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.', 'src'],  # 简化路径配置
    binaries=[],
    datas=collect_data_files(),
    hiddenimports=[
        'tkinter', 
        'tkinterdnd2', 
        'tkinterdnd2.TkinterDnD',
        'pandas',
        'openpyxl',
        'pyautogui',
        'pygetwindow',
        'pywin32',
        'mouse',
        'keyboard'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PyQt6', 'PySide6', 'PySide2',  # 排除不需要的GUI框架
        'IPython', 'jedi',  # 排除开发工具
        'matplotlib', 'numpy.distutils',  # 排除不需要的科学计算库
        'PIL.ImageTk',  # 如果不使用图像处理
        'scipy', 'sympy',  # 排除科学计算库
        'tornado', 'zmq',  # 排除网络库
        'docutils', 'setuptools',  # 排除构建工具
        'pytest', 'unittest',  # 排除测试框架
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=2,  # 添加Python字节码优化
)

# 过滤掉不需要的文件
def filter_binaries(binaries):
    """过滤掉不需要的二进制文件"""
    excluded_patterns = [
        'api-ms-win-',  # Windows API DLL
        'ucrtbase.dll',  # 如果系统已有
        'msvcp140.dll',  # 如果系统已有
        'vcruntime140.dll',  # 如果系统已有
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

# 应用过滤
a.binaries = filter_binaries(a.binaries)

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
    strip=True,  # 启用符号剥离以减小文件大小
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python39.dll',
        'python3.dll',
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，可以在这里指定
    version_file=None,  # 如果有版本信息文件，可以在这里指定
) 