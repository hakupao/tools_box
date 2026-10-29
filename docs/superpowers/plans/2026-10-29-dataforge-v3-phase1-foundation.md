# DataForge Studio v3 · 阶段 1：地基与外壳 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在新包 `src/dataforge/` 中搭好 v3 的公共地基（结果/进度/取消、输出路径、配置、最近使用、日志、后台任务）和界面外壳（主题跟随系统、分组侧边栏、主页、设置页、响应式工具页骨架），并用"日期转换"和"全角转半角"两个工具端到端跑通，含标准样例对照测试。

**Architecture:** v3 代码放在独立包 `src/dataforge/`，与 v2（`src/gui`、`src/utils`）并存，直到阶段 5 删除 v2。后端（`core`/`fileio`/`config`/`tools`）不导入 Qt；界面（`ui`）通过一个全局 `JobRunner`（QThread + 信号）运行后端函数 `fn(progress, cancel) -> Result`。所有工具在 `ui/registry.py` 一处登记。

**Tech Stack:** Python ≥3.11（本机实测只有 3.13），PySide6 ≥6.8，PySide6-Fluent-Widgets ≥1.7（当前 1.11.3），pandas ≥2.2.3，openpyxl ≥3.1.5，platformdirs，unittest 风格测试 + pytest 运行器。

**Spec:** `docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md`

## 总路线图（每个阶段单独成计划，完成后程序都可运行）

| 阶段 | 内容 | 计划文件 |
|---|---|---|
| **1（本计划）** | 地基、外壳、主页、设置、日期转换、全角转半角、标准样例框架 | 本文件 |
| 2 | 统一编码识别（含歧义选择界面，带"本批其余文件也用此编码"勾选；实测 `テスト医師` 等常见日文与多数中文在 cp932/GBK 下都能解码，歧义会较常见）、CSV 读写；格式转换（4 种模式）、工作表拆分（与 XLSX→CSV 共用）、获取字段 | 阶段 1 完成后编写 |
| 3 | 数据模糊化：统一日期模块扩展、Profile 迁移、扫描/执行、歧义日期列选择、页面 | 同上 |
| 4 | EDC 站点添加：可注入执行器、目标窗口记忆、失败即停三选一、线程安全录制浮层 | 同上 |
| 5 | 删除 v2 代码与依赖、打包脚本与 .spec 改为 v3 入口、重写 UI 规范/README/CHANGELOG/AGENTS、版本 3.0.0 | 同上 |

## Global Constraints

- 新代码全部在 `src/dataforge/`；本阶段**不修改、不删除** v2 的 `src/gui`、`src/utils`，v2 仍可用 `python src/main.py` 运行。
- 后端模块（`dataforge.core` / `dataforge.fileio` / `dataforge.config` / `dataforge.tools`）禁止导入 PySide6 / qfluentwidgets；禁止 `print`；用 `logging.getLogger(__name__)`。
- 界面禁止：手写颜色 hex、`setStyleSheet`、QSS 字符串、`setTextColor(x, x)` 同值、`AA_DontUseNativeDialogs`、`DontUseNativeDialog`、DWM 标题栏补丁、`QApplication.processEvents()`、固定像素宽度（`setFixedWidth` 仅允许用于图标尺寸）。
- 主题默认 `Theme.AUTO`；开启 Mica（`setMicaEffectEnabled(True)`）；使用原生文件对话框。
- CSV 写出一律 `encoding="utf-8-sig"`；不覆盖原文件，除非用户勾选"覆盖原文件"并二次确认。
- 同名输出自动加 `_1`、`_2`……
- 全局同一时间只运行一个任务。
- 窗口最小宽度 640 px；布局断点：窗口宽 ≥1100 为 WIDE，750–1099 为 MEDIUM，<750 为 NARROW。
- 配置文件：`platformdirs.user_config_dir("dataforge_studio", appauthor=False, roaming=False)/dataforge_studio_config.json`；环境变量 `DATAFORGE_STUDIO_CONFIG_PATH`、`TOOLS_BOX_CONFIG_PATH` 可覆盖；新文件不存在时读取旧 `tools_box/tools_box_config.json`，写入总是新路径。
- 测试：`unittest.TestCase` 风格，放在 `tests/dataforge/`；Qt 测试设置 `QT_QPA_PLATFORM=offscreen`。
- 运行全部 v3 测试：`python -m pytest tests/dataforge -q`
- 提交信息结尾加：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

1. **输出位置不可写或目标文件被 Excel 占用**（PermissionError）→ 该文件记入 `Result.errors`，批次继续处理下一个文件，界面不崩溃。（测试见 Task 12）
2. **任务运行中关闭窗口** → 先取消并等待线程结束，不出现 "QThread: Destroyed while thread is still running"。（测试见 Task 6 `test_shutdown_cancels_and_waits`）
3. **配置文件损坏或无法写入** → 损坏时备份为 `.corrupt-<时间戳>.bak` 后用默认值；写入失败返回 `False` 并记日志，不抛异常。（测试见 Task 4）
4. **"最近使用"里有已不存在的工具或文件** → 未知工具的记录不显示；文件缺失时只恢复参数并提示。（测试见 Task 11、Task 12）
5. **运行中切换主题或切换页面** → 不崩溃，任务继续，其他工具主按钮显示被占用。（测试见 Task 10 冒烟测试）

---

## 文件结构

