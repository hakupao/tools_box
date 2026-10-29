# DataForge Studio v3 · 阶段 2：文件处理工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先清掉阶段 1 遗留的退出卡死风险，再建立统一的编码识别（含歧义选择界面）与原子写出，然后完成"格式转换（4 种模式）""工作表拆分（与 XLSX→CSV 共用）""获取字段"三个工具的后端、页面、标准样例和规则说明。

**Architecture:** 沿用阶段 1 的分层：后端 `dataforge.fileio`（编码、读写、原子写）与 `dataforge.tools.*`（纯函数 `run(..., progress, cancel) -> Result`）不依赖 Qt；页面继承 `ToolPage`。编码歧义作为 `Result.encoding_questions` 返回，由 `ToolPage` 统一弹窗询问并只对这些文件自动重跑，结果合并显示。

**Tech Stack:** Python 3.13（`.venv`），PySide6 6.12，PySide6-Fluent-Widgets 1.11.3，openpyxl 3.1.5，darkdetect 0.8.0，标准库 `csv`。本阶段不使用 pandas。

**Spec:** `docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md`（§5.4、§6.1、§6.2、§7.1–7.3、§8）
**Carry-over:** `docs/superpowers/plans/2026-10-29-dataforge-v3-phase1-carryover.md`（"Final: parked" 三项在 Task 1 处理）

## Global Constraints

- 阶段 1 的全部 Global Constraints 继续有效（见阶段 1 计划同名一节）：后端无 Qt、无 `print`；界面无 QSS/hex/固定宽度/`processEvents`/`DontUseNativeDialog`；同一时间一个任务；v2 代码不动。
- 编码识别（spec §6.2，作者确认）：先 UTF-8 BOM → UTF-8；都失败再分别试 cp932 与 GBK：只一种成功→采用并在警告中注明；两种都成功→歧义，该文件不处理，询问用户；都失败→报错。**不用 latin1 兜底。** 页面可手动指定编码，此时跳过自动识别。
- 歧义询问对话框必须提供"本批其余文件也用此编码"勾选。
- CSV 写出一律 UTF-8 BOM（`utf-8-sig`）；所有输出经同目录临时文件 + `os.replace` 原子写入。
- 输出默认新文件、同名自动 `_1`、`_2`；"覆盖原文件"默认关闭且需二次确认（仅在输出扩展名与输入相同的模式中出现）。
- 选择文件夹时跳过 `~$` 临时文件（`iter_input_files` 已实现）。
- 新工具登记（id 固定）：`format_convert` 格式转换、`sheet_split` 工作表拆分、`field_extract` 获取字段，组 `ToolGroup.FILES`，图标依次 `FluentIcon.SYNC`、`FluentIcon.LAYOUT`、`FluentIcon.SEARCH`。
- 测试命令：`.venv/Scripts/python.exe -m pytest tests -q`；标准样例放 `tests/golden/<tool_id>/<case>/`，`.txt/.csv` 已在 `.gitattributes` 中设为 `-text`。
- 提交信息结尾：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

1. **Excel 文件正被 Excel 打开或无读权限**（读取时 `PermissionError`）→ 该文件记错误"无法读取文件（可能已在 Excel 中打开）"，批次继续。（测试见 Task 3）
2. **CSV 行长短不一、引号内含换行**→ CSV→XLSX 原样保留每一行、换行保留在单元格内，不报错。（测试见 Task 4）
3. **空文件**（0 字节 CSV、全空工作表）→ 生成对应的空输出或空汇总行，不报错。（测试见 Task 3、4、5）
4. **中文/日文文件名与 sheet 名含 Windows 非法字符或保留名**→ 输出名可用、可追溯。（测试见 Task 3、4）
5. **批次中途取消**→ 已完成的文件保留、未开始的不生成、不留临时文件。（测试见 Task 4）

---

## 文件结构

```
src/dataforge/ui/theme.py                    修改：自有守护线程监听系统主题，去掉 terminate
src/dataforge/app.py                         修改：退出时不再 terminate 监听线程
src/dataforge/ui/components/tool_page.py     修改：快照复位、零输出提示、编码歧义重跑流程
src/dataforge/core/result.py                 修改：EncodingQuestion、Result.encoding_questions、Result.extend
src/dataforge/fileio/atomic.py               新增：atomic_path()
src/dataforge/fileio/encoding.py             新增：detect_encoding() 与异常
src/dataforge/fileio/text_io.py              新增：read_text()、write_csv_rows()
src/dataforge/tools/width_convert.py         修改：改用 atomic_path
src/dataforge/tools/sheet_split.py           新增
src/dataforge/tools/format_convert.py        新增
src/dataforge/tools/field_extract.py         新增
src/dataforge/ui/components/output_location.py   新增：从全角页抽出的"输出位置"字段
src/dataforge/ui/components/folder_picker.py     新增
src/dataforge/ui/components/encoding_field.py    新增：编码下拉框
src/dataforge/ui/components/encoding_dialog.py   新增：歧义选择对话框 + ask_encodings()
src/dataforge/ui/pages/width_convert_page.py     修改：改用 OutputLocationField
src/dataforge/ui/pages/sheet_split_page.py       新增
src/dataforge/ui/pages/field_extract_page.py     新增
src/dataforge/ui/pages/format_convert_page.py    新增
src/dataforge/ui/registry.py                     修改：登记 3 个工具
tests/dataforge/golden.py                        修改：3 个适配器
tests/golden/{sheet_split,format_convert,field_extract}/...   新增样例 + make_fixtures.py
docs/tools/{sheet_split,format_convert,field_extract}.md      新增
docs/tools/README.md                             修改：编码规则一节
```

