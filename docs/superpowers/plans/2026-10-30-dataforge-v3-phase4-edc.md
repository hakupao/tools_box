# DataForge Studio v3 · 阶段 4：EDC 站点添加 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先清掉阶段 3 遗留项，再完成"EDC 站点添加"。要点：
- 执行部分（点击、剪贴板、Excel、窗口激活）可以注入，循环逻辑不碰真实屏幕也能测试；
- 录制时记住目标窗口；
- 出错即停，停下后让用户在 3 个选项里选；
- 录制浮层的回调线程安全，ESC 热键只在运行期间生效；
- 提供与语言无关的标准样例（执行动作序列）和规则说明。

**Architecture:**
- **后端**：`dataforge.tools.edc` 不依赖 Qt，分 4 个模块：
  - `config`：配置与 v2 迁移；
  - `windows`：目标窗口的枚举、匹配和激活，用 pywin32；
  - `loop`：执行接口（Protocol）、逐行循环和整次运行的汇总；
  - `live`：真实的 Excel COM、pyautogui、pyperclip 实现，延迟导入。
- **分段运行**：一次"开始处理"由若干**段**组成。每段是一个辅助任务（kind `"edc"`），在某一行出错或被 ESC 停下时**正常返回**，`Result.data` 是这一段的 `Segment`。页面在 `on_aux_finished` 里弹出 3 选 1 对话框，再用 `submit_job_when_idle` 从指定单元格提交下一段。
- **两种停止方式**：
  - **ESC 和取消按钮是"软停止"**：设置本段的 `threading.Event`，循环在步骤之间检查它，然后按"该行在第 k 步停下"返回，接着弹出对话框。
  - **`CancelToken` 是"硬取消"**：只在程序退出（`JobRunner.shutdown`）时使用，循环收到后抛出 `Cancelled`。
- **界面侧**：
  - 键盘钩子、鼠标钩子的回调只发信号；
  - 录制浮层的步骤推进、提示更新、关闭都在主线程的槽函数里做。

**Tech Stack:** Python 3.13（`.venv`），PySide6 6.12，PySide6-Fluent-Widgets 1.11.3，pywin32 312（`win32com`、`win32gui`、`win32process`、`win32api`、`pythoncom`），pyautogui 0.9.54，pyperclip，keyboard 0.13.5，mouse 0.7.1。不新增依赖。

**Spec:** `docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md`（§3、§5.1、§5.4、§6.1、§6.3、§7.5）
**Carry-over:** `docs/superpowers/plans/2026-10-29-dataforge-v3-phase3-carryover.md`（"Final: parked" 与 "Phase-4 notes" 在 Task 1 处理）

## Global Constraints

- 阶段 1–3 的全部 Global Constraints 继续有效，包括：
  - 后端（`core`/`fileio`/`config`/`tools`）不导入 PySide6/qfluentwidgets，不用 `print`；
  - 界面不用 QSS、hex 颜色、`setFixedWidth`、`processEvents`、`DontUseNativeDialog`；
  - 同一时间只运行一个任务；
  - v2 代码（`src/gui`、`src/utils`、`src/main.py`）不动；
  - 任务代码里不创建 QObject、不调用 `gc.collect()`；
  - 只有在清理后立即再抛出时，才可以捕获 `BaseException`。
- 录制浮层和回放标记可以用固定配色，但只能用 `QColor(r, g, b, a)` 写在 `paintEvent` 或调色板里。不写 hex，不调用 `setStyleSheet`，按钮用 Fluent 的 `PrimaryPushButton` / `PushButton`。
- spec §7.5 中没有标【变更】的规则以 v2 为准：`src/utils/edc_site_adder_worker.py`、`src/utils/edc_site_adder_service.py`、`src/gui/widgets/edc_recording_overlay.py`。等待时间照抄 v2：
  - 复制后 0.1 s；
  - 激活窗口后 0.1 s；
  - 点击【搜索框】后 0.05 s，再按 Ctrl+V；
  - 每次点击后 `step_delay`；
  - 选中下一行后 0.1 s。
- 配置：
  - section 名固定 `edc_site_adder`，旧文件名 `edc_site_adder_config.json`；
  - `retry_count` 读取时忽略、保存时不写；
  - 默认值只在 `EdcConfig` 里写一份。
- 新工具登记：
  - id `edc`；
  - 名称 `EDC 站点添加`；
  - 说明 `录制点击位置，从 Excel 逐行回放`；
  - 组 `ToolGroup.BUSINESS`，放在 masking 之后；
  - 图标 `FluentIcon.ROBOT`。
- EDC 不进"最近使用"：它没有输入文件，也没有要恢复的参数。（裁定）
- 测试中不得导入 pyautogui、keyboard、mouse，也不得操作真实的鼠标、键盘、剪贴板或 Excel。这些都通过假实现或 patch 替代。真实实现只做"可导入"和 COM 初始化路径的测试。
- 测试命令：`.venv/Scripts/python.exe -m pytest tests -q`。
- 提交信息结尾：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

1. **Excel 没打开，或者没有选中单元格**：点"开始处理"后显示中文错误 InfoBar，例如"未检测到正在运行的 Excel…"，不能出现"内部错误"。不留下运行中的会话，ESC 钩子已注销。（测试见 Task 4、Task 7）
2. **运行途中目标浏览器窗口被关闭**：该行在第 3 步"激活目标窗口"停下，原因是"找不到目标窗口：…"，然后弹出 3 选 1 对话框。（测试见 Task 3、Task 4）
3. **单元格带首尾空格，或者只有空格**：值去掉首尾空格后再复制；只有空格算空单元格，正常结束（与 v2 相同）。（测试见 Task 3）
4. **鼠标移到屏幕角落触发 pyautogui 安全停止（`FailSafeException`）**：该行停下，原因是"鼠标移到了屏幕角落，已触发安全停止"，不当作内部错误。（测试见 Task 3）
5. **在 3 选 1 对话框打开时或运行结束后按 ESC**：不影响下一段，也不注册任何钩子。ESC 钩子只在一段运行期间存在，注销时只注销自己的那个句柄，从不调用 `unhook_all`。（测试见 Task 5、Task 7）

---

## 文件结构

```
src/dataforge/ui/jobs.py                        修改：JobRunner.is_closing()
src/dataforge/ui/components/tool_page.py        修改：退出时的后续任务不再提示；keep_log_for_next_start()
src/dataforge/tools/masking/scan.py             修改：select_files()
src/dataforge/tools/masking/execute.py          修改：StaleScanError；写出 OSError 包装
src/dataforge/ui/pages/masking/page.py          修改：复用 select_files；StaleScanError；恢复默认值提示
src/dataforge/ui/pages/masking/scan_view.py     修改：重扫后保留日期顺序选择
src/dataforge/tools/edc/__init__.py             新增
src/dataforge/tools/edc/windows.py              新增：WindowInfo、find_target、list_windows、window_at、activate_window
src/dataforge/tools/edc/config.py               新增：EdcConfig、加载/保存/迁移
src/dataforge/tools/edc/loop.py                 新增：执行接口、run_segment、EdcSession
src/dataforge/tools/edc/live.py                 新增：open_live_ports()（真实实现）
src/dataforge/ui/pages/edc/__init__.py          新增
src/dataforge/ui/pages/edc/hooks.py             新增：EscHook、MouseClickHook
src/dataforge/ui/pages/edc/overlay.py           新增：RecordingOverlay、FlashMarker、schedule_replay、坐标换算
src/dataforge/ui/pages/edc/dialogs.py           新增：StopDialog / ask_stop_choice、WindowPickerDialog / pick_window
src/dataforge/ui/pages/edc/page.py              新增：EdcPage
src/dataforge/ui/registry.py                    修改：登记 edc
tests/dataforge/edc_fakes.py                    新增：FakePorts（记录动作序列、注入失败、模拟 ESC）
tests/dataforge/golden.py                       修改：edc 适配器
tests/golden/edc/...                            新增样例 + make_fixtures.py
docs/tools/edc_site_adder.md                    新增：规则说明（与语言无关）
docs/tools/README.md                            修改：加入 EDC
```