```
pyproject.toml                         新增：包元数据、src 布局、pytest 配置
requirements.txt                       修改：适配 Python 3.13 的版本下限
requirements-dev.txt                   新增：pytest
.gitignore                             修改：加入 .superpowers/
src/dataforge/__init__.py              __version__
src/dataforge/__main__.py              python -m dataforge
src/dataforge/app.py                   main()：日志、主题、窗口
src/dataforge/core/errors.py           异常类型
src/dataforge/core/result.py           Result / FileIssue
src/dataforge/core/progress.py         ProgressFn / CancelToken
src/dataforge/core/logs.py             日志初始化、日志目录
src/dataforge/fileio/paths.py          输出路径规划、输入文件展开
src/dataforge/config/store.py          ConfigStore（分区、原子写、损坏备份、旧路径兼容）
src/dataforge/config/recent.py         RecentStore（最近使用）
src/dataforge/dates.py                 日期标准化（本阶段：to_iso8601）
src/dataforge/tools/date_convert.py    日期转换后端
src/dataforge/tools/width_convert.py   全角转半角后端
src/dataforge/ui/jobs.py               JobRunner（全局单任务 + 日志转发）
src/dataforge/ui/registry.py           ToolSpec / ToolGroup / TOOLS
src/dataforge/ui/theme.py              主题模式应用与系统监听
src/dataforge/ui/layout.py             LayoutMode 与断点函数
src/dataforge/ui/components/responsive_form.py
src/dataforge/ui/components/file_input.py
src/dataforge/ui/components/run_bar.py
src/dataforge/ui/components/result_panel.py
src/dataforge/ui/components/tool_page.py   ToolPage 基类
src/dataforge/ui/shell.py              MainWindow
src/dataforge/ui/home.py               HomePage
src/dataforge/ui/settings.py           SettingsPage
src/dataforge/ui/pages/date_convert_page.py
src/dataforge/ui/pages/width_convert_page.py
tests/dataforge/__init__.py            设置 QT_QPA_PLATFORM=offscreen
tests/dataforge/qt_helpers.py          qapp()、wait_until()
tests/dataforge/golden.py              标准样例发现、适配器、目录比较
tests/dataforge/test_*.py
tests/golden/<tool_id>/<case>/{params.json,input/,expected/}
tests/golden/width_convert/make_fixtures.py
docs/tools/README.md                   规则说明与标准样例格式
docs/tools/date_convert.md
docs/tools/width_convert.md
```

---

### Task 0: 分支、环境与包骨架

**Files:**
- Create: `pyproject.toml`, `requirements-dev.txt`, `src/dataforge/__init__.py`, `src/dataforge/__main__.py`, `tests/dataforge/__init__.py`, `tests/dataforge/qt_helpers.py`, `tests/dataforge/test_package.py`
- Modify: `requirements.txt`, `.gitignore`

**Interfaces:**
- Produces: 可导入的 `dataforge` 包，`dataforge.__version__ == "3.0.0.dev0"`；`tests.dataforge.qt_helpers.qapp() -> QApplication`、`wait_until(predicate: Callable[[], bool], timeout_ms: int = 5000) -> None`（超时抛 `AssertionError`；循环中用 `QCoreApplication.processEvents()` + `QThread.msleep(10)`，仅测试代码允许）。

- [ ] **Step 1:** `git checkout -b rebuild/v3`；把 `docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md` 和本计划一并纳入本分支。
- [ ] **Step 2:** `.gitignore` 增加一行 `.superpowers/`。
- [ ] **Step 3:** `requirements.txt` 调整下限以支持 Python 3.13（v2 仍需的依赖全部保留，删除留到阶段 5）：`pandas>=2.2.3`、`numpy>=2.1`、`openpyxl>=3.1.5`、`pyinstaller>=6.11`、`pywin32>=308`、`PySide6>=6.8`、`PySide6-Fluent-Widgets>=1.7`、`platformdirs>=4.2.2`；删除 `pygetwindow`（v2 已不再导入）。`requirements-dev.txt`：`-r requirements.txt` 与 `pytest>=8`。
- [ ] **Step 4:** `pyproject.toml`：项目名 `dataforge-studio`，`requires-python = ">=3.11"`，setuptools src 布局只打包 `dataforge*`；`[tool.pytest.ini_options] pythonpath = ["src", "."]`，`testpaths = ["tests"]`。
- [ ] **Step 5:** 建 venv 并安装：`python -m venv .venv && .venv\Scripts\activate && pip install -r requirements-dev.txt && pip install -e .`
- [ ] **Step 6:** 写 `tests/dataforge/test_package.py`：`test_version` 断言 `dataforge.__version__ == "3.0.0.dev0"`；`test_backend_has_no_qt_imports` 遍历 `src/dataforge/{core,fileio,config,tools}` 与 `src/dataforge/dates.py` 的源码文本，断言不含 `PySide6` 与 `qfluentwidgets`。
- [ ] **Step 7:** `tests/dataforge/__init__.py` 中 `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`；实现 `qt_helpers.py`。
- [ ] **Step 8:** 运行 `python -m pytest tests/dataforge -q` → 2 passed；运行 `python -m pytest tests -q` → v2 原有 13 个测试仍通过。
- [ ] **Step 9:** Commit：`chore(v3): scaffold dataforge package, branch and dev env`

---

### Task 1: core —— 异常、结果、进度与取消

**Files:**
- Create: `src/dataforge/core/__init__.py`, `errors.py`, `result.py`, `progress.py`
- Test: `tests/dataforge/test_core.py`

**Interfaces:**
- Produces:
  - `class DataForgeError(ValueError)`：所有可预期的输入/业务错误的基类，消息为中文、可直接展示给用户。
  - `class Cancelled(Exception)`
  - `@dataclass(frozen=True) class FileIssue: path: str; message: str`
  - `@dataclass class Result: outputs: list[Path]; warnings: list[FileIssue]; errors: list[FileIssue]; stats: dict[str, int]`（全部 `field(default_factory=...)`）；`ok -> bool`（property，`not errors`）；`add_output(path: Path)`；`warn(path: str | Path, message: str)`；`fail(path: str | Path, message: str)`；`count(key: str, n: int = 1)`（`stats[key] += n`）。
  - `ProgressFn = Callable[[int, int, str], None]`；`def no_progress(current: int, total: int, label: str) -> None`
  - `class CancelToken`：`cancel() -> None`；`cancelled -> bool`（property）；`raise_if_cancelled() -> None`（已取消时抛 `Cancelled`）。基于 `threading.Event`，线程安全。

- [ ] **Step 1: 写失败测试**

```python
class ResultTests(unittest.TestCase):
    def test_ok_false_after_fail(self):
        r = Result(); r.fail("a.csv", "坏了")
        self.assertFalse(r.ok)
        self.assertEqual(r.errors, [FileIssue("a.csv", "坏了")])
    def test_count_accumulates(self):
        r = Result(); r.count("cells"); r.count("cells", 4)
        self.assertEqual(r.stats["cells"], 5)
    def test_paths_are_stringified_in_issues(self):
        r = Result(); r.warn(Path("x/y.csv"), "w")
        self.assertEqual(r.warnings[0].path, str(Path("x/y.csv")))

class CancelTokenTests(unittest.TestCase):
    def test_raise_if_cancelled(self):
        t = CancelToken(); t.raise_if_cancelled()
        t.cancel(); self.assertTrue(t.cancelled)
        with self.assertRaises(Cancelled): t.raise_if_cancelled()
    def test_dataforge_error_is_value_error(self):
        self.assertTrue(issubclass(DataForgeError, ValueError))
```