---

### Task 1: 阶段 1 遗留项

**Files:**
- Modify: `src/dataforge/ui/theme.py`, `src/dataforge/app.py`, `src/dataforge/ui/components/tool_page.py`
- Test: `tests/dataforge/test_registry_theme_layout.py`（或现有主题测试所在文件）, `tests/dataforge/test_tool_page.py`, `tests/dataforge/test_shell_smoke.py`

**Interfaces:**
- Produces:
  - `class SystemThemeWatcher`（`theme.py`）：`__init__(self, parent: QObject, watch: Callable[[Callable[[str], None]], None] | None = None)`，`watch` 默认 `darkdetect.listener`；`start(self) -> None` 在 `threading.Thread(daemon=True, name="dataforge-theme-watch")` 中调用 `watch(callback)`；callback 只发一个跨线程信号到主线程的 `_ThemeBridge`（沿用现有 bridge：仅当 `qconfig.themeMode.value == Theme.AUTO` 时 `setTheme(Theme.AUTO, lazy=True)`）；`watch` 抛异常时记 `logger.exception`，线程结束，不影响程序。
  - `start_system_theme_listener(parent: QObject, watch=None) -> SystemThemeWatcher`：创建并 `start()`。不再使用 qfluentwidgets 的 `SystemThemeListener`。
  - `app.main`：删除 `listener.terminate()` / `listener.wait()`；守护线程随进程退出。
  - `ToolPage`：`_end_run` 里清空快照（`self._snapshot = None`）；`_on_finished` 中 `outputs == 0` 且无警告、无错误时用 `InfoBar.info("未生成文件", "本次运行没有生成任何文件")`。

- [ ] **Step 1: 写失败测试**
  - `test_watcher_applies_system_dark`：`watch` 用假函数 `lambda cb: cb("Dark")`；先 `setTheme(Theme.AUTO)`，patch `darkdetect.theme` 返回 `"Dark"`；`start_system_theme_listener(app, watch=fake)` 后 `wait_until(isDarkTheme)`，并断言某个 `PushButton` 的 `styleSheet()` 已变化。
  - `test_watcher_ignored_in_fixed_mode`：`setTheme(Theme.LIGHT)` 后同样触发 → `isDarkTheme()` 仍为 False。
  - `test_watch_exception_does_not_crash`：`watch` 抛 `RuntimeError` → 线程结束，`assertLogs("dataforge.ui.theme", "ERROR")`。
  - `test_theme_module_has_no_terminate`：读取 `theme.py` 与 `app.py` 源码，断言不含 `terminate(`。
  - `test_snapshot_cleared_after_run`、`test_zero_output_without_issues_shows_info`（patch `InfoBar.info`/`success`，断言调用的是 `info`）。
  - 所有改动全局主题的测试在 `tearDown` 中 `setTheme(Theme.AUTO)` 复位（包括阶段 1 遗留的 `test_theme_switch_while_running`）。
  - 删除或改写阶段 1 中启动真实 `SystemThemeListener` 并 `terminate()` 的两个主题测试，改用假 `watch`。
- [ ] **Step 2:** 运行上述测试 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` 连续运行 3 次 → 全部 PASS 且无挂起（单次超过 120 秒视为失败）。
- [ ] **Step 5:** Commit：`fix(v3): daemon theme watcher, no thread terminate; phase 1 carry-over`

---

### Task 2: 编码识别、文本读写、原子写出

**Files:**
- Create: `src/dataforge/fileio/atomic.py`, `src/dataforge/fileio/encoding.py`, `src/dataforge/fileio/text_io.py`
- Modify: `src/dataforge/core/result.py`, `src/dataforge/tools/width_convert.py`, `docs/tools/README.md`
- Test: `tests/dataforge/test_encoding.py`, `tests/dataforge/test_text_io.py`, `tests/dataforge/test_core.py`

**Interfaces:**
- Produces:
  - `core/result.py`：`@dataclass(frozen=True) class EncodingQuestion: path: str; previews: dict[str, str]`（编码名 → 前 5 行文本）；`Result.encoding_questions: list[EncodingQuestion]`（默认空）；`Result.ask_encoding(self, path: str | Path, previews: dict[str, str]) -> None`；`Result.extend(self, other: Result) -> None`（四个列表依次追加，stats 相加）。`Result.ok` 仍只看 `errors`。
  - `fileio/atomic.py`：`@contextmanager def atomic_path(target: Path) -> Iterator[Path]`：yield 同目录临时路径 `.<stem>.<pid>.<随机8位>.tmp<suffix>`（保留扩展名）；正常退出 `os.replace(tmp, target)`；任何异常（含 `BaseException`）删除临时文件并重新抛出。
  - `fileio/encoding.py`：
    - `class EncodingError(DataForgeError)`；`class AmbiguousEncodingError(EncodingError)`，属性 `previews: dict[str, str]`。
    - `LEGACY_ENCODINGS = ("cp932", "gbk")`；`ENCODING_LABELS = {"utf-8-sig": "UTF-8 (BOM)", "utf-8": "UTF-8", "cp932": "日文 (cp932)", "gbk": "中文 (GBK)"}`
    - `@dataclass(frozen=True) class EncodingDecision: encoding: str; note: str | None`
    - `def detect_encoding(data: bytes, forced: str | None = None) -> EncodingDecision`：`forced` 非空→按它解码，失败抛 `EncodingError(f"无法按 {forced} 解码")`，成功 `note=None`；以 `\xef\xbb\xbf` 开头→`utf-8-sig`；整体能按 `utf-8` 解码→`utf-8`（空字节串也是 `utf-8`）；否则分别试 `cp932`、`gbk`：只一种成功→`EncodingDecision(enc, f"自动识别为 {ENCODING_LABELS[enc]}")`；两种都成功→`AmbiguousEncodingError("无法确定编码（日文 cp932 / 中文 GBK 均可解码）", previews={enc: 前5行})`；都失败→`EncodingError("无法识别文件编码（已尝试 UTF-8、cp932、GBK）")`。
  - `fileio/text_io.py`：
    - `def read_text(path: Path, encoding: str | None = None) -> tuple[str, EncodingDecision]`：读字节 → `detect_encoding` → 解码；换行原样保留（不做 universal newline 转换）。
    - `def write_csv_rows(rows: Iterable[Sequence[str]], path: Path, *, delimiter: str = ",") -> None`：经 `atomic_path` 以 `utf-8-sig`、`newline=""`、`csv.writer(..., delimiter=delimiter, lineterminator="\r\n")` 写出（与 v2 `csv.writer` 默认一致）。
    - `def write_text(text: str, path: Path) -> None`：经 `atomic_path` 以 `utf-8-sig`、`newline=""` 写出。
  - `width_convert.py`：删除自有临时文件逻辑，改用 `atomic_path`（行为不变，原有测试必须仍通过）。
  - `docs/tools/README.md` 新增"编码规则"一节（照抄上面的识别顺序与提示文字）。

- [ ] **Step 1: 写失败测试**

```python
GBK_ONLY = "SUBJID,姓名\nA001,张伟\n".encode("gbk")
CP932_ONLY = "SUBJID,ｼﾒｲ\nA001,ﾔﾏﾀﾞ\n".encode("cp932")
AMBIGUOUS = "テスト医師\n".encode("cp932")
UNDECODABLE = b"A,\x81\n"