---

### Task 1: 阶段 3 遗留项

**Files:**
- Modify:
  - `src/dataforge/ui/jobs.py`
  - `src/dataforge/ui/components/tool_page.py`
  - `src/dataforge/tools/masking/scan.py`
  - `src/dataforge/tools/masking/execute.py`
  - `src/dataforge/ui/pages/masking/page.py`
  - `src/dataforge/ui/pages/masking/scan_view.py`
- Test:
  - `tests/dataforge/test_jobs.py`
  - `tests/dataforge/test_tool_page.py`
  - `tests/dataforge/test_masking_scan.py`
  - `tests/dataforge/test_masking_execute.py`
  - `tests/dataforge/test_masking_page.py`

**Interfaces:**
- Produces:
  - `JobRunner.is_closing(self) -> bool`：`shutdown()` 调用后为 True。
  - `ToolPage.submit_job_when_idle`：延后提交的回调在 `runner.is_closing()` 时直接断开连接并返回，不提交任务，也不弹任何 InfoBar。
  - `scan.select_files(paths: Sequence[Path]) -> list[Path]`：
    - 只保留后缀为 `.csv`（不区分大小写）、`is_file()` 为真的路径；
    - 去重，保持原顺序；
    - `scan()` 和 `MaskingPage._scan_paths()` 都改为调用它。
  - `execute.StaleScanError(DataForgeError)`：现有两处"读取失败，请重新扫描"的异常改为抛出它，消息文字不变。
  - `execute.run`：写出域文件、`usubjid_mapping.csv` 或扫描报告时的 `OSError`，改为抛出 `DataForgeError(f"无法写入输出文件 {name}（{exc}）")`，临时文件夹照常删除。
  - `MaskingPage`：
    - **判断扫描是否过期**：执行任务的闭包捕获 `StaleScanError` 时，先设置本次任务新建的 `threading.Event`，再原样抛出。`_on_failed` 根据这个 Event 判断是否丢弃报告，不再匹配消息中的子串。
    - **恢复默认值**：点"恢复默认值"后显示 `InfoBar.success("已恢复默认值", "下次执行时保存")`。
  - `ScanResultView.show_report`：新报告中 `(file_name, column)` 与旧选择相同的歧义列，保留原来的 日/月 顺序选择。保留的选择不发出 `orders_changed`，由页面在 `_set_report` 里刷新摘要。
- 裁定：M7（同名歧义日期列共用一个顺序键）继续推迟。修改它会牵动 `export_report`、`MaskOptions` 和 `rule_chain_ambiguous` 标准样例，而真实 SDTM 文件不会出现同名列。

- [ ] **Step 1: 写失败测试**
  - `test_is_closing_after_shutdown`：runner 空闲时 `shutdown()` 之后 `is_closing()` 为 True。
  - `test_when_idle_follow_up_dropped_on_shutdown`：
    - runner 忙时调用 `submit_job_when_idle`；
    - 再调用 `runner.shutdown()`；
    - 断言 `InfoBar.warning` 未被调用，后续任务没有提交。
  - `test_select_files_filters_and_dedups`：输入 `[a.CSV, a.CSV, b.txt, 不存在.csv, 文件夹.csv/]`，结果只剩 `[a.CSV]`。
  - `test_stale_scan_error_type`：扫描后删除 AE，`execute.run` 抛出 `StaleScanError`，消息含 `请重新扫描`。
  - `test_write_oserror_wrapped`：patch `write_csv_rows`，让它在第 2 个文件上抛 `PermissionError`。断言：
    - 抛出 `DataForgeError`，消息以 `无法写入输出文件` 开头；
    - 输出目录下没有 `masked_output_*`，也没有临时文件夹。
  - `test_stale_detected_by_type`（页面）：patch `execute.run` 抛 `StaleScanError("x")`（消息里不含"请重新扫描"）。点"开始处理"后，主按钮文字回到 `开始扫描`。
  - `test_restore_defaults_feedback`：点"恢复默认值"，`InfoBar.success` 收到标题 `已恢复默认值`。
  - `test_orders_kept_on_rescan`：选 `日/月/年` 后点"重新扫描"，`view.orders()` 仍是 `DAY_FIRST`，执行摘要不需要再选。
- [ ] **Step 2:** 运行上述测试 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`fix(v3): phase 3 carry-over (typed stale scan, write errors, kept orders, exit follow-up)`

---

### Task 2: EDC 配置与目标窗口

**Files:**
- Create:
  - `src/dataforge/tools/edc/__init__.py`
  - `src/dataforge/tools/edc/windows.py`
  - `src/dataforge/tools/edc/config.py`
- Test:
  - `tests/dataforge/test_edc_windows.py`
  - `tests/dataforge/test_edc_config.py`

**Interfaces:**
- Consumes：`config.legacy.load_section_with_legacy`、`legacy_file_candidates`，`ConfigStore`。
- Produces（`windows.py`，用 pywin32 的 `win32gui` / `win32process` / `win32api`，**不用** ctypes 的 `WNDENUMPROC`。这一点是裁定，spec 允许整体替换窗口枚举方式）：
  - `@dataclass(frozen=True) class WindowInfo: hwnd: int; title: str; process: str`。`process` 是小写的 exe 文件名，例如 `chrome.exe`。
  - `def find_target(target: WindowInfo, candidates: Sequence[WindowInfo]) -> WindowInfo | None`，纯函数，进程名比较不区分大小写。按下面的顺序匹配，第一条命中就返回：
    1. 候选中有 `hwnd` 相同、进程也相同的窗口 → 返回它；
    2. 同进程、`title` 完全相同的窗口 → 返回第一个；
    3. 同进程的窗口恰好只有 1 个 → 返回它；
    4. 都不满足 → 返回 `None`。
  - `def list_windows(exclude_pid: int | None = None) -> list[WindowInfo]`：
    - 只列出可见、有标题的顶层窗口；
    - `exclude_pid` 为 None 时，排除本进程（`os.getpid()`）的窗口。
  - `def window_at(x: int, y: int) -> WindowInfo | None`：
    - 按物理像素坐标取 `WindowFromPoint`，再用 `GetAncestor(…, GA_ROOT=2)` 得到顶层窗口；
    - 本进程的窗口或者出错时返回 None。
  - `def process_name(hwnd: int) -> str`：
    - 通过 `GetWindowThreadProcessId` 取进程 ID，用 `OpenProcess(0x0410, …)` 打开，再用 `GetModuleFileNameEx` 取 exe 路径，返回小写 basename；
    - 失败返回 `""`。
  - `def activate_window(hwnd: int) -> None`：
    - 窗口无效时抛 `DataForgeError("目标窗口已关闭")`；
    - 窗口最小化时先 `ShowWindow(hwnd, 9)`；
    - 调用 `SetForegroundWindow`。如果失败，先用 `win32api.keybd_event(0x12, 0, 0, 0)` 和 `keybd_event(0x12, 0, 2, 0)` 按一下 Alt 再重试 1 次；仍然失败就抛 `DataForgeError("无法激活目标窗口")`。