- [ ] **Step 2:** `python -m pytest tests/dataforge/test_core.py -q` → FAIL（ImportError）
- [ ] **Step 3:** 实现上述三个模块。
- [ ] **Step 4:** 同命令 → PASS
- [ ] **Step 5:** Commit：`feat(v3): core result, progress and cancel types`

---

### Task 2: 日志

**Files:**
- Create: `src/dataforge/core/logs.py`
- Test: `tests/dataforge/test_logs.py`

**Interfaces:**
- Produces:
  - `def default_log_dir() -> Path`：`platformdirs.user_log_dir("dataforge_studio", appauthor=False)`
  - `def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> Path`：在 `logging.getLogger("dataforge")` 上挂 `RotatingFileHandler(log_dir/"dataforge.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")`，格式 `"%(asctime)s %(levelname)s %(name)s: %(message)s"`；重复调用不重复挂 handler；返回日志文件路径。

- [ ] **Step 1: 写失败测试** `test_setup_logging_writes_file`：临时目录调用两次 `setup_logging(tmp)`，`logging.getLogger("dataforge.x").info("hello")` 后 flush，断言 `dataforge.log` 存在、`"hello"` 恰好出现 1 次。测试结束移除该 handler。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): rotating file logging`

---

### Task 3: 输出路径规划与输入文件展开

**Files:**
- Create: `src/dataforge/fileio/__init__.py`, `src/dataforge/fileio/paths.py`
- Test: `tests/dataforge/test_paths.py`

**Interfaces:**
- Produces:
  - `def plan_output(source: Path, *, new_name: str, output_dir: Path | None = None, overwrite_source: bool = False) -> Path`
    - `overwrite_source=True` → 直接返回 `source`。
    - 否则目标为 `(output_dir or source.parent) / new_name`；自动 `mkdir(parents=True, exist_ok=True)`；目标已存在时依次尝试 `<stem>_1<suffix>`、`<stem>_2<suffix>`……返回第一个不存在的路径。
  - `def iter_input_files(paths: Iterable[Path], extensions: tuple[str, ...], recursive: bool = False) -> list[Path]`
    - 文件直接收（扩展名不区分大小写匹配 `extensions`，如 `(".xlsx", ".xlsm")`）；文件夹展开（`recursive` 决定是否进子目录），同一文件夹内按文件名排序。
    - 跳过文件名以 `~$` 开头的文件；按解析后的绝对路径去重，保持首次出现顺序。

- [ ] **Step 1: 写失败测试**

```python
def test_new_name_next_to_source(self):      # tmp/a.xlsx → tmp/a_halfwidth.xlsx
def test_conflict_appends_counter(self):     # 已有 a_halfwidth.xlsx 与 a_halfwidth_1.xlsx → 返回 a_halfwidth_2.xlsx
def test_output_dir_created(self):           # output_dir=tmp/out/sub 不存在 → 返回 tmp/out/sub/a_halfwidth.xlsx 且目录已建
def test_overwrite_returns_source(self):     # overwrite_source=True → 返回 source 本身
def test_iter_skips_lock_files_and_filters_ext(self):
    # tmp 下: b.xlsx, A.XLSX, ~$b.xlsx, note.txt, sub/c.xlsx
    # iter_input_files([tmp], (".xlsx",)) == [tmp/"A.XLSX", tmp/"b.xlsx"]
    # recursive=True 时追加 tmp/"sub"/"c.xlsx"
def test_iter_dedupes(self):                 # [f, f, tmp] 中 f 只出现一次
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): output path planning and input expansion`

---

### Task 4: ConfigStore

**Files:**
- Create: `src/dataforge/config/__init__.py`, `src/dataforge/config/store.py`
- Test: `tests/dataforge/test_config_store.py`

**Interfaces:**
- Produces:
  - `def default_config_path() -> Path`（见 Global Constraints 的路径与环境变量规则）
  - `def legacy_config_path() -> Path`：`user_config_dir("tools_box", appauthor=False, roaming=False)/"tools_box_config.json"`
  - `class ConfigStore`：
    - `__init__(self, path: Path | None = None, legacy_path: Path | None = None)`：`path=None` 时用 `default_config_path()`，`legacy_path=None` 时用 `legacy_config_path()`（仅当 `path` 也为 None 时才启用旧路径回退）。
    - `path: Path`（写入目标）
    - `section(self, name: str) -> dict[str, Any]`：返回深拷贝，不存在为 `{}`。
    - `update_section(self, name: str, data: dict[str, Any]) -> bool`：替换该分区，保留其他分区；先写同目录临时文件再 `os.replace`；失败记 `logger.exception` 并返回 `False`。
  - 读取规则：`path` 存在则读它；否则若允许回退且旧文件存在，读旧文件（不改动旧文件）。JSON 解析失败或顶层不是 dict → 把坏文件重命名为 `<name>.corrupt-YYYYmmdd_HHMMSS.bak`，记 warning，按 `{}` 继续。

- [ ] **Step 1: 写失败测试**

```python
def test_update_preserves_other_sections(self):   # 先写 a={"x":1}，再写 b={"y":2}；新实例读 a == {"x":1}
def test_section_returns_copy(self):              # 修改返回值不影响下次读取
def test_corrupt_file_is_backed_up(self):         # 写入 "{not json"；ConfigStore(path).section("a") == {}；目录中出现 1 个 *.corrupt-*.bak 且内容为 "{not json"
def test_reads_legacy_when_new_missing(self):     # legacy 有 {"edc_site_adder":{"max_loops":5}}；新路径不存在 → section 读到；update_section 后新路径存在、legacy 内容不变
def test_write_failure_returns_false(self):       # patch("os.replace", side_effect=PermissionError) → update_section 返回 False，不抛异常
def test_env_var_overrides_path(self):            # patch.dict(os.environ, {"DATAFORGE_STUDIO_CONFIG_PATH": str(p)}) → default_config_path() == p
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): sectioned config store with atomic save and corrupt backup`

---

### Task 5: RecentStore（最近使用）

**Files:**
- Create: `src/dataforge/config/recent.py`
- Test: `tests/dataforge/test_recent.py`

**Interfaces:**
- Consumes: `ConfigStore`（Task 4）
- Produces:
  - `@dataclass(frozen=True) class RecentEntry: tool_id: str; summary: str; state: dict[str, Any]; timestamp: str`（ISO 8601，秒精度，本地时间）
  - `class RecentStore`：`SECTION = "recent"`；`__init__(self, store: ConfigStore, limit: int = 10)`；`entries(self) -> list[RecentEntry]`（新→旧）；`add(self, tool_id: str, summary: str, state: dict[str, Any]) -> RecentEntry`（若已存在相同 `tool_id` 且 `state` 相等的记录，先移除旧的再插到最前；超出 `limit` 截断）；`clear(self) -> None`。
  - 存储格式：`{"entries": [{"tool_id", "summary", "state", "timestamp"}, ...]}`；读取时跳过缺字段的坏记录。

- [ ] **Step 1: 写失败测试**：`test_add_newest_first`、`test_limit_10`（加 12 条只剩 10 条，最旧 2 条被丢弃）、`test_same_state_moves_to_top`（同工具同 state 再加一次，总数不变且排第一）、`test_clear`、`test_bad_records_skipped`（section 写入 `{"entries":[{"tool_id":"x"}]}` → `entries() == []`）。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): recent-use store`