def test_bom(self):        self.assertEqual(detect_encoding(b"\xef\xbb\xbfa,b\n").encoding, "utf-8-sig")
def test_utf8_and_empty(self):
    self.assertEqual(detect_encoding("中文".encode("utf-8")).encoding, "utf-8")
    self.assertEqual(detect_encoding(b"").encoding, "utf-8")
def test_gbk_only(self):   d = detect_encoding(GBK_ONLY); self.assertEqual((d.encoding, d.note), ("gbk", "自动识别为 中文 (GBK)"))
def test_cp932_only(self): self.assertEqual(detect_encoding(CP932_ONLY).encoding, "cp932")
def test_ambiguous(self):
    with self.assertRaises(AmbiguousEncodingError) as cm: detect_encoding(AMBIGUOUS)
    self.assertEqual(set(cm.exception.previews), {"cp932", "gbk"})
    self.assertEqual(cm.exception.previews["cp932"], "テスト医師\n")
def test_undecodable(self):
    with self.assertRaises(EncodingError) as cm: detect_encoding(UNDECODABLE)
    self.assertNotIsInstance(cm.exception, AmbiguousEncodingError)
def test_forced(self):
    self.assertEqual(detect_encoding(AMBIGUOUS, forced="gbk").encoding, "gbk")
    with self.assertRaises(EncodingError): detect_encoding(UNDECODABLE, forced="utf-8")
def test_preview_limited_to_5_lines(self): # 10 行歧义文本 → 每个 preview 恰好 5 行
```

  `test_text_io.py`：`test_read_text_keeps_crlf`（`"a\r\nb\r\n"` 读回不变）；`test_write_csv_rows_bom_and_crlf`（写 `[["a","b,c"],["1",""]]` → 字节为 `b'\xef\xbb\xbfa,"b,c"\r\n1,\r\n'`）；`test_atomic_path_cleans_up_on_error`（`with atomic_path(t): 写一半后 raise` → 目标不存在、目录无残留）；`test_atomic_path_cleans_up_on_cancelled`（抛 `Cancelled` 同样清理）。
  `test_core.py`：`test_result_extend`、`test_ask_encoding_not_error`（`ask_encoding` 后 `ok` 仍为 True）。

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现；把 `width_convert.py` 改用 `atomic_path`。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): encoding detection, text io and atomic writes`

---

### Task 3: 工作表拆分后端（与 XLSX→CSV 共用）

**Files:**
- Create: `src/dataforge/tools/sheet_split.py`, `tests/golden/sheet_split/make_fixtures.py`, `tests/golden/sheet_split/basic/{params.json,input/book.xlsx,expected/*.csv}`, `docs/tools/sheet_split.md`
- Modify: `tests/dataforge/golden.py`
- Test: `tests/dataforge/test_sheet_split.py`

