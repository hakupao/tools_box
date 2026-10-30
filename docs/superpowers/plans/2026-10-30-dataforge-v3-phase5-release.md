# DataForge Studio v3 · 阶段 5：清理、打包、文档、3.0.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先清掉阶段 4 遗留项，再完成以下工作：删除 v2 代码和不再需要的依赖，让 PyInstaller onedir 和 Inno Setup 打出 v3 的安装包，按 v3 重写全部文档和截图，版本号定为 3.0.0。

**Architecture:**
- **版本号**：只在 `src/dataforge/__init__.py` 的 `__version__` 写一份。`pyproject.toml` 和 `build_installer.ps1` 都与它保持一致，用测试锁定。
- **打包入口**：改为 `src/dataforge/__main__.py`，用 `collect_submodules` 收集 `dataforge`、`keyboard`、`mouse`，因为页面是延迟导入的。
- **打包自检**：程序新增 `--self-check` 参数，导入全部工具页面和 EDC 的系统依赖后退出，用来验证打包出来的 exe 没有漏掉模块。
- **文档**：面向用户的文档和面向开发者的文档都以 `docs/tools/*.md`（规则说明）为准，不再重复写规则细节，只链接过去。

**Tech Stack:** Python 3.13（`.venv`）、PySide6 6.12、PySide6-Fluent-Widgets 1.11.3、PyInstaller 6.22.3、Inno Setup 6（`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`）。

**Spec:** `docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md`（§3、§5.1、§8、§10）
**Carry-over:** `docs/superpowers/plans/2026-10-29-dataforge-v3-phase4-carryover.md`（"Final: parked" 与 "Phase-5 notes" 在 Task 1、Task 3 处理）

## Global Constraints

- 阶段 1–4 的全部 Global Constraints 继续有效，下面几条照常适用：
  - 后端不导入 Qt；
  - 界面不用 QSS、hex 颜色、`setFixedWidth`、`processEvents`、`DontUseNativeDialog`、`unhook_all`、`print(`；
  - 测试中不得导入 pyautogui、keyboard、mouse；
  - 任务代码里不创建 QObject。
- 本阶段**允许**删除 v2 代码：`src/gui/`、`src/utils/`、`src/main.py`、`src/version.py`、`src/__init__.py`、根目录 `__init__.py`、根目录 `tools_box.spec`。
- 依赖（spec §10）：
  - 移除 `pygetwindow`、`pyqtgraph`、`tkinterdnd2`、`requests`、`beautifulsoup4`，以及 `.spec` 里对应的 hidden imports；
  - `mouse` 固定为 `mouse==0.7.1`。
  - **裁定**：同时移除 `pandas`、`numpy`、`backports.tarfile`、`jaraco.text`。v3 的代码从不导入它们（阶段 3 起明确不用 pandas），后两个只为 v2 打包时的 `pkg_resources` 存在。
  - **裁定**：直接导入的 `darkdetect` 要显式写进依赖。
- spec §3：继续用 PyInstaller onedir 和 Inno Setup 打包，`packaging/scripts/` 下的三个脚本继续可用。文件名保持不变（裁定），减少改动。
- 打包产物的名称不变：`dist\DataForgeStudio\DataForgeStudio.exe`、`dist_installer\DataForgeStudio-Setup-<版本>.exe`。Inno Setup 的 `AppId` 不变，这样可以直接覆盖安装 v2。
- 版本号 `3.0.0`。`CHANGELOG.md` 新增 `## [3.0.0] - 2026-10-30`。
- 文档用简体中文。`docs/tools/*.md` 是规则的唯一出处，其他文档只链接，不复制规则。
- 测试命令：`.venv/Scripts/python.exe -m pytest tests -q`。提交信息结尾：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