---

### Task 6: JobRunner（全局单任务后台运行）

**Files:**
- Create: `src/dataforge/ui/__init__.py`, `src/dataforge/ui/jobs.py`
- Test: `tests/dataforge/test_jobs.py`

**Interfaces:**
- Consumes: `Result`、`ProgressFn`、`CancelToken`、`Cancelled`、`DataForgeError`（Task 1）
- Produces:
  - `JobFn = Callable[[ProgressFn, CancelToken], Result]`
  - `class JobRunner(QObject)`：
    - 信号：`started(str)`（tool_id）、`progress(int, int, str)`、`log(str)`、`finished(str, object)`（tool_id, Result）、`failed(str, str)`（tool_id, 中文消息）、`cancelled(str)`、`busy_changed(bool)`
    - `submit(self, tool_id: str, fn: JobFn) -> bool`：忙时返回 `False` 且不启动；否则在内部 `QThread` 子类里运行 `fn`，返回 `True`。
    - `cancel(self) -> None`；`is_busy(self) -> bool`；`current_tool(self) -> str | None`
    - `shutdown(self, timeout_ms: int = 5000) -> None`：取消并 `wait`，供窗口关闭时调用。
  - 异常映射：`Cancelled` → `cancelled`；`DataForgeError` → `failed(tool_id, str(e))`；其他异常 → `logger.exception` 后 `failed(tool_id, f"内部错误：{e}")`。
  - 日志转发：构造时在 `logging.getLogger("dataforge")` 上挂一个 handler，其 `emit` 通过一个 QObject 信号（跨线程自动排队）转发为 `log(str)`，仅在忙时转发；格式 `"%(levelname)s %(message)s"`。
  - 线程中的进度回调只发信号，不触碰任何控件。

- [ ] **Step 1: 写失败测试**（`qapp()` + `wait_until`）

```python
def test_finished_delivers_result(self):         # fn 返回 Result(stats={"n":1}) → finished 收到 ("t", 该 Result)，busy_changed 依次 True、False
def test_second_submit_rejected_while_busy(self):# fn 等待一个 threading.Event；第二次 submit 返回 False；放行后 is_busy() 变 False
def test_cancel_emits_cancelled(self):           # fn 循环 raise_if_cancelled()+sleep(0.01)；cancel() → cancelled("t")
def test_dataforge_error_maps_to_failed(self):   # fn 抛 DataForgeError("缺少 DM.csv") → failed("t", "缺少 DM.csv")
def test_unexpected_error_maps_to_failed(self):  # fn 抛 RuntimeError("boom") → failed 消息以 "内部错误：" 开头
def test_progress_forwarded(self):               # fn 调 progress(1, 2, "a.xlsx") → 收到 (1, 2, "a.xlsx")
def test_log_forwarded_while_busy(self):         # fn 内 logging.getLogger("dataforge.tools.t").info("处理中") → log 信号含 "处理中"
def test_shutdown_cancels_and_waits(self):       # 长任务运行中 shutdown() 返回后 is_busy() 为 False
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 运行 → PASS（连续运行 3 次确认无偶发失败）
- [ ] **Step 5:** Commit：`feat(v3): single global background job runner`

---

### Task 7: 工具登记、主题与布局断点

**Files:**
- Create: `src/dataforge/ui/registry.py`, `src/dataforge/ui/theme.py`, `src/dataforge/ui/layout.py`
- Test: `tests/dataforge/test_registry_theme_layout.py`

**Interfaces:**
- Produces:
  - `class ToolGroup(Enum)`：`FILES = "文件处理"`、`BUSINESS = "业务"`、`UTILS = "小工具"`（声明顺序即侧边栏顺序）
  - `@dataclass(frozen=True) class ToolSpec: id: str; name: str; description: str; group: ToolGroup; icon: FluentIcon; page: str`（`"模块路径:类名"`）
  - `TOOLS: tuple[ToolSpec, ...]`；`def get_tool(tool_id: str) -> ToolSpec`（未知抛 `KeyError`）；`def load_page_class(spec: ToolSpec) -> type`
  - 本阶段登记 2 个工具（后续阶段追加，id 与名称在此固定，供全部阶段使用）：

    | id | name | group | description | icon |
    |---|---|---|---|---|
    | `date_convert` | 日期转换 | UTILS | 文本中的日期转为 ISO 8601 | `FluentIcon.CALENDAR` |
    | `width_convert` | 全角转半角 | UTILS | Excel 中的全角英数符号转半角 | `FluentIcon.FONT` |

    后续阶段将追加：`format_convert` 格式转换、`sheet_split` 工作表拆分、`field_extract` 获取字段（FILES）；`data_masking` 数据模糊化、`edc_site_adder` EDC 站点添加（BUSINESS）。
  - `theme.py`：`THEME_MODES = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}`；`def apply_theme_mode(mode: str) -> Theme`（未知值按 `"auto"`）；`def start_system_theme_listener(parent: QObject) -> SystemThemeListener`（创建并 `start()`；调用方在退出时 `terminate()`+`wait()` 或交给 parent 销毁，按 qfluentwidgets 示例）。
  - `layout.py`：`class LayoutMode(Enum): WIDE, MEDIUM, NARROW`；`def layout_mode_for_width(window_width: int) -> LayoutMode`（≥1100 WIDE，≥750 MEDIUM，否则 NARROW）；`MIN_WINDOW_WIDTH = 640`。

- [ ] **Step 1: 写失败测试**：`test_ids_unique`；`test_get_tool_unknown_raises`；（页面可导入性测试 `test_every_page_importable` 在 Task 13 页面都存在后再加）`test_layout_breakpoints`（1100→WIDE、1099→MEDIUM、750→MEDIUM、749→NARROW、640→NARROW）；`test_apply_theme_mode_unknown_falls_back_to_auto`（返回 `Theme.AUTO`）。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现（`TOOLS` 中 `page` 字段先填最终路径 `dataforge.ui.pages.date_convert_page:DateConvertPage` 与 `dataforge.ui.pages.width_convert_page:WidthConvertPage`）。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): tool registry, theme modes and layout breakpoints`