**Interfaces:**
- Consumes: `plan_output`、`write_csv_rows`、`Result`、`CancelToken`
- Produces:
  - `SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")`
  - `def sanitize_sheet_name(name: str) -> str` 与 `def sheet_rows(ws) -> list[list[str]]`：**逐行移植** v2 `src/utils/xlsx_sheet_splitter_service.py` 的 `_sanitize_sheet_name`、`_make_unique_name`、`_read_sheet_as_strings`、`_cell_to_string`、`_format_excel_date` 及其辅助函数，行为完全一致（非法字符与控制字符→`_`，去尾部空格和点，空名→`Sheet`，保留名加 `_`；日期按 `number_format` 渲染；去掉末尾空行和空列；数字用 `str(value)`）。
  - `def export_workbook(src: Path, *, all_sheets: bool, output_dir: Path | None, result: Result, cancel: CancelToken) -> None`：`load_workbook(src, read_only=True, data_only=True)`，用完关闭；`all_sheets=False` 只导出第一个 sheet，输出名 `<stem>.csv`；`all_sheets=True` 每个 sheet 输出 `<stem>_<安全sheet名>.csv`（同一工作簿内安全名重复时按 v2 规则加 `_n`）；每个输出经 `plan_output(src, new_name=..., output_dir=...)` 再 `write_csv_rows`，`result.add_output`、`result.count("sheets")`；每个 sheet 前 `cancel.raise_if_cancelled()`。读文件 `PermissionError` → `result.fail(src, "无法读取文件（可能已在 Excel 中打开）")`；其他异常 → `result.fail(src, f"读取失败：{e}")`；单个 sheet 写出失败 → `result.fail(src, f"{sheet}: {e}")` 并继续下一个 sheet。
  - `@dataclass class SplitOptions: output_dir: Path | None = None`
  - `def run(files: list[Path], options: SplitOptions, progress: ProgressFn, cancel: CancelToken) -> Result`：空列表抛 `DataForgeError("请先选择要拆分的 Excel 文件")`；每个文件 `progress(i, total, name)` 后 `cancel.raise_if_cancelled()`，再 `export_workbook(..., all_sheets=True)`；`stats["files"]` 计成功文件数。

- [ ] **Step 1: 写失败测试**：
  - `test_sanitize`：`("a/b:c", "a_b_c")`、`("CON", "CON_")`、`("x. ", "x")`、`("", "Sheet")`、`("..", "Sheet")`。
  - `test_split_names_and_dates`：工作簿含 sheet `"数据"`（A1 日期 `2020-03-04`、格式 `yyyy/mm/dd`；B1 `datetime(2020,3,4,10,5)`、格式 `yyyy-mm-dd hh:mm`）与 sheet `"a/b"`；末尾 2 行空行、末尾 1 列空列 → 输出 `book_数据.csv`、`book_a_b.csv`；第一份第一行为 `2020/03/04,2020-03-04 10:05`；无尾随空行空列。
  - `test_duplicate_sanitized_names`：sheet `"a/b"` 与 `"a:b"` → `book_a_b.csv`、`book_a_b_1.csv`。
  - `test_existing_output_gets_suffix`：已有 `book_数据.csv` → 新输出 `book_数据_1.csv`。
  - `test_empty_sheet_writes_empty_csv`：输出文件字节为 `b"\xef\xbb\xbf"`。
  - `test_permission_error_continues`：两个文件，patch `load_workbook` 第一次抛 `PermissionError` → 1 条错误（消息如上）、第二个文件有输出。
  - `test_first_sheet_only`：`export_workbook(..., all_sheets=False)` → 只有 `book.csv`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 标准样例：`make_fixtures.py` 用字面值构造 `input/book.xlsx`（覆盖日期格式、带时间、sheet 名非法字符、尾随空行空列、中文 sheet 名），并**手写**期望 CSV 字节写入 `expected/`；`params.json` 为 `{}`；`ADAPTERS["sheet_split"]` 复制输入后以 `output_dir=输出目录` 运行。
- [ ] **Step 5:** `docs/tools/sheet_split.md`（规则同上；标明 v3 变更：输出名带原文件名前缀 `<stem>_`）。
- [ ] **Step 6:** `.venv/Scripts/python.exe -m pytest tests -q` → PASS
- [ ] **Step 7:** Commit：`feat(v3): sheet split backend with golden samples`

---

### Task 4: 格式转换后端（4 种模式）

**Files:**
- Create: `src/dataforge/tools/format_convert.py`, `tests/golden/format_convert/make_fixtures.py`, `tests/golden/format_convert/<case>/...`（每种模式至少 1 个用例）, `docs/tools/format_convert.md`
- Modify: `tests/dataforge/golden.py`
- Test: `tests/dataforge/test_format_convert.py`