1. **打包后的 exe 打开某个工具页时报"页面加载失败"**：页面是用 `importlib` 延迟导入的，PyInstaller 看不到。`--self-check` 会导入全部页面和 EDC 依赖并返回非 0，打包脚本因此失败。（测试见 Task 3）
2. **从 v2 覆盖安装后丢配置**：主配置在用户目录，不受影响。但安装程序的 `[InstallDelete]` 会清空 `{app}\*`，exe 旁边的 v2 单独配置文件（`edc_site_adder_config.json`、`data_masking_pattern1_config.json`）会在 v3 读取前就被删掉。改为只删 `{app}\_internal` 和 exe 本身。（检查见 Task 3）
3. **删除 v2 后仍有代码或测试引用 `src.gui` / `src.utils`**：用测试扫描 `src/`、`tests/` 中的 `src.gui`、`src.utils`、`from utils`，必须为 0。（测试见 Task 2）
4. **任务栏显示 Qt 默认图标**：v3 目前没有设置窗口图标。开发运行和打包运行都要能找到 `favicon.ico`。（测试见 Task 3）
5. **文档中的命令或路径过期**：例如 `python src/main.py`、`src/utils/...`。用测试扫描 `README.md`、`AGENTS.md`、`docs/*.md`、`packaging/README.md`，不得出现 `src/main.py`、`src/utils`、`src/gui`、`tkinterdnd2`、`pandas`。CHANGELOG 记录历史，不在扫描范围内。（测试见 Task 5）

---

## 文件结构

```
src/dataforge/tools/edc/windows.py        修改：进程名改用 QueryFullProcessImageNameW；空进程名不参与匹配
src/dataforge/tools/edc/live.py           修改：LiveExcel.close()，退出时先释放 COM
src/dataforge/ui/pages/edc/page.py        修改：重做本行后续段失败时，该行记为出错
docs/tools/masking.md                     修改：已知限制写入 M7
src/gui/ src/utils/ src/main.py src/version.py src/__init__.py __init__.py tools_box.spec   删除
tests/test_data_masking_service.py tests/test_unified_config_services.py tests/DS.csv tests/DS.xlsx tests/DS2.csv   删除
docs/XLSX文件制作规范.md                   删除
requirements.txt / .gitignore              修改
src/dataforge/__init__.py / pyproject.toml 修改：3.0.0
src/dataforge/app.py                       修改：窗口图标、--self-check
src/dataforge/ui/resources.py              新增：app_icon_path()
src/dataforge/selfcheck.py                 新增：self_check()
packaging/pyinstaller/tools_box_onedir.spec  重写
packaging/scripts/build_onedir.ps1 / build_installer.ps1   修改
packaging/installer/tools_box.iss          修改：InstallDelete
scripts/capture_screenshots.py             新增：生成 README 截图
README.md CHANGELOG.md AGENTS.md packaging/README.md      重写/更新
docs/用户手册.md docs/开发文档.md docs/API文档.md docs/UI界面规范.md   重写
tests/dataforge/test_release.py            新增：版本、依赖、v2 残留、文档过期内容
```

---

### Task 1: 阶段 4 遗留项

**Files:**
- Modify:
  - `src/dataforge/tools/edc/windows.py`
  - `src/dataforge/tools/edc/live.py`
  - `src/dataforge/ui/pages/edc/page.py`
  - `docs/tools/masking.md`
  - `docs/tools/edc_site_adder.md`
- Test:
  - `tests/dataforge/test_edc_windows.py`
  - `tests/dataforge/test_edc_live.py`
  - `tests/dataforge/test_edc_page.py`
  - `tests/dataforge/test_edc_config.py`