---

### Task 8: 公共组件 —— ResponsiveForm、FileInputCard、RunBar、ResultPanel

**Files:**
- Create: `src/dataforge/ui/components/__init__.py`, `responsive_form.py`, `file_input.py`, `run_bar.py`, `result_panel.py`
- Test: `tests/dataforge/test_components.py`

**Interfaces:**
- Consumes: `iter_input_files`（Task 3）、`Result`（Task 1）
- Produces:
  - `class ResponsiveForm(QWidget)`：`add_row(self, label: str, field: QWidget, hint: str | None = None) -> None`；`set_compact(self, compact: bool) -> None`（False：QGridLayout 两列"标签 | 输入"；True：标签在上、输入在下单列）；`is_compact() -> bool`。标签用 `BodyLabel`，hint 用 `CaptionLabel`。
  - `class FileInputCard(SimpleCardWidget)`：`__init__(self, title: str, extensions: tuple[str, ...], allow_folder: bool = True, parent=None)`；信号 `files_changed(list)`；`files(self) -> list[Path]`；`set_files(self, paths: list[Path]) -> None`；`clear(self) -> None`；`set_locked(self, locked: bool) -> None`。内部：`ListWidget` 显示路径，按钮"选择文件 / 选择文件夹 / 清空"（`PushButton`），文件对话框用 `QFileDialog.getOpenFileNames` / `getExistingDirectory`（原生），拖放接受文件与文件夹，所有新增路径都经 `iter_input_files` 过滤并与已有列表合并去重。
  - `class RunBar(QWidget)`：信号 `start_requested()`、`cancel_requested()`；`set_primary_text(self, text: str)`；`set_running(self, running: bool)`（运行中：主按钮禁用、取消可用、进度条显示）；`set_progress(self, current: int, total: int, label: str)`（`total == 0` 时为不确定进度）；`set_blocked(self, reason: str | None)`（非 None：主按钮禁用并在旁边 `CaptionLabel` 显示 reason）。主按钮 `PrimaryPushButton`，进度 `ProgressBar`。
  - `class ResultPanel(QWidget)`：三个标签页"结果 / 警告 / 日志"（`SegmentedWidget` + `QStackedWidget`，内容为只读 `PlainTextEdit`）；`show_result(self, result: Result) -> None`（结果页列出 `outputs` 与 `stats`，警告页列出 `warnings`+`errors`，标签文字带数量，如 `警告 (2)`）；`append_log(self, line: str)`；`clear(self)`；`set_collapsed(self, collapsed: bool)`（True：只显示一行摘要 `"{成功输出数} 个输出 · {警告+错误数} 个问题"`，点击摘要展开）；`summary_text(self) -> str`。

- [ ] **Step 1: 写失败测试**

```python
def test_form_compact_moves_label_above(self):   # 加 1 行；非紧凑时 label 与 field 同一 grid 行不同列；set_compact(True) 后 field 的行号 = label 行号 + 1 且同列
def test_file_card_filters_and_dedupes(self):   # set_files([a.xlsx, a.xlsx, ~$b.xlsx, n.txt]) 且 extensions=(".xlsx",) → files() == [a.xlsx]；files_changed 发出 1 次
def test_run_bar_running_state(self):           # set_running(True) → 主按钮 disabled、取消按钮 enabled；set_blocked("格式转换 正在运行") → 主按钮 disabled 且提示文本含该字串
def test_result_panel_counts(self):             # Result 含 2 outputs、1 warn、1 fail → 警告标签文字含 "(2)"；summary_text() == "2 个输出 · 2 个问题"
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。（遵守 Global Constraints：无 QSS、无 hex 颜色、无固定宽度。）
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): shared responsive form, file input, run bar and result panel`

---

### Task 9: ToolPage 基类（响应式骨架）

**Files:**
- Create: `src/dataforge/ui/components/tool_page.py`
- Test: `tests/dataforge/test_tool_page.py`

**Interfaces:**
- Consumes: Task 6 `JobRunner`、Task 7 `ToolSpec`/`LayoutMode`/`layout_mode_for_width`、Task 8 全部组件
- Produces:
  - `class ToolPage(QWidget)`：
    - `__init__(self, spec: ToolSpec, runner: JobRunner, parent=None)`；`objectName` 设为 `spec.id`。
    - 结构：标题 `TitleLabel(spec.name)` + 说明 `CaptionLabel(spec.description)`；左侧/上方是 `SmoothScrollArea` 内的设置区，子类通过 `self.add_section(title: str, widget: QWidget) -> SimpleCardWidget` 添加卡片；结果区 `self.result_panel: ResultPanel`；底部固定 `self.run_bar: RunBar`。
    - `apply_layout_mode(self, mode: LayoutMode) -> None`：WIDE 设置区与结果区左右并排（约 55:45）；MEDIUM 上下排列；NARROW 上下排列 + 所有 `ResponsiveForm` 紧凑 + `result_panel.set_collapsed(True)`。`resizeEvent` 中用 `layout_mode_for_width(self.window().width())` 计算并在变化时调用。`layout_mode() -> LayoutMode`。
    - 子类实现：`build_job(self) -> JobFn | None`（校验失败时自行用 `InfoBar.warning` 提示并返回 None）；`capture_state(self) -> dict[str, Any]`；`restore_state(self, state: dict[str, Any]) -> list[str]`（返回已不存在的文件路径列表）；`summary(self) -> str`（最近使用里显示的输入摘要）；`set_inputs_locked(self, locked: bool) -> None`。
    - 信号 `run_succeeded(str, dict)`：收到本工具的 `finished` 且 `result.outputs` 非空时发出 `(summary(), capture_state())`（部分文件失败但有输出也记入最近使用）。
    - 运行流程：`run_bar.start_requested` → `build_job()` → `runner.submit(spec.id, fn)`；只处理 `runner.current_tool() == spec.id` 的信号；`started` → 锁定输入、`run_bar.set_running(True)`、`result_panel.clear()`；`progress`/`log` → 转给 run_bar/result_panel；`finished` → `result_panel.show_result`，`InfoBar.success`（有错误时 `InfoBar.warning`）；`failed` → `InfoBar.error`；`cancelled` → `InfoBar.info("已取消")`；`busy_changed` → 别的工具在跑时 `run_bar.set_blocked(f"{get_tool(other).name} 正在运行")`，空闲时 `set_blocked(None)`。