- Produces（`config.py`）：
  - 常量：
    - `CONFIG_SECTION = "edc_site_adder"`
    - `LEGACY_FILE_NAME = "edc_site_adder_config.json"`
    - `LEGACY_KEYS = frozenset({"max_loops", "click_positions"})`，与 v2 的 `_looks_like_legacy_payload` 一致
    - `STEP_KEYS = ("新建", "查找", "搜索框", "搜索", "选择", "ok", "确认")`
    - `DEFAULT_POSITIONS: dict[str, tuple[int, int]]`，照抄 v2：新建 (241, 212)、查找 (1137, 460)、搜索框 (817, 409)、搜索 (1040, 406)、选择 (699, 471)、ok (1121, 758)、确认 (1038, 728)
    - `MAX_LOOPS_RANGE = (1, 9999)`
    - `STEP_DELAY_RANGE = (0.1, 5.0)`
  - `@dataclass class EdcConfig`：
    - 字段：`max_loops: int = 100`、`step_delay: float = 0.3`、`click_positions: dict[str, tuple[int, int]]`（默认是 `DEFAULT_POSITIONS` 的拷贝，键顺序与 `STEP_KEYS` 相同）、`target_window: WindowInfo | None = None`。
    - `from_dict(raw) -> EdcConfig`：
      - `max_loops`：取值范围内的 int（排除 bool）才采用；
      - `step_delay`：int 或 float（排除 bool），在范围内才采用，转为 float；
      - 每个坐标：`x`、`y` 都是 int（排除 bool）才采用；
      - `target_window`：是 dict，且 `hwnd` 为 int、`title` 和 `process` 为 str 时才采用，否则为 None；
      - 坏值一律保留默认值，未知键和 `retry_count` 忽略。
    - `to_dict(self) -> dict`：返回 `{"max_loops", "step_delay", "click_positions": {key: {"x", "y"}}, "target_window": {"hwnd", "title", "process"} | None}`。
  - `def legacy_files() -> list[Path]`：返回 `legacy_file_candidates(LEGACY_FILE_NAME, Path(__file__).resolve().parents[3] / "gui" / "widgets")`。
  - `def load_config(store: ConfigStore, legacy: Sequence[Path] = ()) -> EdcConfig`
  - `def save_config(store: ConfigStore, config: EdcConfig) -> bool`