**Interfaces:**
- Consumes: Task 2（`read_text`、`write_csv_rows`、`write_text`、`atomic_path`、`AmbiguousEncodingError`、`EncodingError`）、Task 3（`export_workbook`、`sheet_split.SUPPORTED_EXTENSIONS`）、`plan_output`
- Produces:
  - `class ConvertMode(str, Enum)`：`CSV_TO_XLSX = "csv_to_xlsx"`、`XLSX_TO_CSV = "xlsx_to_csv"`、`CSV_TO_BOM = "csv_to_bom"`、`CSV_UNQUOTE = "csv_unquote"`
  - `MODE_EXTENSIONS: dict[ConvertMode, tuple[str, ...]]`：XLSX_TO_CSV → `(".xlsx", ".xlsm")`，其余 → `(".csv",)`
  - `@dataclass class FormatOptions: mode: ConvertMode; output_dir: Path | None = None; overwrite_source: bool = False; all_sheets: bool = False; encoding: str | None = None; encodings: dict[str, str] = field(default_factory=dict)`（`encodings` 以 `str(path)` 为键，优先于 `encoding`）
  - `def run(files: list[Path], options: FormatOptions, progress: ProgressFn, cancel: CancelToken) -> Result`
  - 每个 CSV 文件：取 `options.encodings.get(str(f), options.encoding)` → `read_text`；`AmbiguousEncodingError` → `result.ask_encoding(f, e.previews)`；`EncodingError` → `result.fail(f, str(e))`；`decision.note` 非空 → `result.warn(f, decision.note)`。
  - 规则：
    - **CSV_TO_XLSX**：`csv.reader`（分隔符 `,`）逐行读，**原样**写入新工作簿单个 sheet `Sheet1`，所有写入的单元格 `number_format = "@"`，行长不一时按原样；输出 `<stem>.xlsx`；经 `atomic_path` 保存。（v2 用 pandas，行长不一时会报错——【变更】改为原样保留。）`overwrite_source` 在此模式无效。
    - **XLSX_TO_CSV**：`export_workbook(f, all_sheets=options.all_sheets, ...)`；`overwrite_source` 无效。
    - **CSV_TO_BOM**：已是 `utf-8-sig` → `result.warn(f, "已是 UTF-8 BOM，未生成文件")`，不输出；否则文本原样（换行不变）`write_text` 到 `<stem>_bom.csv`（`overwrite_source=True` 时写回原文件）。
    - **CSV_UNQUOTE**：分隔符用 `csv.Sniffer().sniff(text[:1024], delimiters=",\t;|")`，失败用 `,`；按标准 CSV 解析后写出，字段内容原样保留（首尾空格、内部引号都不动）；仅当字段含分隔符、`\r`、`\n` 或以 `"` 开头时才加引号（内部 `"` 双写），这类字段计数 `n`，`n > 0` 时 `result.warn(f, f"{n} 个字段含分隔符、换行或以引号开头，已保留引号")`；行尾 `\r\n`、编码 `utf-8-sig`；输出 `<stem>_unquoted.csv`（`overwrite_source=True` 时写回原文件）。
  - 每个文件：`progress(i, total, name)` → `cancel.raise_if_cancelled()`；CSV_TO_XLSX 每 5000 行再检查一次取消；单文件其他异常 → `result.fail(f, f"转换失败：{e}")`，`PermissionError` → `"无法写入输出文件（可能已被其他程序打开）"`；空 `files` → `DataForgeError("请先选择要转换的文件")`；扩展名不符合 `MODE_EXTENSIONS[mode]` 的文件 → `result.fail(f, "文件类型与所选模式不符")`。

- [ ] **Step 1: 写失败测试**