- [ ] **Step 1: 写失败测试**（测试内定义一个最小子类 `_DummyPage(ToolPage)`，`build_job` 返回立即完成的 fn）

```python
def test_layout_mode_switches(self):        # page.apply_layout_mode(NARROW) → result_panel 处于折叠；apply_layout_mode(WIDE) → 未折叠
def test_run_emits_run_succeeded(self):     # 触发 run_bar.start_requested → 等待 run_succeeded，参数 == (page.summary(), page.capture_state())
def test_other_tool_running_blocks(self):   # runner.submit("width_convert", 阻塞 fn) → dummy(spec=date_convert) 的 run_bar 主按钮 disabled 且提示含 "全角转半角 正在运行"；放行后恢复
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): responsive ToolPage base`

---

### Task 10: 外壳 MainWindow、设置页与应用入口

**Files:**
- Create: `src/dataforge/ui/shell.py`, `src/dataforge/ui/settings.py`, `src/dataforge/app.py`; Modify: `src/dataforge/__main__.py`
- Test: `tests/dataforge/test_shell_smoke.py`

**Interfaces:**
- Consumes: Task 4/5/6/7/9
- Produces:
  - `class MainWindow(FluentWindow)`：`__init__(self, config: ConfigStore, runner: JobRunner, recent: RecentStore)`；
    - `setMicaEffectEnabled(True)`；`setMinimumWidth(MIN_WINDOW_WIDTH)`；窗口标题 `f"DataForge Studio {__version__}"`。
    - 侧边栏：主页（TOP）→ 按 `ToolGroup` 顺序，每组前 `navigationInterface.addSeparator()`，组内按 `TOOLS` 顺序添加（TOP）→ 设置（BOTTOM）。
    - 工具页延迟创建：每个工具先加一个空容器，首次切到时 `load_page_class(spec)(spec, runner)` 放进容器，并连接 `run_succeeded` → `recent.add(spec.id, summary, state)` → `home.refresh()`。
    - `open_tool(self, tool_id: str, state: dict | None = None) -> None`：切换并（若给出）调用 `restore_state`；返回的缺失文件非空时 `InfoBar.warning(title="部分文件已不存在", content=…)`。
    - `page_for(self, tool_id: str) -> ToolPage | None`（测试用：已创建的页面）
    - `closeEvent`：`runner.shutdown()` 后再关闭；有任务在跑时先 `MessageBox` 确认"任务仍在运行，确定退出？"。
  - `class SettingsPage(QWidget)`：`ComboBox` 选项 跟随系统/浅色/深色 ↔ `auto/light/dark`，变更时 `apply_theme_mode` 并 `config.update_section("app", {..., "theme": mode})`；按钮"打开日志文件夹""打开配置文件夹"（`QDesktopServices.openUrl(QUrl.fromLocalFile(...))`）；"清空最近使用"（`recent.clear()` 后通知主页刷新，信号 `recent_cleared()`）；版本 `BodyLabel`。
  - `app.main(argv: list[str] | None = None) -> int`：`setup_logging()` → `QApplication` → `config = ConfigStore()` → `apply_theme_mode(config.section("app").get("theme", "auto"))` → `start_system_theme_listener(app)` → `JobRunner()`、`RecentStore(config)` → `MainWindow(...).show()` → `app.exec()`。不设置 `AA_DontUseNativeDialogs`，不改全局字体。
  - `__main__.py`：`raise SystemExit(main())`。

- [ ] **Step 1: 写失败测试**（临时目录配置文件）