**Interfaces:**
- Produces：
  - `windows.process_name(hwnd) -> str`：
    - 用 `win32api.OpenProcess(0x1000, False, pid)` 打开进程（`0x1000` 即 `PROCESS_QUERY_LIMITED_INFORMATION`，能跨权限级别）；
    - 用 `ctypes.windll.kernel32.QueryFullProcessImageNameW` 取 exe 路径。函数原型要写正确：`argtypes = [HANDLE, DWORD, LPWSTR, POINTER(DWORD)]`，`restype = BOOL`，缓冲区 32768；
    - 返回小写 basename，失败返回 `""`，句柄在 `finally` 里关闭。
  - `windows.find_target`：`target.process` 为空时只按第 1 条规则匹配（hwnd 相同且进程名也为空）；规则 2、3 只考虑进程名非空的候选。规则说明 `edc_site_adder.md` 的匹配顺序一节补一句说明。
  - `LiveExcel.close(self) -> None`：把 `self._app` 置为 None。`open_live_ports` 在 `finally` 里先 `close()`，再 `CoUninitialize()`。
  - `EdcPage`：
    - 选"重做本行"后，如果后续段失败或被取消，当时停下的那一行没有任何结果；
    - 把这一行记入会话的 `failed`，reason 写成 `重做未完成：{失败消息或"已取消"}`，然后再显示汇总；
    - 做法：会话里记录 `pending_redo: RowStop | None`；后续段正常返回时清空它。
  - `masking.md` 的"已知限制"加一条：同一个文件里有两个完全同名、日期顺序都有歧义的列时，它们共用一个 日/月 顺序选择。
- [ ] **Step 1: 写失败测试**
  - `test_process_name_own_process`：对 `test_edc_windows.py` 中已有的 win32 探针窗口，返回 `python.exe` 或 `python3.13.exe`（以 `python` 开头）。
  - `test_find_target_empty_process`：目标窗口的进程名为空，候选是一个进程名为空、hwnd 不同的窗口 → None；hwnd 相同 → 返回它。
  - `test_close_before_uninitialize`：patch `pythoncom`，并记录调用顺序 → `close` 在 `CoUninitialize` 之前。
  - `test_redo_then_continuation_fails_records_row`：
    - 第 2 行失败，`ask_stop_choice` 返回 REDO；
    - 第二次调用 `open_live_ports` 时抛 `DataForgeError("Excel 已关闭")`；
    - 结果区显示 `failed: 1`，警告页含 `重做未完成：Excel 已关闭`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`fix(v3): phase 4 carry-over (elevated process name, COM close, redo summary)`

---

### Task 2: 删除 v2 代码与依赖

**Files:**
- Delete：
  - v2 代码：`src/gui/`、`src/utils/`、`src/main.py`、`src/version.py`、`src/__init__.py`、根目录 `__init__.py`、根目录 `tools_box.spec`；
  - v2 测试：`tests/test_data_masking_service.py`、`tests/test_unified_config_services.py`、`tests/DS.csv`、`tests/DS.xlsx`、`tests/DS2.csv`；
  - `docs/XLSX文件制作规范.md`；
  - 磁盘上的 `temp_tkdnd/`。它不在 git 中，删除前先确认没有被跟踪。
- Modify：`requirements.txt`、`.gitignore`（去掉 `temp_tkdnd/` 一行）
- Create：`tests/dataforge/test_release.py`
- Test：`tests/dataforge/test_edc_config.py`

**Interfaces:**
- 删除之前先核对覆盖范围。逐条阅读两个 v2 测试文件，在报告里列一张"v2 测试 → v3 测试"对照表：
  - 已有对应的 v3 测试，就写出测试名；
  - 没有对应的，补到 v3 测试里。已知需要补：EDC 保存时保留其他 section，即 `test_save_keeps_other_sections`（在 `test_edc_config.py` 中）。
- 新的 `requirements.txt`，内容与顺序如下：
  ```
  openpyxl>=3.1.5
  platformdirs>=4.2.2
  darkdetect>=0.8.0
  PySide6>=6.8
  PySide6-Fluent-Widgets>=1.7
  pywin32>=308
  pyautogui==0.9.54
  pyperclip>=1.8.2
  keyboard==0.13.5
  mouse==0.7.1
  pyinstaller>=6.11
  ```
- `tests/dataforge/test_release.py`（本任务先写其中两项）：
  - `test_no_v2_tree`：`src/gui`、`src/utils`、`src/main.py`、`src/version.py` 都不存在；在 `src/` 和 `tests/` 的 `.py` 文件中，排除本测试文件后，搜索 `src.gui`、`src.utils`、`from utils` 的结果为 0。
  - `test_requirements`：
    - 不含 `pygetwindow`、`pyqtgraph`、`tkinterdnd2`、`requests`、`beautifulsoup4`、`pandas`、`numpy`；
    - 含 `mouse==0.7.1`；
    - 含 `darkdetect`。