- [ ] **Step 1: 写失败测试**
  - `test_find_target_rules`：用 4 个候选覆盖以下情况：
    - 同 hwnd 且同进程；
    - hwnd 已失效但标题相同；
    - 只有一个同进程窗口；
    - 两个同进程窗口、标题都不同，返回 None；
    - 进程名大小写不同也能匹配；
    - hwnd 相同但进程不同，不算命中。
  - `test_list_windows_smoke`：
    - 创建一个可见的 `QWidget`，标题 `edc-probe`；
    - `list_windows(exclude_pid=-1)` 里有它，进程名以 `python` 开头、以 `.exe` 结尾；
    - `list_windows()` 默认排除本进程，所以不包含它。
  - `test_window_at_own_window_is_none`：取上面窗口中心点的物理坐标，`window_at` 返回 None。
  - `test_v2_section_values`：section `{"max_loops": 30, "retry_count": 3, "step_delay": 0.5, "click_positions": {"新建": {"x": 1, "y": 2}}}`。断言：
    - 这三个值被采用；
    - 其余坐标为默认值；
    - `save_config` 写出的内容不含 `retry_count`。
  - `test_bad_values_fall_back`：`max_loops` 取 0、`"abc"`、`True`，`step_delay` 取 0、9，坐标 `{"x": "1"}` → 全部取默认值。
  - `test_target_window_round_trip`，以及 `test_target_window_bad_shape`（坏格式 → None）。
  - `test_root_level_legacy`：配置文件顶层直接是 v2 的 `{"max_loops": 5, ...}` → 读到 5，配置文件不变。
  - `test_legacy_file_migrated`：传入临时旧文件，读到其中的值并写入 section，旧文件字节不变。
  - `test_legacy_files_candidates`：结果中包含 `src/gui/widgets/edc_site_adder_config.json` 和 `src/utils/edc_site_adder_config.json`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): EDC config migration and target window matching`

---

### Task 3: 逐行循环、整次运行汇总、标准样例、规则说明

**Files:**
- Create:
  - `src/dataforge/tools/edc/loop.py`
  - `tests/dataforge/edc_fakes.py`
  - `tests/golden/edc/make_fixtures.py` 及其生成的样例
  - `docs/tools/edc_site_adder.md`
- Modify:
  - `tests/dataforge/golden.py`
  - `docs/tools/README.md`
- Test:
  - `tests/dataforge/test_edc_loop.py`
  - `tests/dataforge/test_golden.py`（自动发现新样例）

**Interfaces:**
- Consumes：Task 2 的 `EdcConfig`、`STEP_KEYS`、`WindowInfo`。
- Produces（`loop.py`）：
  - `STEP_NAMES: tuple[str, ...]`，共 11 步：
    1. `读取单元格`
    2. `复制到剪贴板`
    3. `激活目标窗口`
    4. `点击【新建】`
    5. `点击【查找】`
    6. `点击【搜索框】并粘贴`
    7. `点击【搜索】`
    8. `点击【选择】`
    9. `点击【ok】`
    10. `点击【确认】`
    11. `切回 Excel 并选中下一行`
  - `@dataclass(frozen=True) class CellRef: workbook: str; sheet: str; row: int; column: int`，带两个方法：
    - `address(self) -> str`：例如列 1 行 5 → `"A5"`，列 27 → `"AA…"`；
    - `at_row(self, row: int) -> CellRef`。
  - 执行接口，用 `typing.Protocol` 定义：
    - `ExcelPort`：`selection() -> CellRef`、`text(cell: CellRef) -> str`、`focus(cell: CellRef) -> None`；
    - `ScreenPort`：`click(x: int, y: int) -> None`、`paste() -> None`；
    - `ClipboardPort`：`copy(text: str) -> None`；
    - `WindowPort`：`activate(target: WindowInfo) -> None`；
    - `StopFlag`：`is_set() -> bool`，`threading.Event` 满足这个接口。
  - `@dataclass class EdcPorts: excel; screen; clipboard; window; sleep: Callable[[float], None]`
  - `@dataclass(frozen=True) class RowDone: cell: CellRef; value: str`
  - `@dataclass(frozen=True) class RowStop: cell: CellRef; value: str; step: int; reason: str; by_user: bool`
    - `step` 从 1 开始，是 `STEP_NAMES` 的下标加 1；
    - 有 `step_name` 属性；
    - `step == 1` 表示这一行还没有任何动作。
  - `@dataclass class Segment: start: CellRef; end_row: int; done: list[RowDone]; stop: RowStop | None; reached: str`，`reached` 取 `"empty"`、`"limit"` 或 `"stopped"`。
  - `def run_segment(config: EdcConfig, ports: EdcPorts, start: CellRef | None, end_row: int | None, stop: StopFlag, progress: ProgressFn, cancel: CancelToken) -> Result`，返回的 `Result.data` 是 `Segment`。规则如下：
    - `config.target_window is None` → 抛 `DataForgeError("未设置目标窗口")`。
    - `start is None` → 用 `ports.excel.selection()` 取起点。它抛出的 `DataForgeError` 原样抛出，其他异常包装为 `DataForgeError(f"无法读取 Excel 选中的单元格：{exc}")`。
    - `end_row is None` → `start.row + config.max_loops`。只处理 `row < end_row` 的行。
    - 预先数总行数：从起点往下逐个读取 `text`，直到第一个空格子或 `end_row`。读取出错时，总数取 `end_row - start.row`。
    - 每一步执行前，依次检查：
      1. `cancel.raise_if_cancelled()`；
      2. `stop.is_set()` → `RowStop(by_user=True, reason="已按 ESC 停止")`，`reached="stopped"`。
    - 每一步出现 `Exception` 时：`RowStop(by_user=False, reason=_reason(exc))`，`reached="stopped"`。`_reason` 的规则：
      - 类名为 `FailSafeException` → `鼠标移到了屏幕角落，已触发安全停止`；
      - 其他情况 → `str(exc)`，为空时用类名。
    - 每一行的动作：
      1. `value = text(cell).strip()`，为空则 `reached="empty"` 并结束；
      2. `progress(i, total, f"Excel {addr}：{value}")`，`logger.info` 记一行；
      3. `copy(value)`、`sleep(0.1)`；
      4. `activate(target)`、`sleep(0.1)`；
      5. 按 `STEP_KEYS` 依次点击：`click(x, y)`；如果是【搜索框】，接着 `sleep(0.05)`、`paste()`；然后 `sleep(step_delay)`；
      6. `focus(cell.at_row(row + 1))`、`sleep(0.1)`；
      7. 记录 `RowDone`。
    - 循环走到 `end_row` → `reached="limit"`。
  - `class StopChoice(Enum): REDO = "redo"; SKIP = "skip"; END = "end"`
  - `@dataclass class EdcSession: first: CellRef; end_row: int; done: list[RowDone]; skipped: list[RowStop]; failed: list[RowStop]`，方法：
    - `@classmethod def begin(cls, segment: Segment) -> EdcSession`
    - `def absorb(self, segment: Segment) -> None`：把 `done` 追加进来。`begin` 已经包含首段的吸收。
    - `def resolve(self, stop: RowStop, choice: StopChoice) -> CellRef | None`：
      - REDO → 返回 `stop.cell`；
      - SKIP → 把这一行记入 `skipped`，返回下一行；下一行 `>= end_row` 时返回 None；
      - END → 返回 None，同时：除非 `stop.by_user and stop.step == 1`（这一行什么都没做），否则把这一行记入 `failed`。
    - `def to_result(self) -> Result`：
      - `stats = {"succeeded": n, "skipped": n, "failed": n}`；
      - 每个跳过的行：`warn(address, f"已跳过（第 {step} 步「{name}」：{reason}）")`；
      - 每个出错的行：`fail(address, f"出错（第 {step} 步「{name}」：{reason}）")`；
      - `data = self`。
    - `def done_lines(self) -> list[str]`：每个成功行一条 `f"{address} {value}"`。
- Produces（`tests/dataforge/edc_fakes.py`）：
  - `class FakePorts`：构造参数 `cells: dict[int, str]`（行号 → 文本，列固定为 A，工作簿 `Book1`，工作表 `Sheet1`）、`start_row: int`、`fail: list[dict] | None`、`esc_after: int | None`。
  - `.ports() -> EdcPorts`。
  - `.trace: list[str]`：每次调用追加一行。格式固定，标准样例依赖这个格式：
    - `excel.selection -> A2`
    - `excel.text A3`
    - `clipboard.copy SITE-1`
    - `window.activate`
    - `screen.click 241 212`
    - `screen.paste`
    - `excel.focus A4`
    - `sleep 0.3`
  - `fail = [{"call": "screen.click", "nth": 5, "message": "boom", "exc": "FailSafeException" | None}, ...]`：列表中的每一项各自生效，跨段累计计数。第 nth 次（从 1 开始计数）调用该动作时，抛出指定类名的异常（动态创建同名类）或 `RuntimeError`。
  - `esc_after = n`：动作序列长度达到 n 之后，`stop.is_set()` 返回 True。返回 `FakePorts.stop_flag()`。
- 标准样例（`tests/golden/edc/<case>/params.json` + `expected/trace.txt`，按字节比较）：
  - `params.json` 包含 `cells`、`start_row`、`max_loops`、`step_delay`、`fail`、`esc_after`、`choices`（例如 `["skip", "redo", "end"]`）。
  - golden 适配器 `_run_edc` 用 `FakePorts` 驱动 `run_segment` 和 `EdcSession`：
    - 每次停下时追加一行 `== stop {address} step {step}: {reason} -> {choice}`，并按 `choices` 依次选择，用完后取 `end`；
    - 下一段的 `esc_after` 只对第一段生效；
    - 结束后追加汇总：`succeeded {address} {value}`、`skipped {address} step {k}`、`failed {address} step {k}`。
  - 期望输出由 `make_fixtures.py` 里的字面值生成，共 4 个样例：
    - `basic_three_rows`：A2–A4 有值，A5 为空，`step_delay` 0.3；
    - `limit_and_whitespace`：值为 `" SITE-2 "`，`max_loops` 2；
    - `failure_skip_then_redo`：第 2 行第 5 次点击失败，选 skip；第 3 行模拟窗口激活失败，选 redo，重做后成功；
    - `esc_then_end`：`esc_after` 落在第 1 行点击中途，选 end。
- `docs/tools/edc_site_adder.md`，与语言无关，包含以下内容：
  - 11 个步骤及等待时间；
  - 起点和 `max_loops` 的含义：整次运行最多处理到起点行 + `max_loops` − 1，重做不额外占用次数；
  - 空单元格的判定（去掉首尾空格后为空）；
  - 停止条件、3 个选择、汇总规则（包括 END 时"未开始的行不计入出错"）；
  - 目标窗口的匹配顺序；
  - 配置键与迁移；
  - 动作序列的格式；
  - 原文照录 spec 中的限制："程序无法判断一次点击是否真正生效"。

- [ ] **Step 1: 写失败测试**（`test_edc_loop.py`，全部用 `FakePorts`，`sleep` 只记录不等待）
  - `test_three_rows_then_empty`：3 个 `RowDone`，`reached == "empty"`，各行动作顺序与 `STEP_NAMES` 一致，点击坐标与配置一致。
  - `test_whitespace_trimmed_and_blank_is_empty`：`" SITE "` 复制为 `SITE`；`"   "` 视为空，正常结束。
  - `test_limit`：`max_loops=2` 时只处理 2 行，`reached == "limit"`。
  - `test_click_failure_stops_row`：失败点在第 2 行【查找】，得到 `RowStop(step=5, by_user=False, reason="boom")`；`done` 只有第 1 行；之后不再发生任何动作。
  - `test_failsafe_reason`：`exc` 为 `FailSafeException` 时，reason 等于固定文字。
  - `test_window_missing_stops_at_step_3`：`window.activate` 抛 `DataForgeError("找不到目标窗口：EDC（chrome.exe）")` → `step == 3`，reason 为原消息。
  - `test_esc_soft_stop`：`by_user is True`，`reached == "stopped"`，没有抛 `Cancelled`。
  - `test_hard_cancel_raises`：`CancelToken` 已取消 → 抛 `Cancelled`。
  - `test_no_target_window_raises`、`test_selection_error_wrapped`：selection 抛 `RuntimeError` → `DataForgeError`，消息以 `无法读取 Excel 选中的单元格` 开头。
  - `test_explicit_start_skips_selection`：传入 `start` 时不调用 `excel.selection`。
  - `test_session_resolve`：覆盖 REDO、SKIP、SKIP 到 `end_row`、END（`step` 大于 1 → failed；`by_user` 且 `step` 为 1 → 不记录），以及 `to_result` 的 stats、警告和错误文字。
  - `test_address`：(1, 5) → `A5`，(27, 3) → `AA3`，(52, 1) → `AZ1`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现 `loop.py`、`edc_fakes.py`、golden 适配器，运行 `make_fixtures.py` 生成样例，写规则说明。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS（新增的 4 个 golden 样例都被发现）
- [ ] **Step 5:** Commit：`feat(v3): EDC row loop, session summary, golden traces and rules doc`

---

### Task 4: 真实执行实现（`live.py`）

**Files:**
- Create：`src/dataforge/tools/edc/live.py`
- Test：`tests/dataforge/test_edc_live.py`

**Interfaces:**
- Consumes：Task 2 的 `find_target`、`list_windows`、`activate_window`；Task 3 的执行接口和 `EdcPorts`。
- Produces：
  - `@contextmanager def open_live_ports() -> Iterator[EdcPorts]`：
    - 进入时调用 `pythoncom.CoInitialize()`，退出时（`finally`）先释放所有 COM 引用（设为 None），再调用 `CoUninitialize()`。
    - 用 `win32com.client.GetActiveObject("Excel.Application")` 连接已打开的 Excel，**不用** `Dispatch`，避免另开一个看不见的 Excel。连接失败（`pywintypes.com_error`）时抛 `DataForgeError("未检测到正在运行的 Excel，请先打开 Excel 并选中第一个站点所在的单元格")`。
    - pyautogui 和 pyperclip 在函数内部导入。模块顶层只允许导入标准库和 `dataforge`。
  - `LiveExcel`：
    - `selection()`：没有选区或选区没有 `Cells` → 抛 `DataForgeError("请先在 Excel 中选中第一个站点所在的单元格")`；否则取左上角单元格，`CellRef(workbook=cell.Worksheet.Parent.Name, sheet=cell.Worksheet.Name, row=cell.Row, column=cell.Column)`。
    - `text(cell)`：`Workbooks(wb).Worksheets(sheet).Cells(row, col).Text`。
    - `focus(cell)`：依次 `workbook.Activate()`、`sheet.Activate()`、`xl.ActiveWindow.Activate()`、`Cells(row, col).Select()`。
  - `LiveScreen`：
    - `click(x, y)` → `pyautogui.click(x, y)`；
    - `paste()` → `pyautogui.hotkey("ctrl", "v")`；
    - 保留 pyautogui 默认的 `FAILSAFE` 和 `PAUSE`。
  - `LiveClipboard`：`copy` → `pyperclip.copy`。
  - `LiveWindow.activate(target)`：
    - `find_target(target, list_windows())` 为 None → 抛 `DataForgeError(f"找不到目标窗口：{target.title}（{target.process}）")`；
    - 否则调用 `activate_window(match.hwnd)`。
  - `sleep`：`time.sleep`。

- [ ] **Step 1: 写失败测试**
  - `test_import_is_light`：在子进程里 `import dataforge.tools.edc.live`，之后 `"pyautogui" not in sys.modules`，`"pyperclip" not in sys.modules`。
  - `test_no_excel_message`：patch `GetActiveObject` 抛 `pywintypes.com_error`，`with open_live_ports()` 抛出对应的 `DataForgeError`；`CoInitialize` 和 `CoUninitialize` 各被调用 1 次（patch `pythoncom`）。
  - `test_uninitialize_on_body_error`：with 块内抛 `RuntimeError`，`CoUninitialize` 仍被调用。
  - `test_live_window_missing`：patch `list_windows` 返回 `[]`，抛出的消息为 `找不到目标窗口：EDC（chrome.exe）`。
  - `test_live_window_activates_match`：patch `activate_window`，收到的是匹配到的 hwnd。
  - `test_live_excel_selection`：用 `SimpleNamespace` 假 COM 对象，验证 `CellRef` 各字段，以及 `Selection is None` 时的错误消息。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): live Excel/screen/window ports for EDC`