```python
def test_csv_to_xlsx_ragged_and_multiline(self):
    # 输入（utf-8）：'a,b\r\n1,"x\ny",extra\r\n2\r\n'
    # → Sheet1: A1="a" B1="b"; A2="1" B2="x\ny" C2="extra"; A3="2"; 所有已写单元格 number_format == "@"
def test_csv_to_xlsx_keeps_leading_zero(self):     # "id\n007\n" → A2 == "007"
def test_xlsx_to_csv_first_and_all(self):          # all_sheets False → book.csv；True → book_S1.csv, book_S2.csv
def test_bom_converts_gbk_and_skips_bom(self):
    # gbk 文件 → <stem>_bom.csv 字节 == "﻿".encode("utf-8") + 原文本.encode("utf-8")，warnings 含 "自动识别为 中文 (GBK)"
    # 已有 BOM 的文件 → 无输出，警告 "已是 UTF-8 BOM，未生成文件"
def test_bom_keeps_line_endings(self):             # "a\r\nb\n" 原样
def test_unquote_lossless(self):
    # 输入：'"a","  b ","c""d"\r\n"x,y","1"\r\n'
    # → 输出字节：b'\xef\xbb\xbfa,  b ,c"d\r\n"x,y",1\r\n'；警告 "1 个字段含分隔符、换行或以引号开头，已保留引号"
def test_unquote_tab_delimiter(self):              # '"a"\t"b"\n' → 'a\tb\r\n'
def test_ambiguous_becomes_question(self):         # AMBIGUOUS 字节的 csv → 无输出、无错误、encoding_questions 1 条
def test_override_resolves_question(self):         # options.encodings={str(f): "cp932"} → 有输出、无问题
def test_undecodable_is_error(self):               # UNDECODABLE → errors 1 条，消息含 "无法识别文件编码"
def test_empty_csv(self):                          # 0 字节 → CSV_TO_XLSX 生成空 Sheet1；CSV_TO_BOM 生成只含 BOM 的文件
def test_japanese_filename(self):                  # "データ.csv" → "データ.xlsx"
def test_cancel_mid_batch_leaves_no_partial(self):
    # 3 个文件，progress 在 current==2 时 cancel → 抛 Cancelled；第 1 个输出存在，第 2、3 个不存在，目录无 *.tmp*
def test_overwrite_ignored_for_xlsx_modes(self):   # CSV_TO_XLSX + overwrite_source=True → 仍生成 .xlsx，源 csv 不变
def test_wrong_extension_fails(self):
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 标准样例：每种模式一个用例目录（`csv_to_xlsx/`、`xlsx_to_csv_all/`、`csv_to_bom_gbk/`、`csv_unquote/`），`params.json` 写明 `{"mode": ..., "all_sheets": ...}`；`ADAPTERS["format_convert"]` 读取 `params` 构造 `FormatOptions`（输出目录设为输出文件夹）；输入与期望用 `make_fixtures.py` 以字面值生成，期望不得由被测代码生成。
- [ ] **Step 5:** `docs/tools/format_convert.md`：四种模式的规则、输出名、编码规则引用 README，标注 v3 变更（行长不一原样保留、去引号无损、BOM 不覆盖原文件、已是 BOM 不重复生成）。
- [ ] **Step 6:** `.venv/Scripts/python.exe -m pytest tests -q` → PASS
- [ ] **Step 7:** Commit：`feat(v3): format convert backend (4 modes) with golden samples`

---

### Task 5: 获取字段后端

**Files:**
- Create: `src/dataforge/tools/field_extract.py`, `tests/golden/field_extract/make_fixtures.py`, `tests/golden/field_extract/basic/...`, `docs/tools/field_extract.md`
- Modify: `tests/dataforge/golden.py`
- Test: `tests/dataforge/test_field_extract.py`

**Interfaces:**
- Consumes: Task 2、`iter_input_files`、`plan_output`、`write_csv_rows`
- Produces:
  - `SUMMARY_NAME = "file_fields_summary.csv"`；`SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xlsm")`
  - `@dataclass class FieldOptions: header_row: int = 1; include_subfolders: bool = False; output_dir: Path | None = None; encoding: str | None = None; encodings: dict[str, str] = field(default_factory=dict)`
  - `def run(folder: Path, options: FieldOptions, progress: ProgressFn, cancel: CancelToken) -> Result`
  - 规则：
    - 校验：`folder` 不是目录 → `DataForgeError("请选择有效的文件夹")`；`header_row < 1` → `DataForgeError("列名行号必须大于等于 1")`。
    - 文件：`iter_input_files([folder], SUPPORTED_EXTENSIONS, recursive=include_subfolders)`，再排除文件名匹配 `^file_fields_summary(_\d+)?\.csv$`（不区分大小写）的文件；无文件 → `DataForgeError("该文件夹中没有 CSV 或 Excel 文件")`。
    - CSV：`read_text` → `csv.reader`（分隔符 `,`），取第 `header_row` 行的原始值作为字段名（不改名、不去重、空值保留为 `""`）；行数不足 → 无字段。【变更】v2 经 pandas 会把重复列改成 `a.1`、空列名改成 `Unnamed: 0`。
    - Excel：`load_workbook(read_only=True, data_only=True)`，每个 sheet 取第 `header_row` 行，去掉尾部空单元格，`None` → `""`，字段名格式 `f"{sheet}: {value}"`（与 v2 一致）；读取失败 → `result.fail`。
    - 编码歧义/失败处理与 Task 4 相同（`ask_encoding` / `fail` / note → `warn`）。
    - 汇总：表头 `["文件名", "字段名"]`；文件名为相对 `folder` 的路径（`/` 用 `Path.as_posix()`）；每个字段一行；无字段或出错的文件写一行 `[相对路径, ""]`；被询问编码的文件不写入。输出 `plan_output(folder / SUMMARY_NAME, new_name=SUMMARY_NAME, output_dir=options.output_dir)`（默认在所选文件夹内，重名加 `_1`）。
    - `stats`：`files`（成功读取的文件数）、`fields`（字段总数）。
    - 每个文件 `progress(i, total, 相对路径)` 后检查取消。

- [ ] **Step 1: 写失败测试**：
  - `test_csv_and_excel_fields`：`a.csv`（`"id,name,id,\n1,2,3,4\n"`）与 `b.xlsx`（sheet `S1` 表头 `x,y` 加尾部空格子）→ 汇总行依次：`a.csv,id`、`a.csv,name`、`a.csv,id`、`a.csv,""`、`b.xlsx,S1: x`、`b.xlsx,S1: y`；`stats == {"files": 2, "fields": 6}`。
  - `test_header_row_2`。
  - `test_previous_summary_excluded`：文件夹中已有 `file_fields_summary.csv` 与 `file_fields_summary_1.csv` → 不作为输入，新汇总为 `file_fields_summary_2.csv`。
  - `test_subfolders_relative_names`：`sub/c.csv` → 文件名列为 `sub/c.csv`。
  - `test_empty_csv_writes_blank_row`。
  - `test_lock_files_skipped`：`~$b.xlsx` 不出现。
  - `test_ambiguous_csv_question`：歧义文件不写入汇总，`encoding_questions` 1 条。
  - `test_invalid_inputs`：非目录、`header_row=0`、空文件夹各抛 `DataForgeError`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** 标准样例与 `ADAPTERS["field_extract"]`（`params` 含 `header_row`、`include_subfolders`；输入目录本身作为 `folder`，`output_dir` 设为输出目录）。
- [ ] **Step 5:** `docs/tools/field_extract.md`。
- [ ] **Step 6:** `.venv/Scripts/python.exe -m pytest tests -q` → PASS
- [ ] **Step 7:** Commit：`feat(v3): field extract backend with golden samples`

---

### Task 6: 公共界面件与编码歧义重跑流程

**Files:**
- Create: `src/dataforge/ui/components/output_location.py`, `folder_picker.py`, `encoding_field.py`, `encoding_dialog.py`
- Modify: `src/dataforge/ui/components/tool_page.py`, `src/dataforge/ui/components/result_panel.py`, `src/dataforge/ui/pages/width_convert_page.py`
- Test: `tests/dataforge/test_components_phase2.py`, `tests/dataforge/test_tool_page.py`, `tests/dataforge/test_width_convert.py`