- [ ] **Step 1:** 写出对照表，补齐缺失的 v3 测试，并写 `test_release.py` 的两项 → 运行，`test_release` 的两项 FAIL。
- [ ] **Step 2:** 删除文件、更新 `requirements.txt` 和 `.gitignore`。
- [ ] **Step 3:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS。`python -m dataforge` 能启动（用 `QT_QPA_PLATFORM=offscreen` 运行 3 秒后结束进程，没有 ImportError 即可）。
- [ ] **Step 4:** Commit：`chore(v3): remove v2 code, tests and unused dependencies`

---

### Task 3: 版本 3.0.0、窗口图标、打包自检、打包脚本

**Files:**
- Create：
  - `src/dataforge/ui/resources.py`
  - `src/dataforge/selfcheck.py`
- Modify：
  - `src/dataforge/__init__.py`
  - `pyproject.toml`
  - `src/dataforge/app.py`
  - `packaging/pyinstaller/tools_box_onedir.spec`（重写）
  - `packaging/scripts/build_onedir.ps1`
  - `packaging/scripts/build_installer.ps1`
  - `packaging/installer/tools_box.iss`
- Test：
  - `tests/dataforge/test_package.py`
  - `tests/dataforge/test_release.py`
  - `tests/dataforge/test_selfcheck.py`

**Interfaces:**
- **版本号**：`__version__ = "3.0.0"`，`pyproject.toml` 中 `version = "3.0.0"`。
- **图标**：`ui/resources.py` 提供 `def app_icon_path() -> Path | None`：
  - 打包运行时（`sys.frozen`）返回 `Path(sys._MEIPASS) / "assets" / "icons" / "favicon.ico"`；
  - 开发运行时返回 `Path(__file__).resolve().parents[3] / "assets" / "icons" / "favicon.ico"`；
  - 文件不存在时返回 None。
  - `app.main` 在创建 `QApplication` 之后，路径不为 None 时调用 `app.setWindowIcon(QIcon(str(path)))`。
- **自检**：`selfcheck.py` 提供 `def self_check() -> list[str]`：
  - 依次 `importlib.import_module`：registry 中每个 `ToolSpec.page` 的模块，再加上 `dataforge.tools.edc.live`、`pyautogui`、`pyperclip`、`keyboard`、`mouse`、`win32com.client`、`pythoncom`、`win32gui`、`win32process`、`openpyxl`；
  - 返回失败项列表，每项格式为 `"<模块>: <异常>"`。
  - `self_check` 本身不创建 QApplication；页面模块只导入，不实例化。
  - `app.main(argv)`：参数中有 `--self-check` 时，在 `setup_logging()` 之后调用 `self_check()`，把每个失败项记为 `logger.error`，然后写结果文件 `<日志目录>/self_check.txt`，内容为 `OK` 或失败项（每行一项）。全部通过返回 0，否则返回 1。这条路径不创建窗口。
- **打包配置**：`tools_box_onedir.spec` 重写：
  - 入口：`src/dataforge/__main__.py`；`pathex=[src]`；
  - `hiddenimports` 由以下几部分组成：`collect_submodules("dataforge")`、`collect_submodules("keyboard")`、`collect_submodules("mouse")`，再加上 `pythoncom`、`pywintypes`、`win32com.client`、`win32gui`、`win32process`、`win32api`、`win32con`；
  - `datas=[(assets/icons/favicon.ico, "assets/icons")]`；
  - 不再包含 tkinter / tkdnd / pandas / requests / bs4 / pygetwindow；
  - `excludes` 保留原有项，再加上 `tkinter`、`pandas`、`numpy`。但 `unittest` 不能排除：pyautogui 的依赖链可能用到它，先实测再定，并在报告里写明结论；
  - 保留 `filter_binaries`、`console=False`、图标、名称 `DataForgeStudio`。