---

### Task 5: 系统钩子与 ToolPage 续跑日志

**Files:**
- Create：
  - `src/dataforge/ui/pages/edc/__init__.py`
  - `src/dataforge/ui/pages/edc/hooks.py`
- Modify：`src/dataforge/ui/components/tool_page.py`
- Test：
  - `tests/dataforge/test_edc_hooks.py`
  - `tests/dataforge/test_tool_page.py`

**Interfaces:**
- Produces：
  - `class EscHook(QObject)`：
    - 信号 `pressed = Signal()`；
    - 构造参数 `__init__(self, backend: Any = None, parent: QObject | None = None)`，`backend` 为 None 时在 `start()` 里才 `import keyboard` 作为后端；
    - `start()`：没有句柄时 `self._handle = backend.on_press_key("esc", self._callback)`；
    - `stop()`：有句柄时 `backend.unhook(self._handle)`，然后把句柄置为 None，可重复调用；
    - `is_active() -> bool`；
    - `_callback(event)` 只做一件事：`self.pressed.emit()`；
    - 任何地方都不调用 `unhook_all`。
  - `class MouseClickHook(QObject)`：
    - 信号 `clicked = Signal(int, int)`，坐标为物理像素；
    - 默认后端是 `mouse` 模块；
    - `start()` 调用 `backend.hook(cb)`，`stop()` 调用 `backend.unhook(handle)`；
    - 回调里只在 `getattr(event, "event_type", None) == "down"` 且 `getattr(event, "button", None) == "left"` 时，读取 `backend.get_position()` 并发出 `clicked`，不做其他事。
  - `ToolPage.keep_log_for_next_start(self, separator: str) -> None`：下一次本页任务开始时（`_on_started`），不清空结果区，改为 `append_log(separator)`，然后标记复位。现有的重跑逻辑不变。