**Interfaces:**
- Consumes: Task 2 `EncodingQuestion`、`Result.extend`、`ENCODING_LABELS`
- Produces:
  - `class OutputLocationField(QWidget)`：从 `WidthConvertPage` 原样抽出（ComboBox"与原文件相同 / 指定文件夹…"、原生目录对话框、取消时回退、路径 `CaptionLabel`）；`output_dir() -> Path | None`；`set_output_dir(path: Path | None)`；`setEnabled` 照常可用。`WidthConvertPage` 改用它，原有页面测试必须仍通过。
  - `class FolderPicker(QWidget)`：只读 `LineEdit` + `PushButton("选择文件夹")`（`QFileDialog.getExistingDirectory`）+ 接受拖入单个文件夹；信号 `folder_changed(object)`；`folder() -> Path | None`；`set_folder(path: Path | None)`；`set_locked(locked: bool)`。
  - `class EncodingField(ComboBox)`：选项依次 `自动识别`、`UTF-8`、`UTF-8 (BOM)`、`日文 (cp932)`、`中文 (GBK)`；`encoding() -> str | None`（自动识别为 None，其余对应 `utf-8`、`utf-8-sig`、`cp932`、`gbk`）；`set_encoding(value: str | None)`。
  - `class EncodingChoiceDialog(MessageBoxBase)`：标题 `选择编码`，显示文件名、每个候选编码一个 `RadioButton`（文字取 `ENCODING_LABELS`）和一个只读 `PlainTextEdit` 预览，默认选中第一个；`CheckBox("本批其余文件也用此编码")`；`chosen() -> str`；`apply_to_rest() -> bool`。
  - `def ask_encodings(parent: QWidget, questions: list[EncodingQuestion], dialog_factory=EncodingChoiceDialog) -> dict[str, str]`：逐个询问；某次勾选"本批其余文件也用此编码"后，其余文件中预览里含该编码的直接采用；用户点取消则停止询问，返回已答部分。
  - `ToolPage` 新增：
    - 钩子 `build_retry_job(self, encodings: dict[str, str]) -> JobFn | None`，默认返回 `None`（不支持重跑）。
    - `_on_finished`：若 `result.encoding_questions` 非空且本页 `build_retry_job` 被子类重写：先 `result_panel.show_result(result)`，调用 `ask_encodings(self.window(), result.encoding_questions)`；有答案则保存 `self._carry = result`（去掉已答的问题）、`job = build_retry_job(answers)` 并 `runner.submit`；重跑结束时把 `self._carry.extend(新结果)` 作为最终结果显示，再按原规则发 InfoBar 与 `run_succeeded`（快照仍是第一次提交时的）。用户全部取消 → 按当前结果结束，未答文件以警告"未选择编码，已跳过"列出。
    - `ResultPanel.show_result` 在"警告"页列出 `encoding_questions`（`path: 需要选择编码`），计入警告数。
  - 本任务只用测试中的假子类验证重跑流程；真实页面在 Task 7、8 接入。

- [ ] **Step 1: 写失败测试**：
  - `test_output_location_extracted`：`WidthConvertPage` 现有测试全部通过；`OutputLocationField` 取消对话框回退到"与原文件相同"。
  - `test_folder_picker_drop_and_lock`。
  - `test_encoding_field_values`：5 个选项对应的 `encoding()` 值。
  - `test_ask_encodings_apply_to_rest`：3 个问题，用假对话框在第 1 个返回 `("gbk", apply_to_rest=True)` → 只弹 1 次，结果 3 个都是 `gbk`。
  - `test_ask_encodings_cancel_stops`：第 2 个取消 → 返回 1 个答案。
  - `test_retry_flow_merges_results`：假子类第一次 job 返回 1 个输出 + 1 个问题，重跑 job 返回 1 个输出；patch `ask_encodings` 返回答案 → 最终 `ResultPanel` 结果页显示 2 个输出，`run_succeeded` 只发 1 次，载荷为第一次提交时的快照。
  - `test_retry_not_offered_without_hook`：未重写 `build_retry_job` 的页面不弹窗，问题作为警告显示。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → PASS
- [ ] **Step 5:** Commit：`feat(v3): shared output/folder/encoding widgets and encoding retry flow`

---

### Task 7: 工作表拆分页、获取字段页

**Files:**
- Create: `src/dataforge/ui/pages/sheet_split_page.py`, `src/dataforge/ui/pages/field_extract_page.py`
- Modify: `src/dataforge/ui/registry.py`
- Test: `tests/dataforge/test_sheet_split_page.py`, `tests/dataforge/test_field_extract_page.py`, `tests/dataforge/test_registry_theme_layout.py`

**Interfaces:**
- Consumes: Task 3、5、6
- Produces:
  - 登记（插在 `TOOLS` 最前，FILES 组）：`sheet_split` 工作表拆分，描述 `每个工作表导出为一个 CSV`，`FluentIcon.LAYOUT`；`field_extract` 获取字段，描述 `批量读取 CSV / Excel 表头并汇总`，`FluentIcon.SEARCH`。（`format_convert` 在 Task 8 登记并排在 FILES 组第一位。）
  - `SheetSplitPage(ToolPage)`：输入 `FileInputCard("Excel 文件", sheet_split.SUPPORTED_EXTENSIONS)`；参数 `OutputLocationField`；主按钮 `开始拆分`；`capture_state = {"files", "output_dir"}`；`summary` 同全角页规则。
  - `FieldExtractPage(ToolPage)`：输入 `FolderPicker`；参数 `ResponsiveForm`：`列名行号` `SpinBox`（1–1000，默认 1）、`包含子文件夹` `CheckBox`、`编码` `EncodingField`、`汇总输出位置` `OutputLocationField`（"与原文件相同"在此页显示为"所选文件夹"）；主按钮 `开始获取`；重写 `build_retry_job`（把答案并入 `FieldOptions.encodings` 后**整体重跑**一次——因为汇总是一个文件；重跑前删除第一次生成的汇总文件，保证只留一份汇总）；`capture_state = {"folder", "header_row", "include_subfolders", "encoding", "output_dir"}`；`summary` = 文件夹名。
  - 运行成功后结果面板列出汇总文件路径。