- **`build_onedir.ps1`**：
  - Python 解释器的选择顺序：`$env:PYTHON`、`<repo>\.venv\Scripts\python.exe`、`python`；
  - `-Clean` 不再处理 `temp_tkdnd`；
  - 构建成功后运行 `dist\DataForgeStudio\DataForgeStudio.exe --self-check` 并等待退出，退出码不为 0 时 `throw`，同时把 `self_check.txt` 的内容打印出来。日志目录与 `dataforge.core.logs.default_log_dir()` 一致，即 platformdirs 的 `user_log_dir("dataforge_studio", appauthor=False)`；脚本可以调用 venv 里的 Python 取得这个路径。
- **`build_installer.ps1`**：
  - 版本号从 `src\dataforge\__init__.py` 中的 `__version__ = "x"` 解析；
  - 去掉 tkdnd 检查，改为检查 `_internal\assets\icons\favicon.ico` 是否存在；
  - 其他逻辑不变。
- **`tools_box.iss`**：
  - `[InstallDelete]` 只删 `{app}\_internal` 和 `{app}\{#MyAppExeName}`（Review Focus 2）；
  - `[UninstallDelete]` 不变。
- **`test_release.py`** 增加：
  - `test_version_consistent`：`dataforge.__version__ == "3.0.0"`，`pyproject.toml` 中的版本相同，`CHANGELOG.md` 含 `## [3.0.0]`。CHANGELOG 由 Task 4 写，所以这条断言放在 Task 4 加入，本任务先断言前两项。
  - `test_spec_has_no_removed_imports`：spec 文本中不出现 `tkinterdnd2`、`pygetwindow`、`requests`、`bs4`、`pandas`、`src/main.py`。
  - `test_installer_keeps_side_files`：`.iss` 的 `[InstallDelete]` 一节不出现 `{app}\*`。
- **其他测试**：
  - `test_package.py::test_version` 改为 `3.0.0`；
  - `test_selfcheck.py::test_self_check_passes_in_dev`：开发环境下 `self_check() == []`。注意：这条测试会导入 pyautogui、keyboard、mouse。**裁定**：它是唯一允许导入这三个库的测试，因为它就是用来验证"能不能导入"的；而且它在子进程里运行（`subprocess` 执行 `-c "from dataforge.selfcheck import self_check; ..."`），不污染测试进程；
  - `test_self_check_reports_failure`：patch `importlib.import_module`，让某个模块抛 `ImportError`，返回值中包含该模块名；
  - `test_app_icon_path_dev`：返回的路径存在。
- [ ] **Step 1:** 写失败测试 → 运行 → FAIL
- [ ] **Step 2:** 实现代码和打包配置。
- [ ] **Step 3:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 4:** `powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_onedir.ps1 -Clean` → 构建成功，自检输出 `OK`。在报告里记录 `dist\DataForgeStudio` 的大小（MB），并和 v2 对比（如果 git 里或磁盘上已有 v2 的产物）。
- [ ] **Step 5:** `powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_installer.ps1 -SkipBuild` → 生成 `dist_installer\DataForgeStudio-Setup-3.0.0.exe`。
- [ ] **Step 6:** `powershell -ExecutionPolicy Bypass -File .\packaging\scripts\measure_startup.ps1 -BaselineExe .\nonexistent.exe` → 候选 exe 在 30 秒内出现主窗口，记录启动时间。`dist/`、`dist_installer/` 已在 `.gitignore` 中，不提交。
- [ ] **Step 7:** Commit：`build(v3): version 3.0.0, app icon, self-check and packaging`

---

### Task 4: README、CHANGELOG、AGENTS.md、打包说明、截图

**Files:**
- Create：`scripts/capture_screenshots.py`
- Replace：`docs/images/readme/*.png`
- Modify：
  - `README.md`
  - `CHANGELOG.md`
  - `AGENTS.md`
  - `packaging/README.md`
  - `tests/dataforge/test_release.py`（加入 CHANGELOG 断言）

