# Packaging Guide

本目录提供 `onedir + 安装包` 发布链路，默认用于 Windows 10/11。

## 目录说明

- `pyinstaller/tools_box_onedir.spec`
  - 新的 onedir 打包配置，输出 `dist/DataForgeStudio/DataForgeStudio.exe`。
- `installer/tools_box.iss`
  - Inno Setup 安装器脚本，默认安装到 `%LocalAppData%\Programs\DataForgeStudio`。
  - 安装前会清理 `{app}` 目录残留文件，避免升级时旧版本文件干扰新版本运行。
- `scripts/build_onedir.ps1`
  - 构建 onedir 产物。
- `scripts/build_installer.ps1`
  - 校验关键文件后构建安装包。
- `scripts/measure_startup.ps1`
  - 基线（one-file）与候选（onedir）启动耗时对比脚本。

## 快速开始

1. 构建 onedir：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_onedir.ps1 -Clean
```

2. 构建安装包（要求已安装 Inno Setup 6）：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_installer.ps1 -Clean
```

3. 对比启动时间：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\measure_startup.ps1
```

## 关键产物

- onedir 可执行文件：`dist/DataForgeStudio/DataForgeStudio.exe`
- 安装包：`dist_installer/DataForgeStudio-Setup-<version>.exe`

## 回滚方式

旧发布链路保留不变，仍可执行：

```powershell
python -m PyInstaller tools_box.spec --clean
```