```python
def test_window_builds_in_both_themes(self):     # 对 Theme.LIGHT、Theme.DARK：setTheme 后构建 MainWindow，逐个 open_tool(spec.id)，page_for(id) 非 None
def test_theme_switch_while_running(self):       # 提交阻塞任务后 setTheme(DARK)、切换页面，不抛异常；放行后正常 finished
def test_settings_persists_theme(self):          # 设置页选择"深色" → 新 ConfigStore 读 section("app")["theme"] == "dark"
def test_close_while_running_shuts_down(self):   # 阻塞任务运行中，patch MessageBox 确认为是，window.close() 后 runner.is_busy() 为 False
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。（主页在 Task 11 完成前用 `HomePage` 的最小实现占位亦可，但 Task 11 必须替换为完整实现。）
- [ ] **Step 4:** 运行 → PASS；手动 `python -m dataforge` 启动一次，Windows 设置里切换亮/暗，确认窗口与标题栏跟随变化。
- [ ] **Step 5:** Commit：`feat(v3): main window shell, settings page and entry point`

---

### Task 11: 主页（最近使用 + 紧凑工具格）

**Files:**
- Create: `src/dataforge/ui/home.py`; Modify: `src/dataforge/ui/shell.py`（接入）
- Test: `tests/dataforge/test_home.py`

**Interfaces:**
- Consumes: `RecentStore`/`RecentEntry`（Task 5）、`TOOLS`（Task 7）
- Produces:
  - `class HomePage(QWidget)`：`__init__(self, tools: tuple[ToolSpec, ...], recent: RecentStore, open_tool: Callable[[str, dict | None], None], parent=None)`；`refresh(self) -> None`；`visible_recent(self) -> list[RecentEntry]`（测试用）。
  - 布局：`SmoothScrollArea` 内，标题 `TitleLabel("DataForge Studio")` + 版本；"最近使用"区：每条一张可点击 `CardWidget`，显示工具名、`summary`、时间（`今天 HH:MM` / `昨天` / `YYYY-MM-DD`），点击调用 `open_tool(entry.tool_id, entry.state)`；无记录时显示 `CaptionLabel("还没有使用记录")`。"全部工具"区：`FlowLayout` 中每个工具一张可点击 `CardWidget`（图标 + 名称 + 描述），点击调用 `open_tool(id, None)`。
  - 未在 `tools` 中的 `tool_id` 记录不显示。

- [ ] **Step 1: 写失败测试**：`test_unknown_tool_entries_hidden`（recent 含 `"dead_link"` 与 `"date_convert"` 各一条 → `visible_recent()` 只有后者）；`test_click_recent_opens_with_state`（模拟点击第一张最近卡片 → `open_tool` 收到 `("date_convert", {...})`）；`test_click_tool_card_opens_without_state`；`test_refresh_after_add`（`recent.add` 后 `refresh()`，`visible_recent()` 数量 +1）。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现并在 `MainWindow` 中替换占位。
- [ ] **Step 4:** 运行 → PASS
- [ ] **Step 5:** Commit：`feat(v3): home page with recent runs and tool grid`

---

### Task 12: 全角转半角（后端 + 页面 + 标准样例）

**Files:**
- Create: `src/dataforge/tools/__init__.py`, `src/dataforge/tools/width_convert.py`, `src/dataforge/ui/pages/__init__.py`, `src/dataforge/ui/pages/width_convert_page.py`, `tests/golden/width_convert/make_fixtures.py`, `tests/golden/width_convert/basic/{params.json,input/sample.xlsx,expected/sample_halfwidth.xlsx}`, `tests/dataforge/golden.py`, `docs/tools/README.md`, `docs/tools/width_convert.md`
- Test: `tests/dataforge/test_width_convert.py`, `tests/dataforge/test_golden.py`

**Interfaces:**
- Consumes: `Result`/`ProgressFn`/`CancelToken`（Task 1）、`plan_output`/`iter_input_files`（Task 3）、`ToolPage`（Task 9）
- Produces:
  - `def to_halfwidth(text: str) -> str`：U+FF01–U+FF5E → U+0021–U+007E（减 0xFEE0），U+3000 → U+0020；其他字符（含日文假名、汉字、半角片假名）不变。
  - `@dataclass class WidthOptions: output_dir: Path | None = None; overwrite_source: bool = False`
  - `def run(files: list[Path], options: WidthOptions, progress: ProgressFn, cancel: CancelToken) -> Result`
    - 接受 `.xlsx`、`.xlsm`（`.xlsm` 用 `keep_vba=True`）；每个文件 `openpyxl.load_workbook`，遍历所有 sheet 所有单元格：仅 `data_type == "s"` 的字符串单元格转换（公式 `"f"` 不动）；表头一并转换。
    - 输出：`plan_output(src, new_name=f"{src.stem}_halfwidth{src.suffix}", output_dir=..., overwrite_source=...)`。
    - stats：`files`（成功文件数）、`cells_changed`（实际有变化的单元格数）。
    - 每个文件开始前 `cancel.raise_if_cancelled()`，并 `progress(i, total, src.name)`；单个文件异常（含 `PermissionError`）→ `result.fail(src, 中文原因)` 并继续；`files` 为空 → 抛 `DataForgeError("请先选择要转换的 Excel 文件")`。
  - `tests/dataforge/golden.py`：
    - `GOLDEN_ROOT = Path("tests/golden")`
    - `def discover(tool_id: str) -> list[Path]`（返回 `tests/golden/<tool_id>/*/` 中含 `params.json` 的用例目录）
    - `ADAPTERS: dict[str, Callable[[Path, Path, dict], None]]`（`(input_dir, output_dir, params)`，把 input 复制到临时目录后运行工具，输出写入 `output_dir`）
    - `def assert_dirs_equal(test: unittest.TestCase, expected: Path, actual: Path) -> None`：文件名集合一致；`.csv`/`.txt` 逐字节相等；`.xlsx`/`.xlsm` 用 openpyxl 比较每个 sheet 的名称、每个单元格 `value`、`number_format`、合并区域。
  - `WidthConvertPage(ToolPage)`：设置区 = `FileInputCard("Excel 文件", (".xlsx", ".xlsm"))` + `ResponsiveForm`（"输出位置"：`ComboBox` 与原文件相同 / 指定文件夹…（选中时弹原生目录对话框并显示路径）；"覆盖原文件"：`CheckBox`，默认不勾，运行前若勾选则 `MessageBox` 二次确认）；主按钮文字"开始转换"；`capture_state` = `{"files": [...], "output_dir": str | None, "overwrite_source": bool}`；`summary` = `"{首个文件名} 等 {n} 个文件"`（n=1 时只显示文件名）。

- [ ] **Step 1: 写失败测试**

```python
def test_to_halfwidth(self):
    self.assertEqual(to_halfwidth("ＡＢＣ１２３！　ｘ"), "ABC123! x")
    self.assertEqual(to_halfwidth("テスト医師ｱｲｳ"), "テスト医師ｱｲｳ")   # 假名、汉字、半角片假名不变
def test_run_keeps_formatting_and_formula(self):
    # 用 openpyxl 构造：A1="ＮＡＭＥ"(表头, 加粗), A2="ＡＢＣ", B2="=LEN(A2)", A3 合并 A3:B3 值 "１２"
    # run → 输出 sample_halfwidth.xlsx：A1=="NAME" 且仍加粗；A2=="ABC"；B2=="=LEN(A2)"；A3=="12" 且合并区域仍为 A3:B3
    # stats == {"files": 1, "cells_changed": 3}；原文件内容不变
def test_conflict_and_permission_error_continue(self):
    # 两个文件 a.xlsx、b.xlsx；patch openpyxl Workbook.save 在第一次调用抛 PermissionError
    # → result.errors 1 条（path 为 a.xlsx）、outputs 1 个（b_halfwidth.xlsx）
def test_cancel_before_second_file(self):
    # progress 回调里在 current==1 时 cancel.cancel() → 抛 Cancelled
def test_empty_files_raises(self):
    with self.assertRaises(DataForgeError): run([], WidthOptions(), no_progress, CancelToken())
```

  `tests/dataforge/test_golden.py`：对 `discover(tool_id)` 的每个用例用 `subTest` 运行 `ADAPTERS[tool_id]` 并 `assert_dirs_equal`。

- [ ] **Step 2:** 运行两个测试文件 → FAIL
- [ ] **Step 3:** 实现 `width_convert.py`。
- [ ] **Step 4:** 写 `make_fixtures.py`：用**手写的字面值**分别构造 `input/sample.xlsx` 与 `expected/sample_halfwidth.xlsx`（不得调用被测代码生成期望值）；覆盖：表头、普通文本、全角空格、数字字符串、日文假名、公式、合并单元格、两个 sheet。`params.json` 为 `{}`。运行它生成文件并提交。
- [ ] **Step 5:** 实现 `golden.py` 与 `ADAPTERS["width_convert"]`。
- [ ] **Step 6:** 实现 `WidthConvertPage`，在 `test_width_convert.py` 增加页面测试 `test_page_restore_reports_missing`：`restore_state({"files": [存在的 a.xlsx, 不存在的 z.xlsx], "output_dir": None, "overwrite_source": False})` 返回 `[str(z)]`，`FileInputCard.files() == [a]`。
- [ ] **Step 7:** `python -m pytest tests/dataforge -q` → 全部 PASS
- [ ] **Step 8:** 写 `docs/tools/README.md`（规则说明模板：输入、参数与默认值、处理步骤、输出位置与命名、编码、边界情况、已知限制；标准样例目录格式与比较规则，说明以后其他语言版本按同一目录对照）与 `docs/tools/width_convert.md`（依 spec §7.7 与本任务的实际行为填写，含输出名 `<stem>_halfwidth<suffix>`）。
- [ ] **Step 9:** Commit：`feat(v3): fullwidth-to-halfwidth tool with golden samples`

---

### Task 13: 日期转换（后端 + 简化页面 + 标准样例）

**Files:**
- Create: `src/dataforge/dates.py`, `src/dataforge/tools/date_convert.py`, `src/dataforge/ui/pages/date_convert_page.py`, `tests/golden/date_convert/basic/{params.json,input/input.txt,expected/output.txt}`, `docs/tools/date_convert.md`
- Modify: `tests/dataforge/golden.py`（加适配器）, `tests/dataforge/test_registry_theme_layout.py`（加 `test_every_page_importable`）
- Test: `tests/dataforge/test_date_convert.py`

**Interfaces:**
- Produces:
  - `dates.to_iso8601(value: str) -> str`：规则（沿用 v2，含一处变更）
    - 先 `strip()`；空 → `""`。
    - 不含 `/` → 原样返回（strip 后的值）。
    - 按 `/` 切分；任一部分不是整数 → 原样返回；年不在 1000–9999 → 原样返回；只有年 → `"YYYY"`。
    - 月不在 1–12 → `"YYYY"`；只有年月 → `"YYYY-MM"`。
    - 年月日三段：【变更】用真实日历校验（`calendar.monthrange`），有效 → `"YYYY-MM-DD"`，无效 → `"YYYY-MM"`。
    - 超过三段 → 原样返回。
  - `tools.date_convert.convert_text(text: str) -> str`：按 `splitlines()` 逐行 `to_iso8601`，以 `"\n"` 连接。
  - `DateConvertPage(QWidget)`：**不继承 ToolPage**（spec §5.4 简化版）；构造签名同 ToolPage（`spec, runner, parent=None`）以便外壳统一创建；两个 `PlainTextEdit`（输入、结果；结果只读），宽 ≥750 左右并排、否则上下；按钮"转换"（`PrimaryPushButton`）与"复制结果"（`PushButton`，复制后 `InfoBar.success("已复制")`，空结果时 `InfoBar.info("没有可复制的内容")`）；提供 `restore_state(state) -> list[str]` 返回 `[]`，不发 `run_succeeded`（即时工具不记入最近使用）。

- [ ] **Step 1: 写失败测试**

```python
CASES = [
    ("2021/2/3", "2021-02-03"), ("2020/02/29", "2020-02-29"),
    ("2021/02/31", "2021-02"),          # 变更：日历校验
    ("2010/99/99", "2010"), ("2010/10/99", "2010-10"), ("2010/10", "2010-10"),
    (" 2010/1 ", "2010-01"), ("", ""), ("abc", "abc"), ("2010", "2010"),
    ("999/01/01", "999/01/01"), ("2010/10/ab", "2010/10/ab"), ("2010/", "2010/"),
    ("2010/1/2/3", "2010/1/2/3"),
]
def test_to_iso8601_cases(self):
    for raw, want in CASES:
        with self.subTest(raw=raw): self.assertEqual(to_iso8601(raw), want)
def test_convert_text_lines(self):
    self.assertEqual(convert_text("2021/2/3\n\nabc"), "2021-02-03\n\nabc")
```

  在 `test_registry_theme_layout.py` 加 `test_every_page_importable`（每个 `TOOLS` 项 `load_page_class` 成功）。

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现 `dates.py`、`date_convert.py`。
- [ ] **Step 4:** 标准样例：`input/input.txt` 为上面 CASES 的输入（每行一个，UTF-8 无 BOM，`\n` 换行），`expected/output.txt` 为对应期望；`ADAPTERS["date_convert"]` 读 `input.txt` 写 `output.txt`（UTF-8 无 BOM）。注意：`" 2010/1 "` 一行要保留前后空格写入文件。
- [ ] **Step 5:** 实现 `DateConvertPage`。
- [ ] **Step 6:** `python -m pytest tests/dataforge -q` → 全部 PASS
- [ ] **Step 7:** 写 `docs/tools/date_convert.md`（规则同上，标注日历校验为 v3 变更）。
- [ ] **Step 8:** Commit：`feat(v3): date conversion tool with golden samples`

---

### Task 14: 阶段验收

**Files:** 无新增（只在发现问题时修改）

- [ ] **Step 1:** `python -m pytest tests -q` → v2 原测试与 v3 测试全部通过。
- [ ] **Step 2:** 检查禁用写法：`rg -n "setStyleSheet|#[0-9A-Fa-f]{6}|processEvents|DontUseNativeDialog|setFixedWidth|print\(" src/dataforge` → 无匹配（`setFixedWidth` 若用于图标需逐条说明）。
- [ ] **Step 3:** `rg -n "TODO|FIXME|skip\(|\.only" src/dataforge tests/dataforge` → 无匹配。
- [ ] **Step 4:** 手动验收（`python -m dataforge`）并记录结果：系统亮/暗切换窗口跟随；设置页切换三种模式即时生效且重启后保持；拖动窗口宽度经过 1100、750 两个断点时全角转半角页面在三种排法间切换且无控件被挤压；运行全角转半角后主页"最近使用"出现记录，点击恢复文件与参数；删除其中一个输入文件后再点击，出现"部分文件已不存在"提示。
- [ ] **Step 5:** Commit（如有修正）：`fix(v3): phase 1 acceptance fixes`