**Interfaces:**
- **截图脚本** `scripts/capture_screenshots.py`：
  - 在真实桌面上运行，**不能**用 offscreen 模式，因为中文字体需要系统渲染；
  - 使用临时配置（设置 `DATAFORGE_STUDIO_CONFIG_PATH` 指向临时文件），这样不会读到作者自己的配置和最近使用记录；
  - 创建 `MainWindow`，窗口大小 1200×760；
  - 依次截取以下图片（用 `window.grab()`，每次切换后用 `QTimer` 等待 300 ms 再截），保存到 `docs/images/readme/`：
    - 亮色主页 → `home-light.png`
    - 暗色主页 → `home-dark.png`
    - 亮色格式转换页 → `format-convert.png`
    - 暗色数据模糊化页 → `masking-dark.png`
    - 亮色 EDC 页 → `edc.png`
  - 截完后退出，并删除旧图 `home-overview.png`、`file-format-converter.png`、`data-masking-workflow.png`、`edc-site-adder.png`。
- **`README.md`**（重写）：
  - 一句话简介；
  - 截图（亮色、暗色主页各一张，三个工具页并排）；
  - 7 个工具的表格（名称、用途、规则说明链接 `docs/tools/*.md`）；
  - 运行方式：`python -m venv .venv`，`pip install -r requirements-dev.txt`，`.venv\Scripts\python -m dataforge`；
  - 测试命令；
  - 打包命令（三个脚本）；
  - 配置文件和日志位置：`%LOCALAPPDATA%\dataforge_studio\...`，具体以 platformdirs 为准，设置页里可以直接打开；
  - 从 v2 升级的说明：配置自动迁移，仕様書工作流和死链检测已移除；
  - 说明 Python 版是过渡版，规则说明和标准样例用于 C#/Rust 版对照。
- **`CHANGELOG.md`**：新增 `## [3.0.0] - 2026-10-30`，分"移除 / 变更 / 新增 / 修复"四节：
  - 内容逐条对应 spec 中所有标【变更】的项，以及 §5 的界面变化；
  - 写给用户看，不提内部实现；
  - `[Unreleased]` 保留为空。
- **`AGENTS.md`**（重写为 v3）：
  - 项目概况：入口 `python -m dataforge`，包结构与 spec §9 一致；
  - 环境与命令；
  - 分层规则：后端不导入 Qt，`run(inputs, options, progress, cancel) -> Result`；
  - 界面规则：本计划 Global Constraints 中的禁用项；
  - 后台任务规则：JobRunner、只允许辅助任务、任务代码里不创建 QObject；
  - 配置：ConfigStore、section、legacy 迁移；
  - 测试：unittest 风格、golden 样例、`make_fixtures.py` 中写字面值；
  - 规则说明：改规则必须同步修改 `docs/tools/*.md` 和标准样例；
  - 删除所有 v2 内容（`src/gui`、`*_service.py`、`qt_common.py`、强制浅色等）。
- **`packaging/README.md`**：三个脚本的用法、`--self-check`、输出位置、Inno Setup 路径、覆盖安装说明。
- `test_release.py::test_version_consistent` 加上 CHANGELOG 断言。
- [ ] **Step 1:** 在真实桌面运行 `.venv/Scripts/python.exe scripts/capture_screenshots.py`，生成 5 张图。打开其中至少 2 张（用 Read 工具查看图片），确认中文正常显示、暗色确实是暗色。
- [ ] **Step 2:** 写这 4 份文档。
- [ ] **Step 3:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 4:** Commit：`docs(v3): README, CHANGELOG 3.0.0, AGENTS.md, packaging notes and screenshots`

---

### Task 5: 用户手册、开发文档、API 文档、UI 规范

**Files:**
- Modify（整体重写）：
  - `docs/用户手册.md`
  - `docs/开发文档.md`
  - `docs/API文档.md`
  - `docs/UI界面规范.md`
- Modify：`docs/tools/README.md`（如需补充索引）、`tests/dataforge/test_release.py`

**Interfaces:**
- **`用户手册.md`**：
  - 安装与升级；
  - 主页（最近使用、工具格）；
  - 窗口宽度与布局（宽、中、窄三档）；
  - 编码选择对话框；
  - 每个工具一节：用途、操作步骤、输出位置；规则细节链接到 `docs/tools/<tool>.md`；
  - 设置页；
  - 常见问题：文件被 Excel 打开、编码有歧义、EDC 停止后怎么选、ESC 停止。