- [ ] **Step 1: 写失败测试**（假后端只记录 `on_press_key` / `unhook` / `hook` 调用，并保存回调）
  - `test_esc_hook_register_once_and_unhook_own_handle`：`start()` 两次只注册 1 次；`stop()` 用同一个句柄注销；再次 `stop()` 不再调用；假后端没有 `unhook_all` 属性，测试也不报错。
  - `test_esc_callback_from_thread_reaches_main`：在 `threading.Thread` 中调用保存的回调，`wait_until` 收到 `pressed`，且槽函数运行在主线程（槽内记录 `QThread.currentThread() is qapp().thread()`）。
  - `test_mouse_hook_filters_events`：up 事件、右键都不发信号；左键 down 时发出 `clicked(10, 20)`（假后端 `get_position` 返回这个值）。
  - `test_keep_log_for_next_start`：`keep_log_for_next_start("—— 继续 ——")` 后提交任务，结束后日志页同时含旧行和分隔行；再提交一次，日志被清空。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): run-scoped ESC/mouse hooks and continued run log`

---

### Task 6: 录制浮层、回放标记、对话框

**Files:**
- Create：
  - `src/dataforge/ui/pages/edc/overlay.py`
  - `src/dataforge/ui/pages/edc/dialogs.py`
- Test：`tests/dataforge/test_edc_overlay.py`

**Interfaces:**
- Consumes：Task 5 的 `EscHook`、`MouseClickHook`；Task 3 的 `RowStop`、`StopChoice`、`STEP_NAMES`；Task 2 的 `WindowInfo`。
- Produces（`overlay.py`）：
  - 坐标换算 `def physical_to_logical(x: int, y: int) -> QPoint`：遍历 `QGuiApplication.screens()`，对每个屏幕取 `g = s.geometry()`、`d = s.devicePixelRatio()`：
    - 物理范围是 `QRect(g.x(), g.y(), round(g.width() * d), round(g.height() * d))`；
    - 点落在这个范围内时，返回 `QPoint(g.x() + round((x - g.x()) / d), g.y() + round((y - g.y()) / d))`；
    - 没有屏幕命中时，按主屏的 `d` 换算。
    - 这是裁定：v2 在缩放 150% 时标记位置和"忽略顶部区域"都会偏。
  - `class RecordingOverlay(QWidget)`：
    - 信号 `captured = Signal(str, int, int)`（步骤键、物理坐标）、`finished = Signal()`、`cancelled = Signal()`；
    - 构造参数 `__init__(self, steps: Sequence[str], mouse_hook: MouseClickHook, esc_hook: EscHook)`；
    - 窗口：`FramelessWindowHint | WindowStaysOnTopHint | Tool`，背景透明；
    - 位置：占满主屏 `availableGeometry()` 顶部，高度 `BAR_HEIGHT = 60`；
    - 绘制：`paintEvent` 用 `QColor(15, 23, 42, 210)` 填充；提示文字用 `QLabel`，通过调色板设为 `QColor(255, 255, 255)`；
    - 按钮：`PrimaryPushButton("开始")`、`PushButton("取消（ESC）")`。
    - 流程：
      1. `show()` 时启动 `esc_hook`，提示 `请切换到 EDC 页面，准备好后点击「开始」（共 {n} 步）`；
      2. 点"开始"后隐藏开始按钮，提示 `请点击【{key}】（{i}/{n}）`，并用 `QTimer.singleShot(300, mouse_hook.start)` 延后启动鼠标钩子，避免把"开始"这一下记进去；
      3. 收到 `mouse_hook.clicked(x, y)`（主线程槽）：换算成逻辑坐标；如果落在 `self.geometry().adjusted(0, 0, 0, 10)` 内就忽略（100% 缩放时即顶部 70 px）；否则 `captured.emit(key, x, y)`，推进到下一步；
      4. 全部完成：停止两个钩子，`finished.emit()`，`close()`；
      5. 按 ESC 或点"取消"：停止两个钩子，`cancelled.emit()`，`close()`；
      6. `closeEvent` 停止两个钩子（可重复调用）。
  - `class FlashMarker(QWidget)`：
    - 构造参数 `(label: str, x: int, y: int)`，x、y 为物理坐标，内部换算成逻辑坐标；
    - 无边框、置顶、Tool 窗口，不抢焦点，背景透明；
    - 绘制：圆半径 20，填充 `QColor(220, 38, 38, 180)`，描边和十字线 `QColor(255, 255, 255, 220)`，标签为白色；
    - 尺寸由字体宽度计算。
  - 常量 `REPLAY_INTERVAL_MS = 600`、`REPLAY_VISIBLE_MS = 1500`。
  - `def schedule_replay(points: Sequence[tuple[str, int, int]]) -> list[FlashMarker]`：第 i 个标记在 `i * 600` ms 时 `show`，在 `i * 600 + 1500` ms 时 `close`，两者都用 `QTimer.singleShot`。调用方需要持有返回的列表。
- Produces（`dialogs.py`，都是 `MessageBoxBase` 子类）：
  - `class StopDialog(MessageBoxBase)`：
    - 构造参数 `(parent, stop: RowStop)`；
    - 标题 `StrongBodyLabel`：`by_user` 为真时写 `已停止`，否则写 `处理出错`；
    - 正文：`f"Excel {stop.cell.address()}（{stop.value}）在第 {stop.step} 步「{stop.step_name}」停止：{stop.reason}"`；
    - 提醒（`CaptionLabel`）：`重做前请先在 EDC 中确认这一行是否已经添加过，避免重复添加。`；
    - 按钮：`yesButton` 写 `重做本行`；在 `buttonLayout` 的 yes 与 cancel 之间插入 `PushButton("跳到下一行")`；`cancelButton` 写 `结束`；
    - `choice() -> StopChoice`：默认 `END`，关闭对话框也是 `END`。
  - `def ask_stop_choice(parent: QWidget, stop: RowStop) -> StopChoice`：执行对话框，用完 `deleteLater`。
  - `class WindowPickerDialog(MessageBoxBase)`：
    - 构造参数 `(parent, windows: Sequence[WindowInfo], current: WindowInfo | None)`；
    - 标题 `选择目标窗口`；
    - `ListWidget` 每行显示 `f"{title} — {process}"`，有 `current` 时预选与它 `find_target` 匹配的那一行；
    - 没有选中时 yes 按钮不可用；
    - `selected() -> WindowInfo | None`。
  - `def pick_window(parent, windows, current) -> WindowInfo | None`：取消时返回 None。

- [ ] **Step 1: 写失败测试**（`MouseClickHook` / `EscHook` 用 Task 5 的假后端，测试直接 `emit` 信号）
  - `test_physical_to_logical_identity`：dpr 为 1 时坐标不变。
  - `test_physical_to_logical_scaled`：patch `QGuiApplication.screens` 返回 geometry `(0, 0, 1280, 720)`、dpr 1.5 的假屏幕，(300, 150) → (200, 100)。
  - `test_recording_sequence`：3 步；点"开始"（patch `QTimer.singleShot` 让它立即执行）；发出顶部区域内的点击 → 忽略；再发出 3 次点击 → 依次收到 3 个 `captured`，然后收到 `finished`；两个钩子都已 `stop`。
  - `test_recording_esc_cancels`：发出 `esc_hook.pressed` → 收到 `cancelled`，浮层关闭，钩子停止。
  - `test_overlay_has_no_stylesheet`：浮层及其子控件的 `styleSheet()` 都为空。
  - `test_replay_schedule`：patch `QTimer.singleShot` 记录 `(ms, fn)`；3 个点 → show 的时间为 0/600/1200，close 的时间为 1500/2100/2700。
  - `test_stop_dialog_texts_and_choices`：正文含 `A3`、`第 5 步「点击【查找】」`、reason；`by_user` 时标题为 `已停止`；点"跳到下一行" → `SKIP`；点 yes → `REDO`；点 cancel → `END`。
  - `test_window_picker`：预选与 `current` 匹配的行；未选中时 yes 不可用；选第 2 行后 `selected()` 等于第 2 个窗口。
  - 每个测试结束后对创建的窗口调用 `drain_deleted`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): EDC recording overlay, replay markers and dialogs`

