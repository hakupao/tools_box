# 打包说明

本目录用 PyInstaller（onedir 模式）和 Inno Setup 6 生成 DataForge Studio 的 Windows 程序目录和安装包。当前版本 3.0.0。

## 准备

1. 按仓库根目录 README 的"从源码运行"建好 `.venv`，并执行过 `pip install -e .`。`requirements-dev.txt` 已包含 PyInstaller。
2. 生成安装包还需要 Inno Setup 6。脚本按以下顺序查找 `ISCC.exe`：
   - `PATH` 中的 `iscc.exe`；
   - `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`；
   - `C:\Program Files\Inno Setup 6\ISCC.exe`。

## 目录内容

| 文件 | 作用 |
| --- | --- |
| `pyinstaller/tools_box_onedir.spec` | PyInstaller 配置。入口 `src/dataforge/__main__.py`，收集 `dataforge`、`keyboard`、`mouse` 的全部子模块和 pywin32 相关模块，带上 `assets/icons/favicon.ico` |
| `installer/tools_box.iss` | Inno Setup 安装脚本 |
| `scripts/build_onedir.ps1` | 生成程序目录并运行自检 |
| `scripts/build_installer.ps1` | 生成安装包 |
| `scripts/measure_startup.ps1` | 测量启动时间 |

文件名沿用 v2，没有改。

## 1. 生成程序目录：build_onedir.ps1

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_onedir.ps1 -Clean
```

- `-Clean`：先删除 `build\` 和 `dist\`。
- Python 解释器按以下顺序选择：环境变量 `PYTHON`、`.venv\Scripts\python.exe`、`PATH` 中的 `python`。
- 输出：`dist\DataForgeStudio\DataForgeStudio.exe`（同目录下的 `_internal\` 是运行所需文件）。
- 构建完成后脚本会自动运行一次自检（见下文）。自检失败时脚本报错退出。

## 2. 打包自检：--self-check

```powershell
.\dist\DataForgeStudio\DataForgeStudio.exe --self-check
```

- 工具页面是在第一次打开时才加载的，PyInstaller 分析不到。自检会导入全部工具页面，以及 EDC 用到的 pyautogui、pyperclip、keyboard、mouse、pywin32 和 openpyxl，用来发现打包时漏掉的模块。
- 不打开窗口。全部成功时退出码为 0，否则为 1。
- 打包后的程序没有控制台，结果写在日志目录的 `self_check.txt` 中：通过时内容为 `OK`，否则每行一个失败的模块和原因。日志目录一般是 `%LOCALAPPDATA%\dataforge_studio\Logs\`（以 platformdirs 为准）。
- `build_onedir.ps1` 会先删掉旧的 `self_check.txt`，运行后把新内容打印出来。

开发环境下也可以运行：`.venv\Scripts\python -m dataforge --self-check`。

## 3. 生成安装包：build_installer.ps1

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_installer.ps1 -Clean
```

- 默认先调用 `build_onedir.ps1`；`-Clean` 会传给它。
- `-SkipBuild`：跳过构建，直接用已有的 `dist\DataForgeStudio` 生成安装包。
- 版本号从 `src\dataforge\__init__.py` 的 `__version__` 读取。
- 生成前检查：`DataForgeStudio.exe`、Qt 平台插件 `qwindows.dll`、程序目录中的 `_internal\assets\icons\favicon.ico`、仓库中的 `assets\icons\favicon.ico`。
- 输出：`dist_installer\DataForgeStudio-Setup-<版本>.exe`，例如 `DataForgeStudio-Setup-3.0.0.exe`。

`dist\`、`dist_installer\` 和 `build\` 都不提交到 git。

## 4. 测量启动时间：measure_startup.ps1

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\measure_startup.ps1
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-BaselineExe` | `.\dist\DataForgeStudio.exe` | 对比用的旧版程序，不存在时只测候选程序 |
| `-CandidateExe` | `.\dist\DataForgeStudio\DataForgeStudio.exe` | 要测量的程序 |
| `-Runs` | 5 | 正式测量次数 |
| `-Warmup` | 1 | 预热次数，不计入结果 |
| `-TimeoutSec` | 30 | 等待主窗口出现的最长时间（秒） |

## 安装与覆盖安装

- 默认安装位置：`%LOCALAPPDATA%\Programs\DataForgeStudio`，不需要管理员权限。
- 安装包的 `AppId` 与 v2 相同，可以直接覆盖安装 v2 或更早的 3.x，不用先卸载。
- 覆盖安装时只删除旧的 `_internal\` 目录和 `DataForgeStudio.exe`，再装入新文件。程序目录旁边 v2 的单独配置文件（`edc_site_adder_config.json`、`data_masking_pattern1_config.json`）会保留，v3 第一次打开对应工具时读取并迁移到新配置文件。
- 卸载时删除整个程序目录。
- 主配置和日志都在用户目录（`%LOCALAPPDATA%\dataforge_studio\`），安装和卸载都不会动它们。