- **`开发文档.md`**：
  - 架构分层图，用文字或 mermaid；
  - 目录说明；
  - 新增一个工具的步骤：后端模块 → Result → 页面继承 ToolPage → registry 登记 → 规则说明 → golden 样例；
  - JobRunner 与辅助任务、编码重跑、主线程 GC；
  - 配置与迁移；
  - 主题；
  - 测试与 golden；
  - 打包与自检。
- **`API文档.md`**：
  - 只写对外稳定的后端接口，即 C#/Rust 移植时需要对照的部分：`core`（Result、FileIssue、EncodingQuestion、CancelToken、ProgressFn、DataForgeError、Cancelled）、`fileio`（编码识别、读写 CSV、输出路径、`atomic_path`）、`dates`、每个工具的 options dataclass 和 `run` 签名，以及 EDC 的执行接口和 `run_segment` / `EdcSession`；
  - 签名必须从源码核对，不能凭记忆写。
- **`UI界面规范.md`**：
  - 主题：`Theme.AUTO`、Mica、原生对话框；
  - 禁用项清单，与 Global Constraints 相同，并说明原因；
  - 语义色集中定义的位置；
  - 布局：三档宽度、ResponsiveForm、结果区的三个标签页；
  - 交互：结果一律用 InfoBar，模态对话框只用于需要用户确认的场景，运行时锁定输入；
  - 唯一例外：EDC 浮层用固定配色；
  - 新页面检查清单。
- `test_release.py` 加入 `test_docs_not_stale`（Review Focus 5）：在 `README.md`、`AGENTS.md`、`packaging/README.md`、`docs/*.md`（仅 docs 根目录，不含 `superpowers/`）中，不得出现 `src/main.py`、`src/utils`、`src/gui`、`tkinterdnd2`、`pandas`、`processEvents`。例外：`UI界面规范.md` 在禁用清单中出现 `processEvents` 是允许的，按行判断，该行同时含"禁止"或"不用"即可。
- [ ] **Step 1:** 先写 `test_docs_not_stale` → FAIL（旧文档中有这些词）。
- [ ] **Step 2:** 重写 4 份文档。API 签名逐个用 `grep -n "def run\|class .*Options" src/dataforge` 核对。
- [ ] **Step 3:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 4:** Commit：`docs(v3): rewrite user manual, developer guide, API reference and UI guidelines`

---

### Task 6: 阶段验收

- [ ] **Step 1:** `.venv/Scripts/python.exe -m pytest tests -q` 连续 3 次 → 全部 PASS。
- [ ] **Step 2:** 禁用模式检查：`grep -rnE "setStyleSheet|#[0-9a-fA-F]{6}|setFixedWidth|processEvents|DontUseNativeDialog|import pandas|print\(|unhook_all" src/dataforge` → 无输出。
- [ ] **Step 3:** 请作者手动验收：
  1. **安装**：双击 `dist_installer\DataForgeStudio-Setup-3.0.0.exe`，在装过 v2 的电脑上覆盖安装。启动后：任务栏图标正确；设置页显示 3.0.0；v2 的数据模糊化配置和 EDC 坐标都还在。
  2. **打包版全部工具可用**：在打包版里逐个打开 7 个工具页，都能正常显示；EDC 页的"回放测试"能闪出标记。
  3. **主题**：切换 Windows 的亮色 / 暗色后，程序跟着切换。
  4. **文档**：看一遍 README 和截图，以及用户手册中自己常用的那一节。
- [ ] **Step 4:** 新建 `docs/superpowers/plans/2026-10-29-dataforge-v3-phase5-carryover.md`，记录裁定与遗留项，写明仍未处理的事项（例如 M7）。Commit：`docs(v3): record phase 5 rulings and carry-over items`。
- [ ] **Step 5:** 之后的合并、打 tag、发布，都由作者在 finishing-a-development-branch 的选项中决定。本计划不合并、不打 tag、不推送。