---

### Task 7: EDC 页面

**Files:**
- Create：`src/dataforge/ui/pages/edc/page.py`
- Modify：`src/dataforge/ui/registry.py`
- Test：
  - `tests/dataforge/test_edc_page.py`
  - `tests/dataforge/test_registry_theme_layout.py`（登记相关断言）

**Interfaces:**
- Consumes：
  - Task 1：`submit_job_when_idle`；
  - Task 2：`load_config`、`save_config`、`legacy_files`、`EdcConfig`、`DEFAULT_POSITIONS`、`STEP_KEYS`、`find_target`、`list_windows`、`window_at`；
  - Task 3：`run_segment`、`EdcSession`、`StopChoice`；
  - Task 4：`open_live_ports`；
  - Task 5：`EscHook`、`MouseClickHook`、`keep_log_for_next_start`；
  - Task 6：`RecordingOverlay`、`schedule_replay`、`ask_stop_choice`、`pick_window`。
  - **以上名字全部用 `from … import name` 导入到 `page.py` 模块级，测试通过 patch `dataforge.ui.pages.edc.page.<name>` 替换。**
- Produces：
  - `registry`：`ToolSpec(id="edc", name="EDC 站点添加", description="录制点击位置，从 Excel 逐行回放", group=ToolGroup.BUSINESS, icon=FluentIcon.ROBOT, page="dataforge.ui.pages.edc.page:EdcPage")`。
  - `class EdcPage(ToolPage)`：`USES_CONFIG = True`；`__init__(self, spec, runner, parent=None, config: ConfigStore | None = None)`；加载 `load_config(config, legacy_files())`。
- 页面结构（属性名供测试使用）：
  1. **`目标窗口`**：
     - `target_label`：显示 `{title} · {process}`；未设置时显示 `未设置（录制时会自动记住你点击的窗口）`；
     - `pick_window_button`：`选择窗口…`。
  2. **`点击位置`**：
     - 一个 `ResponsiveForm`，7 行，标签为 `1. 新建` … `7. 确认`；
     - 每行的字段是 X `SpinBox`、Y `SpinBox`（范围 −32768–32767）加一个 `PushButton("重录")`；
     - 这些控件存在 `position_fields: dict[str, tuple[SpinBox, SpinBox, PushButton]]` 里；
     - 下方按钮：`record_button` `一键录制`、`replay_button` `回放测试`、`restore_defaults_button` `恢复默认值`。
  3. **`运行参数`**：
     - `max_loops_spin`：`最多处理行数`，1–9999；
     - `step_delay_spin`：`DoubleSpinBox`，`每步间隔（秒）`，0.1–5.0，步长 0.1。
  4. **`使用说明`**：若干条 `BodyLabel`（自动换行），内容包括：
     - 前提：Excel 已打开并选中第一个站点；浏览器已打开 EDC 页面；
     - 运行期间不要操作鼠标和键盘，按 ESC 停止；
     - 限制：程序无法判断点击是否真正生效。
- 行为：
  - **自动保存**：任何字段变化都立即更新配置并 `save_config`；保存失败时 `InfoBar.warning("配置未保存", "请检查配置文件权限")`。程序自己设置控件值时用 `QSignalBlocker`，避免触发保存。
  - **主按钮**：文字为 `开始处理`；`current_job_kind()` 返回 `"edc"`。
  - **`build_job()`**：
    - 未设置目标窗口 → `InfoBar.warning("请先设置目标窗口", "请先“一键录制”，或点击“选择窗口…”指定 EDC 所在的浏览器窗口")`，返回 None；
    - `find_target(target, list_windows())` 为 None → `InfoBar.warning("找不到目标窗口", f"{title}（{process}）未打开，请重新选择窗口")`，返回 None；
    - 否则清空会话，返回 `_segment_job(None, None)`。
  - **`_segment_job(start, end_row)`**：
    - 新建 `threading.Event` 存到 `self._stop_event`；
    - 用 `dataclasses.replace` 拷贝当前配置；
    - 返回的任务函数为 `with open_live_ports() as ports: return run_segment(cfg, ports, start, end_row, event, progress, token)`。
  - **ESC 钩子**：
    - `runner.started` 收到本页 id 时调用 `self.esc_hook.start()`；
    - `esc_hook.pressed` → 如果本页任务正在运行，就设置 `_stop_event`，并在日志里写 `已按 ESC，当前步骤结束后停止`；
    - `on_aux_finished`、`_on_failed`、`_on_cancelled` 的**第一件事**都是调用 `self.esc_hook.stop()`。
  - **取消按钮**：覆盖 `_on_cancel_requested`，本页任务运行时设置 `_stop_event`（软停止），**不**调用 `runner.cancel()`。
  - **`on_aux_finished("edc", result)`**：
    1. `seg = result.data`；没有会话时 `EdcSession.begin(seg)`，否则 `absorb(seg)`。
    2. 如果 `seg.stop` 不为空：
       - 先 `self.window().showNormal(); raise_(); activateWindow()`；
       - `choice = ask_stop_choice(self.window(), seg.stop)`，`nxt = session.resolve(seg.stop, choice)`；
       - `nxt` 不为空时，调用 `keep_log_for_next_start(f"—— 从 {nxt.address()} 继续 ——")`，再 `submit_job_when_idle(self._segment_job(nxt, session.end_row), "edc")`，然后返回。
    3. 结束会话：`show_result(session.to_result())`，日志里追加 `成功的行：` 和 `done_lines()`。然后按下面的规则提示：
       - 成功数大于 0，且跳过和出错都是 0 → `InfoBar.success("完成", f"成功 {n} 行")`；
       - 三项都是 0 → `InfoBar.warning("没有处理任何行", "选中的单元格为空")`；
       - 其他情况 → `InfoBar.warning("已结束", f"成功 {a} 行，跳过 {b} 行，出错 {c} 行")`。
       - 最后清空会话。
  - **`_on_failed` / `_on_cancelled`**（本页任务）：停止钩子，调用 `super()`。如果有会话，在结果区显示它的 `to_result()`，然后清空会话。
  - **录制**：
    - `record_button` → `_start_recording(STEP_KEYS)`；某一行的"重录" → `_start_recording((key,))`；
    - 每次录制新建一组 `MouseClickHook`、`EscHook` 和 `RecordingOverlay`，主窗口 `showMinimized()`，然后 `overlay.show()`；
    - 收到 `captured(key, x, y)`：更新对应的 SpinBox 和配置。如果这是本次录制的第一下，且 `window_at(x, y)` 不为 None，就设为目标窗口并更新 `target_label`。然后保存；
    - 收到 `finished` → 主窗口 `showNormal()` + `activateWindow()`，`InfoBar.success("录制完成", "")`；
    - 收到 `cancelled` → 同样恢复主窗口，`InfoBar.info("已取消录制", "")`；
    - 两种情况都把 `self._overlay` 置为 None。
  - **回放测试**：`self._markers = schedule_replay([(f"{i}. {key}", x, y), ...])`。
  - **选择窗口**：`pick_window(self.window(), list_windows(), current)` 返回的结果不为 None 时，设为目标窗口并保存，更新标签。
  - **恢复默认值**：坐标、`max_loops`、`step_delay` 恢复默认，目标窗口保留；然后保存，`InfoBar.success("已恢复默认值", "目标窗口未改变")`。
  - **`set_inputs_locked(locked)`**：锁定上面所有按钮和输入框。
  - **最近使用相关**：`capture_state()` 返回 `{}`，`restore_state()` 返回 `[]`，`summary()` 返回 `""`。