- [ ] **Step 1: 写失败测试**：每页 `test_build_job_validation`（无输入 → `InfoBar.warning` 且返回 None）、`test_state_roundtrip`（`restore_state(capture_state())` 后控件值一致，缺失路径返回列表）、`test_run_end_to_end`（真实 `JobRunner` 跑临时目录，`wait_until` 完成，输出存在）；获取字段页 `test_retry_rewrites_single_summary`（歧义 CSV + patch `ask_encodings` → 最终目录只有一个 `file_fields_summary*.csv`，且含该文件字段）；注册表 `test_every_page_importable` 覆盖新条目、`test_files_group_order`（FILES 组当前顺序为 `sheet_split`、`field_extract`）。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → PASS
- [ ] **Step 5:** Commit：`feat(v3): sheet split and field extract pages`

---

### Task 8: 格式转换页

**Files:**
- Create: `src/dataforge/ui/pages/format_convert_page.py`
- Modify: `src/dataforge/ui/registry.py`
- Test: `tests/dataforge/test_format_convert_page.py`, `tests/dataforge/test_registry_theme_layout.py`

**Interfaces:**
- Consumes: Task 4、6
- Produces:
  - 登记：`format_convert` 格式转换，描述 `CSV↔XLSX、转 UTF-8 BOM、去引号`，`FluentIcon.SYNC`，FILES 组第一位。
  - `FormatConvertPage(ToolPage)`：
    - 模式选择 `SegmentedWidget`（窄布局下仍可用即可），四项文字依次 `CSV → XLSX`、`XLSX → CSV`、`转 UTF-8 BOM`、`去除引号`，下方 `CaptionLabel` 一句说明当前模式。
    - 输入 `FileInputCard`，切换模式时扩展名过滤随 `MODE_EXTENSIONS` 变化；已选文件中与新模式不符的移除，并 `InfoBar.info` 告知移除了几个。（`FileInputCard` 若无法改扩展名，在本任务内为其增加 `set_extensions(extensions: tuple[str, ...]) -> list[Path]`（返回被移除的文件）并补测试。）
    - 参数：`编码`（`EncodingField`，仅 CSV 三种模式显示）、`全部工作表`（`CheckBox`，仅 XLSX→CSV 显示，默认不勾）、`输出位置`（`OutputLocationField`）、`覆盖原文件`（`CheckBox`，仅 `转 UTF-8 BOM` 与 `去除引号` 显示；勾选时禁用输出位置、运行前 `MessageBox` 二次确认，确认文字含"无法撤销"）。
    - 主按钮文字：`开始转换`。
    - 重写 `build_retry_job`：只对回答了的文件构造 `FormatOptions(encodings=answers, ...)` 重跑。
    - `capture_state = {"mode", "files", "encoding", "all_sheets", "output_dir", "overwrite_source"}`；`summary` = `f"{模式文字} · {首个文件名} 等 {n} 个文件"`（n=1 时省略"等…"）。

- [ ] **Step 1: 写失败测试**：`test_mode_switch_updates_controls`（四种模式下编码/全部工作表/覆盖选项的可见性）、`test_mode_switch_drops_mismatched_files`、`test_overwrite_confirm_cancel_aborts`、`test_state_roundtrip`、`test_run_end_to_end_each_mode`（四种模式各跑一次临时文件）、`test_encoding_retry_only_answered_files`（两个 CSV，一个歧义 → 重跑只处理歧义文件，最终 2 个输出、无 `_1` 重复文件）。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → PASS
- [ ] **Step 5:** Commit：`feat(v3): format convert page`

---

### Task 9: 阶段验收

- [ ] **Step 1:** `.venv/Scripts/python.exe -m pytest tests -q` 连续 3 次全部通过、无挂起。
- [ ] **Step 2:** `grep -rnE "setStyleSheet|#[0-9A-Fa-f]{6}\b|processEvents|DontUseNativeDialog|setFixedWidth|print\(|terminate\(" src/dataforge` → 无匹配；`grep -rnE "TODO|FIXME|skip\(|\.only" src/dataforge tests/dataforge` → 无匹配。
- [ ] **Step 3:** 给作者的手动验收清单（由作者在桌面上执行）：
  1. 格式转换四种模式各转一个真实文件，用 Excel / 记事本打开检查。
  2. 用一个 GBK 的 CSV 和一个含 `テスト医師` 的 Shift-JIS CSV 做"转 UTF-8 BOM"：前者自动识别，后者弹出编码选择；勾选"本批其余文件也用此编码"后同批其余歧义文件不再询问。
  3. 工作表拆分一个多 sheet 的真实工作簿；获取字段对一个真实文件夹运行两次，确认第二次不把第一次的汇总当输入。
  4. 关闭程序（含任务运行中关闭）不卡顿。
- [ ] **Step 4:** Commit（如有修正）：`fix(v3): phase 2 acceptance fixes`