- [ ] **Step 1: 写失败测试**（准备工作如下）
  - 使用临时 `ConfigStore`；
  - patch `legacy_files` → `[]`；
  - patch `open_live_ports` → 用 `contextlib.nullcontext(fake.ports())`，`fake` 来自 `edc_fakes.FakePorts`；
  - patch `list_windows` → `[target]`；
  - patch `ask_stop_choice`，按顺序返回预设的选择；
  - patch `InfoBar.*`；
  - patch `EscHook`，换成用假后端的子类；
  - 用 `wait_until` 等待会话结束（`page._session is None` 且 runner 空闲）。

  测试项：
  - `test_registered_in_business_group`：id、名称、组、图标都正确，排在 masking 之后，`load_page_class` 可以导入。
  - `test_full_run_success`：3 行全部成功 → `InfoBar.success` 收到 `("完成", "成功 3 行")`；结果区显示 `succeeded: 3`；`run_succeeded` 没有发出；ESC 假后端恰好注册 1 次、注销 1 次。
  - `test_failure_skip_continues_and_keeps_log`：第 2 行点击失败，选 SKIP → 第 3 行成功。断言：
    - `ask_stop_choice` 被调用 1 次；
    - 最终 InfoBar 为 `已结束`，内容 `成功 2 行，跳过 1 行，出错 0 行`；
    - 日志里同时有第 1 段的 `A2` 行和 `—— 从 A4 继续 ——`；
    - 第二段以显式起点运行，没有再调用 `excel.selection`。
  - `test_redo_then_end`：先选 REDO，第二段同一行再次失败后选 END → `出错 1 行`。
  - `test_cancel_button_is_soft_stop`：`FakePorts` 在第一次点击时阻塞在 `threading.Event` 上；测试点击取消按钮后放行。断言：
    - 对话框收到 `by_user=True` 的 stop；
    - `InfoBar.info("已取消", …)` 没有被调用。
  - `test_esc_signal_sets_stop`：与上一项相同的阻塞方式，改为发出 `page.esc_hook.pressed` → 对话框收到 `by_user=True`。
  - `test_esc_outside_run_ignored`：没有任务运行时发出 `pressed`，不报错，不改变任何状态；ESC 假后端没有注册。
  - `test_no_target_window_blocks_start`、`test_target_missing_blocks_start`：没有提交任务，各自的警告标题正确。
  - `test_excel_error_ends_cleanly`：patch `open_live_ports` 抛 `DataForgeError("未检测到正在运行的 Excel…")` → `InfoBar.error` 显示该消息，没有遗留会话，钩子已注销。
  - `test_recording_updates_positions_and_target`：patch `RecordingOverlay`，换成测试里的假浮层，它可以手动发出 `captured` / `finished`；patch `window_at` 返回 `WindowInfo(7, "EDC", "chrome.exe")`。录制 2 步后断言：
    - SpinBox 值已更新；
    - 配置文件中出现新坐标和 `target_window`；
    - `target_label` 含 `EDC`；
    - 主窗口的 `showMinimized` 和 `showNormal` 都被调用过（patch 为记录调用）。
  - `test_single_step_rerecord_only_that_step`。
  - `test_v2_config_shown`：配置中预置 `{"edc_site_adder": {"max_loops": 30, "retry_count": 2, "click_positions": {"ok": {"x": 5, "y": 6}}}}` → 页面显示 30 和 (5, 6)；改动任一字段后，配置文件不含 `retry_count`。
  - `test_restore_defaults_keeps_target`。
  - `test_pick_window_sets_target`：patch `pick_window` 返回一个窗口 → 目标窗口已设置并保存。
  - `test_locked_while_running`、`test_narrow_mode_compacts_forms`。
  - 每个测试结束关闭页面并 `drain_deleted`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现；在 registry 中登记。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` 连续 3 次 → 全部 PASS，无挂起
- [ ] **Step 5:** Commit：`feat(v3): EDC site adder page`

---

### Task 8: 阶段验收

- [ ] **Step 1:** `.venv/Scripts/python.exe -m pytest tests -q` 连续 3 次 → 全部 PASS，单次不超过 120 秒。
- [ ] **Step 2:** 禁用模式检查：`grep -rnE "setStyleSheet|#[0-9a-fA-F]{6}|setFixedWidth|processEvents|DontUseNativeDialog|import pandas|print\(|unhook_all" src/dataforge` → 无输出。
- [ ] **Step 3:** 请作者手动验收（`.venv\Scripts\python -m dataforge`，打开"业务 → EDC 站点添加"）：
  1. **v2 配置**：在用过 v2 的电脑上，页面显示 v2 保存的坐标和最多处理行数；首次点"开始处理"时提示先设置目标窗口。
  2. **一键录制**：主窗口最小化，顶部出现提示条；点"开始"后依次点击 7 个按钮，录完自动回到主窗口，坐标和目标窗口（浏览器标题 · 进程名）已更新。录制中按 ESC 能取消。用"重录"单独录一步，只改这一步。
  3. **回放测试**：7 个红色标记按顺序闪过，位置与录制的按钮重合。如果显示器缩放不是 100%，重点检查这一项。
  4. **正常运行**：在 Excel 中选中第一个站点，点"开始处理"，逐行添加；遇到空单元格停止，提示"成功 N 行"。
  5. **出错停止**：运行中按 ESC，弹出"已停止"对话框，写明行和步骤。分别试"跳到下一行"、"重做本行"、"结束"，最后的汇总与选择一致；日志从头到尾保留。
  6. **窗口和 Excel 异常**：关闭浏览器后运行，在第 3 步停下，原因是"找不到目标窗口"。关闭 Excel 后运行，提示"未检测到正在运行的 Excel…"。
  7. **ESC 不残留**：运行结束后在其他程序里按 ESC，DataForge 没有任何反应。
- [ ] **Step 4:** 新建 `docs/superpowers/plans/2026-10-29-dataforge-v3-phase4-carryover.md`，记录裁定与遗留项，并写明阶段 5 的注意事项：打包时需要收集 `mouse._winmouse`、`keyboard` 的 Windows 后端、`win32com` 和 `pythoncom`。Commit：`docs(v3): record phase 4 rulings and carry-over items`
