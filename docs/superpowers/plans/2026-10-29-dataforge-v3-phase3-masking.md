# DataForge Studio v3 · 阶段 3：数据模糊化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先清掉阶段 2 遗留项，再完成"数据模糊化（SDTM Pattern1）"：配置档与 v2 迁移、日期规则（保留时间、歧义日期列由用户选顺序）、扫描、执行（SUBJID 清空）、两步式页面、标准样例和规则说明。

**Architecture:** 后端 `dataforge.tools.masking`（`profile` / `scan` / `execute` 三个模块）不依赖 Qt，日期解析并入 `dataforge/dates.py`；扫描与执行都通过全局 `JobRunner` 在后台运行。`ToolPage` 增加"辅助任务"（kind≠`"run"`）支持，扫描就是辅助任务：结果以 `Result.data` 携带 `ScanReport` 回到页面，不弹完成提示、不记最近使用。执行是普通 `"run"` 任务。

**Tech Stack:** Python 3.13（`.venv`），PySide6 6.12，PySide6-Fluent-Widgets 1.11.3，标准库 `csv` / `decimal` / `json`。**本阶段不使用 pandas**（v2 测试改写时也去掉 pandas）。

**Spec:** `docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md`（§5.4、§6.2、§6.3、§7.4、§8）
**Carry-over:** `docs/superpowers/plans/2026-10-29-dataforge-v3-phase2-carryover.md`（"Final: parked" 与 "Phase-3 notes" 在 Task 1 处理）

## Global Constraints

- 阶段 1、2 的全部 Global Constraints 继续有效：后端无 Qt、无 `print`；界面无 QSS/hex/固定宽度/`processEvents`/`DontUseNativeDialog`；同一时间一个任务；v2 代码（`src/gui`、`src/utils`、`src/main.py`）不动；任务代码里不创建 QObject、不调用 `gc.collect()`。
- 编码识别沿用阶段 2（`read_text` / `detect_encoding`）；CSV 写出 `utf-8-sig` + `\r\n`（`write_csv_rows`）；所有输出原子写入。
- spec §7.4 中没有标【变更】的规则以 v2 `src/utils/data_masking_service.py` 为准；本计划写明的偏差均为已裁定的变更。
- 配置 section 名固定 `data_masking_pattern1`；`subject_sort`、`date_output_format`、`partial_date_policy` 读取时忽略、保存时不写。默认值只在 `MaskingProfile` dataclass 里写一份。
- 新工具登记：id `masking`，名称 `数据模糊化`，说明 `SDTM Pattern1：扫描 → 配置 → 执行`，组 `ToolGroup.BUSINESS`，图标 `FluentIcon.HIDE`。
- 标准样例数据必须是虚构的；期望输出由 `make_fixtures.py` 中的字面值生成。
- 不改 `dates.to_iso8601`（日期转换的样例依赖它）。
- 测试命令：`.venv/Scripts/python.exe -m pytest tests -q`。
- 提交信息结尾：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

1. **USUBJID 为空或带首尾空格的行**→ 空 USUBJID 行删除；`" A001 "` 按去空格后的值匹配受试者并替换为新 ID（v2 会静默丢掉这些行）。（测试见 Task 5）
2. **扫描时某个 CSV 正被 Excel 打开**→ 该文件报"无法读取文件（可能已在 Excel 中打开）"，其余文件照常扫描，扫描不通过。（测试见 Task 4）
3. **DM 的 INVNAM 列整列为空**→ 不替换（输出仍为空），执行摘要不出现 INVNAM 一行。（测试见 Task 5）
4. **两个子文件夹里各有一个 DM.csv / 同名 AE.csv**→ 扫描报错，不允许执行（否则输出文件互相覆盖）。（测试见 Task 4）
5. **扫描后用户又改了文件**→ 点"开始处理"时提示重新扫描，不按旧扫描结果执行；执行中途取消→不留下 `masked_output_*` 文件夹。（测试见 Task 5、Task 7）

---

## 文件结构

```
src/dataforge/core/result.py                    修改：Result.data
src/dataforge/fileio/paths.py                   修改：临时文件跳过规则收紧
src/dataforge/tools/field_extract.py            修改：CSV 读取 PermissionError 提示
src/dataforge/ui/jobs.py                        修改：模块说明补"任务代码禁止事项"
src/dataforge/ui/components/encoding_dialog.py  修改：本次会话记住上次选择
src/dataforge/ui/components/tool_page.py        修改：重跑统计/日志；辅助任务 kind
src/dataforge/ui/shell.py                       修改：USES_CONFIG 页面传入 ConfigStore
src/dataforge/config/store.py                   修改：ConfigStore.root()
src/dataforge/config/legacy.py                  新增：通用 v2 配置迁移
src/dataforge/dates.py                          修改：模糊化日期解析与偏移
src/dataforge/tools/masking/__init__.py         新增
src/dataforge/tools/masking/profile.py          新增：MaskingProfile、加载/保存
src/dataforge/tools/masking/table.py            新增：read_table()、find_column()、is_blank()
src/dataforge/tools/masking/scan.py             新增：ScanReport、scan()、scan_signature()、export_report()
src/dataforge/tools/masking/execute.py          新增：build_mapping()、describe_plan()、run()
src/dataforge/ui/pages/masking/__init__.py      新增
src/dataforge/ui/pages/masking/page.py          新增：MaskingPage
src/dataforge/ui/pages/masking/scan_view.py     新增：扫描结果表 + 歧义日期列顺序选择
src/dataforge/ui/pages/masking/profile_form.py  新增：配置表单
src/dataforge/ui/registry.py                    修改：登记 masking
tests/dataforge/golden.py                       修改：masking 适配器
tests/golden/masking/...                        新增样例 + make_fixtures.py
tests/golden/format_convert/overwrite_source/   新增样例
docs/tools/masking.md                           新增
docs/tools/README.md                            修改：params 键
```

---

### Task 1: 阶段 2 遗留项

**Files:**
- Modify: `src/dataforge/ui/components/tool_page.py`, `src/dataforge/ui/components/encoding_dialog.py`, `src/dataforge/tools/field_extract.py`, `src/dataforge/fileio/paths.py`, `src/dataforge/ui/jobs.py`, `tests/dataforge/golden.py`（仅当新样例需要）, `docs/tools/README.md`
- Create: `tests/golden/format_convert/overwrite_source/{params.json,input/,expected/}`（由 `tests/golden/format_convert/make_fixtures.py` 生成）
- Test: `tests/dataforge/test_tool_page.py`, `tests/dataforge/test_components_phase2.py`, `tests/dataforge/test_field_extract.py`, `tests/dataforge/test_paths.py`

**Interfaces:**
- Produces:
  - `ToolPage._start_retry`：每个被拒绝（未回答）的编码问题除了现有警告"未选择编码，已跳过"，再 `result.count("skipped")`。
  - `ToolPage._on_started`：重跑（`self._retrying` 为 True）时**不**清空结果区，改为 `append_log("—— 重新处理编码有歧义的文件 ——")`。
  - `encoding_dialog.py`：模块级 `_last_choice: str | None`；`EncodingChoiceDialog.__init__(self, parent, question, default: str | None = None)`，`default` 在 previews 中时预选它，否则预选第一个；`ask_encodings(..., dialog_factory)` 以 `dialog_factory(parent, question, _last_choice)` 创建对话框，每次确定后 `_last_choice = chosen`；`reset_encoding_memory() -> None` 供测试复位。只预选，不跳过询问。
  - `field_extract.py`：CSV 读取时的 `PermissionError` 也报 `无法读取文件（可能已在 Excel 中打开）`。
  - `paths.iter_input_files`：只跳过与 `atomic_path` 命名完全一致的临时文件，正则 `^\..+\.\d+\.[0-9a-f]{8}\.tmp(\.[^.]*)?$`。
  - `jobs.py` 模块说明末尾加一句：任务函数不得创建 QObject、不得调用 `gc.collect()`（垃圾回收只在主线程由 `MainThreadGarbageCollector` 做）。
  - 新样例 `format_convert/overwrite_source`：模式 CSV_TO_BOM，`"overwrite_source": true`，输入一个无 BOM 的 UTF-8 CSV，期望输出为同名带 BOM 文件。
  - `docs/tools/README.md`：把"未选择编码的文件由重新处理计数"改为"计入 skipped"。

- [ ] **Step 1: 写失败测试**
  - `test_declined_encoding_counts_as_skipped`：两个歧义文件，假 `ask_encodings` 只回答第一个 → 最终 `result.stats["skipped"]` 比首次运行多 1。
  - `test_retry_keeps_first_run_log`：首次运行日志中的一行在重跑结束后仍在日志页，且出现分隔行。
  - `test_retry_failure_keeps_first_outputs`：重跑任务抛 `DataForgeError` → `run_succeeded` 恰好发出 1 次（参数为首次提交时的快照），结果区显示首次的输出，`InfoBar.error` 被调用。
  - `test_retry_cancel_keeps_first_outputs`：重跑中取消 → 同上，`InfoBar.info` 被调用。
  - `test_dialog_preselects_last_choice`：假工厂记录收到的 `default`；第一次调用选 `gbk` 后，第二次 `ask_encodings` 的工厂收到 `default == "gbk"`；`setUp` 调 `reset_encoding_memory()`。
  - `test_real_dialog_default_selected`：`EncodingChoiceDialog(win, q, default="gbk").chosen() == "gbk"`，`deleteLater` 后 `drain_deleted`。
  - `test_csv_permission_error_message`：patch `read_text`（或 `Path.read_bytes`）对 CSV 抛 `PermissionError` → 错误消息等于 `无法读取文件（可能已在 Excel 中打开）`。
  - `test_temp_skip_rule`：`.a.123.0123abcd.tmp.csv` 被跳过；`.tmpdata.csv`、`.x.tmp.csv` 不被跳过。
- [ ] **Step 2:** 运行上述测试 → FAIL
- [ ] **Step 3:** 实现；生成 `overwrite_source` 样例（`make_fixtures.py` 增加该样例），`test_golden.py` 自动发现它。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`fix(v3): phase 2 carry-over (retry stats/log, encoding memory, temp skip rule)`

---

### Task 2: v2 配置迁移与 MaskingProfile

**Files:**
- Create: `src/dataforge/config/legacy.py`, `src/dataforge/tools/masking/__init__.py`, `src/dataforge/tools/masking/profile.py`
- Modify: `src/dataforge/config/store.py`
- Test: `tests/dataforge/test_config_legacy.py`, `tests/dataforge/test_masking_profile.py`

**Interfaces:**
- Produces:
  - `ConfigStore.root(self) -> dict[str, Any]`：整个配置的深拷贝；读不了（`OSError`）返回 `{}`。
  - `config/legacy.py`：
    - `def load_section_with_legacy(store: ConfigStore, section: str, legacy_keys: Collection[str], legacy_files: Sequence[Path] = ()) -> dict[str, Any]`。顺序：① `store.section(section)` 非空 → 返回它；② `store.root()` 顶层含任一 `legacy_keys` → 返回 root 的拷贝（v2 "整个文件就是配置档"的旧格式，不回写）；③ 依次读 `legacy_files`：存在、按 `utf-8-sig` 解析为 JSON 对象、含任一 `legacy_keys` → `store.update_section(section, data)` 后返回 data（旧文件本身不改不删）；读/解析失败跳过；④ 返回 `{}`。
    - `def legacy_file_candidates(file_name: str, *extra_dirs: Path) -> list[Path]`：打包运行（`sys.frozen`）时 `Path(sys.executable).resolve().parent / file_name`；再加 v2 源码目录 `Path(__file__).resolve().parents[2] / "utils" / file_name`（即 `src/utils/`，v2 服务模块所在处）；再加 `extra_dirs` 各自 `/ file_name`；去重保序。阶段 4 的 EDC 复用这两个函数。
  - `tools/masking/profile.py`：
    - `CONFIG_SECTION = "data_masking_pattern1"`，`LEGACY_FILE_NAME = "data_masking_pattern1_config.json"`，`REMOVED_KEYS = frozenset({"subject_sort", "date_output_format", "partial_date_policy"})`
    - `@dataclass class RuleStep: op: str; value: Any`
    - `@dataclass class MaskingProfile`，字段与默认值照抄 v2 `Pattern1Profile`，去掉 3 个 `REMOVED_KEYS`：`studyid_value="[UAT]CIRCULATE"`、`subject_limit=100`、`usubjid_mode="sequential"`、`rule_chain_steps=[remove_prefix 4, remove_suffix 0, prepend "SKLT", append ""]`、`sequential_prefix="TEST"`、`sequential_width=4`、`sequential_start=1`、`date_shift_years=-2`、`age_shift_years=-2`、`date_detect_sample_size=200`、`date_detect_min_non_empty=20`、`date_detect_success_ratio=0.8`、`doctor_fields=["INVNAM"]`、`doctor_value="テスト医師"`、`doctor_replace_enabled=True`、`site_field="SITEID"`、`site_value="テスト施設"`、`site_replace_enabled=True`、`age_field="AGE"`、`include_subjid=True`。
    - `LEGACY_KEYS: frozenset[str]` = 全部字段名 ∪ `REMOVED_KEYS`。
    - `MaskingProfile.from_dict(raw: Mapping[str, Any]) -> MaskingProfile`：转换规则照抄 v2 `from_dict` / `_coerce_bool`（坏值保留默认值）；未知键与 `REMOVED_KEYS` 忽略；`usubjid_mode` 不是 `sequential`/`rule_chain` 时取 `sequential`。
    - `MaskingProfile.to_dict(self) -> dict[str, Any]`（`rule_chain_steps` 为 `[{"op", "value"}]`）。
    - `def load_profile(store: ConfigStore, legacy_files: Sequence[Path] = ()) -> MaskingProfile`、`def save_profile(store: ConfigStore, profile: MaskingProfile) -> bool`。

- [ ] **Step 1: 写失败测试**（全部用临时目录里的 `ConfigStore(path, legacy_path=None)`）
  - `test_section_round_trip_keeps_other_sections`：先写 `{"app": {"theme": "dark"}}`，`save_profile` 后两个 section 都在。
  - `test_removed_keys_ignored_and_not_written`：section 含 `subject_sort` 等 3 键 → 加载成功；`save_profile` 后文件里不再有这 3 键。
  - `test_v2_values_kept`：section `{"include_subjid": false, "subject_limit": "30", "doctor_fields": [" INVNAM ", "", "ICINVNAM"]}` → `include_subjid is False`、`subject_limit == 30`、`doctor_fields == ["INVNAM", "ICINVNAM"]`。
  - `test_bad_values_fall_back`：`subject_limit: "abc"` → 100；`include_subjid: "maybe"` → True；`include_subjid: "no"` → False；`usubjid_mode: "x"` → `"sequential"`。
  - `test_root_level_legacy_profile`：配置文件顶层就是 `{"studyid_value": "S1"}` → `load_profile(...).studyid_value == "S1"`，文件内容不变。
  - `test_legacy_file_migrated`：`legacy_files=[tmp/"data_masking_pattern1_config.json"]`（内容 `{"subject_limit": 5}`）→ 加载得 5；新配置文件出现 `data_masking_pattern1` section；旧文件字节不变。
  - `test_section_wins_over_legacy_file`、`test_broken_legacy_file_skipped`（旧文件内容 `{`）。
  - `test_candidates`：非打包时包含 `src/utils/data_masking_pattern1_config.json`；patch `sys.frozen=True`、`sys.executable` 后第一项为 exe 同目录。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): legacy config migration and masking profile`

---

### Task 3: 模糊化日期规则（`dataforge/dates.py`）

**Files:**
- Modify: `src/dataforge/dates.py`
- Test: `tests/dataforge/test_dates_masking.py`

**Interfaces:**
- Produces（全部纯函数，`to_iso8601` 不动）：
  - `class SlashOrder(Enum): DAY_FIRST = "dmy"; MONTH_FIRST = "mdy"`
  - `class SlashKind(Enum): NOT_SLASH, DAY_FIRST_ONLY, MONTH_FIRST_ONLY, SAME, AMBIGUOUS, INVALID`
  - `def slash_kind(text: str) -> SlashKind`：只看去空格后完整匹配 `^(\d{1,2})/(\d{1,2})/(\d{4})$` 的值（a/b/yyyy）；`d/m` 与 `m/d` 两种读法分别判断是否为有效日期：都有效且 a≠b → `AMBIGUOUS`；都有效且 a=b → `SAME`；只一种有效 → 对应 `*_ONLY`；都无效 → `INVALID`；不匹配 → `NOT_SLASH`。
  - `@dataclass(frozen=True) class ParsedDate: value: date; partial: bool; suffix: str`
  - `def parse_mask_date(text: str, order: SlashOrder | None = None) -> ParsedDate | None`，对去空格后的文本 `t`：
    1. 完整日期 `^(\d{4})[-/](\d{1,2})[-/](\d{1,2})`，其后必须是：结尾、`Z` 结尾、或 `[T ]\d{1,2}:\d{1,2}` 开头的时间；`suffix = t[日期部分之后:]`（原文照留，如 `T13:30:00+09:00`、` 10:30`、`Z`）。
    2. `^(\d{4})[-/](\d{1,2})$` → 当月 1 日，`partial=True`；`^(\d{4})$` → 1 月 1 日，`partial=True`。
    3. 斜杠日期：`*_ONLY` / `SAME` 按唯一读法；`AMBIGUOUS` 按 `order`，`order` 为 None 时返回 None。
    4. 日历无效（如 `2024-13-01`）返回 None。
  - `def is_date_like(text: str) -> bool`：任一读法能解析即为 True（歧义值算日期，保证全是歧义值的列仍被识别为日期列）。
  - `def shift_years(value: date, years: int) -> date | None`：年份加 `years`；日大于新月份天数时取当月最后一天；新年份不在 1–9999 返回 None。
  - `class DateOutcome(Enum): BLANK, SHIFTED, FILLED, UNPARSED`
  - `def mask_date(text: str, years: int, order: SlashOrder | None) -> tuple[str, DateOutcome]`：空白（去空格为空，或小写为 `nan`，与 v2 一致）→ 原值 + `BLANK`；无法解析或偏移后越界 → 原值 + `UNPARSED`；否则输出 `YYYY-MM-DD` + `suffix`，`partial` 为 `FILLED`，否则 `SHIFTED`。

- [ ] **Step 1: 写失败测试**（`years=-2`，除非注明）

```python
CASES = [
    ("2024-06-15T13:30:00", None, "2022-06-15T13:30:00", SHIFTED),
    ("2024-06-15 13:30", None, "2022-06-15 13:30", SHIFTED),
    ("2024-06-15T13:30:00Z", None, "2022-06-15T13:30:00Z", SHIFTED),
    ("2024-06-15T13:30:00+09:00", None, "2022-06-15T13:30:00+09:00", SHIFTED),
    ("2024/6/5", None, "2022-06-05", SHIFTED),
    ("2024/06/05 08:00:00", None, "2022-06-05 08:00:00", SHIFTED),
    ("2024-05", None, "2022-05-01", FILLED),
    ("2024", None, "2022-01-01", FILLED),
    ("2024-02-29", None, "2022-02-28", SHIFTED),
    ("25/03/2024", None, "2022-03-25", SHIFTED),
    ("03/25/2024", None, "2022-03-25", SHIFTED),
    ("05/05/2024", None, "2022-05-05", SHIFTED),
    ("03/04/2024", DAY_FIRST, "2022-04-03", SHIFTED),
    ("03/04/2024", MONTH_FIRST, "2022-03-04", SHIFTED),
    ("03/04/2024", None, "03/04/2024", UNPARSED),
    ("25/03/2024", MONTH_FIRST, "2022-03-25", SHIFTED),   # 唯一读法优先于所选顺序
    ("2024-13-01", None, "2024-13-01", UNPARSED),
    ("2024-06-15T", None, "2024-06-15T", UNPARSED),
    ("abc", None, "abc", UNPARSED),
    ("", None, "", BLANK),
    ("NaN", None, "NaN", BLANK),
    ("0001-03-01", None, "0001-03-01", UNPARSED),
]
def test_mask_date_cases(self): ...  # subTest 逐条断言 mask_date(text, -2, order) == (expected, outcome)
def test_leap_forward(self): self.assertEqual(mask_date("2024-02-29", 4, None)[0], "2028-02-29")
def test_slash_kind(self):  # "03/04/2024"→AMBIGUOUS, "25/03/2024"→DAY_FIRST_ONLY, "03/25/2024"→MONTH_FIRST_ONLY,
                            # "05/05/2024"→SAME, "31/31/2024"→INVALID, "2024-01-01"→NOT_SLASH
def test_is_date_like_counts_ambiguous(self): self.assertTrue(is_date_like("03/04/2024"))
def test_to_iso8601_unchanged(self): self.assertEqual(to_iso8601("2024/2/30"), "2024-02")
```

- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): masking date parsing with kept time and slash order`

---

### Task 4: 扫描后端

**Files:**
- Create: `src/dataforge/tools/masking/table.py`, `src/dataforge/tools/masking/scan.py`
- Modify: `src/dataforge/core/result.py`
- Test: `tests/dataforge/test_masking_scan.py`, `tests/dataforge/test_core.py`

**Interfaces:**
- Consumes: Task 2 `MaskingProfile`；Task 3 `is_date_like`、`slash_kind`、`SlashOrder`；阶段 2 `read_text`、`AmbiguousEncodingError`、`EncodingError`。
- Produces:
  - `Result.data: Any = None`：任务附带的结构化结果；`extend` 不处理它。
  - `table.py`：
    - `def is_blank(value: str) -> bool`：去空格为空或小写为 `nan`（与 v2 一致）。
    - `def find_column(header: Sequence[str], name: str) -> int | None`：第一个不区分大小写相等的列（不去空格）。
    - `@dataclass class Table: header: list[str]; rows: list[list[str]]; encoding: str; note: str | None`
    - `def read_table(path: Path, encoding: str | None) -> Table`：`read_text` 后 `csv.reader(io.StringIO(text, newline=""))`；空行（`[]`）跳过；短行右侧补 `""` 到表头长度；无表头 → `DataForgeError("文件为空")`；某行字段多于表头 → `DataForgeError(f"第 {reader.line_num} 行字段数多于表头")`。编码异常原样抛出。
  - `scan.py`：
    - `@dataclass(frozen=True) class ScanSettings: sample_size: int = 200; min_non_empty: int = 20; ratio: float = 0.8`；`ScanSettings.from_profile(p: MaskingProfile) -> ScanSettings`。
    - `@dataclass class FileScan: path: Path; file_name: str; encoding: str; row_count: int; unique_usubjid_count: int; non_empty_fields: list[str]; empty_fields: list[str]; date_fields: list[str]`
    - `@dataclass class AmbiguousColumn: file_name: str; column: str; ambiguous: int; day_first_only: int; month_first_only: int`
    - `@dataclass class ScanReport: files: list[FileScan]; dm_file: str | None; dm_first_usubjid: str | None; subjects: list[str]; ambiguous_columns: list[AmbiguousColumn]; settings: ScanSettings; errors: list[str]; warnings: list[str]; signature: str`；属性 `processable -> bool`（无错误且 `subjects` 非空）；`def to_dict(self, date_orders: Mapping[tuple[str, str], SlashOrder] | None = None) -> dict[str, Any]`。
    - `def scan_signature(paths: Sequence[Path], settings: ScanSettings, encoding: str | None, encodings: Mapping[str, str]) -> str`：对 `[(str(p), size, mtime_ns) 按路径排序]`、settings、encoding、排序后的 encodings 做 JSON 后取 sha256 hex；`stat` 失败的文件 size/mtime 记 -1。
    - `def scan(paths: Sequence[Path], settings: ScanSettings, encoding: str | None, encodings: Mapping[str, str], progress: ProgressFn, cancel: CancelToken) -> Result`：`result.data` 为 `ScanReport`；report 的每条错误/警告同时写入 `result.fail/warn`（路径为文件名，无文件时为 `""`）；`encodings` 以 `str(path)` 为键，优先于 `encoding`。
    - `def export_report(report: ScanReport, target: Path) -> Path`：`.csv` → 列 `file_name,row_count,unique_usubjid_count,non_empty_fields,empty_fields,date_fields`（列表用 `|` 连接，`write_csv_rows`）；其他扩展名 → JSON。
  - JSON 格式（`to_dict`，执行时写成 `pattern1_scan_report.json`）：`json.dumps(d, ensure_ascii=False, indent=2) + "\n"`，UTF-8 无 BOM，`\n` 换行，原子写入。键依次为 `dm_file`、`dm_first_usubjid`、`subject_count`、`subjects`、`date_detect`（`sample_size`、`min_non_empty`、`ratio`）、`files`（每项 `file_name`、`encoding`、`row_count`、`unique_usubjid_count`、`non_empty_fields`、`empty_fields`、`date_fields`）、`ambiguous_date_columns`（每项 `file_name`、`column`、`ambiguous`、`day_first_only`、`month_first_only`、`order`：`"dmy"`/`"mdy"`/`null`）、`errors`、`warnings`。**只存文件名，不存绝对路径和时间。**
- 扫描规则（照 v2，括号内为本阶段裁定）：
  1. 只取存在的 `.csv`（不区分大小写），去重保序；为空 → 错误 `未选择任何 CSV 文件`。
  2. （新增）文件名不区分大小写重复 → 错误 `文件名重复：{name}（输出时会互相覆盖）`。
  3. 逐个文件：进度 `progress(i, total, name)`，每个文件前 `cancel.raise_if_cancelled()`；`AmbiguousEncodingError` → `result.ask_encoding(path, previews)` 且错误 `未确定编码：{name}`；`EncodingError`/`DataForgeError` → 错误 `{name}：{message}`；`PermissionError` → 错误 `{name}：无法读取文件（可能已在 Excel 中打开）`；其他 `OSError` → `{name}：读取失败（{exc}）`；均继续下一个文件。编码 `note` → 警告。
  4. 缺 USUBJID → 错误 `文件缺少 USUBJID 列：{name}`。有值字段 = 至少一个非空白值的列（表头顺序），其余为空字段；受试者去重数 = 去空格非空白值的集合大小。
  5. 日期列：对每个有值字段，取去空格非空白值的前 `max(1, sample_size)` 个；`is_date_like` 命中比例 ≥ 阈值即为日期列；阈值 = `ratio` 限制在 [0,1]，样本数 < `max(1, min_non_empty)` 时阈值为 1.0。
  6. （新增）对每个日期列统计**全部**非空白值的 `slash_kind`：`AMBIGUOUS` 数 > 0 → 记 `AmbiguousColumn`，警告 `{column} 列有 {n} 个日期无法判断是 日/月 还是 月/日，请选择顺序`；`DAY_FIRST_ONLY` 与 `MONTH_FIRST_ONLY` 都 > 0 → 警告 `{column} 列同时有只能按 日/月 和只能按 月/日 解读的日期，请检查数据`。
  7. DM：文件名大写等于 `DM.CSV` 的个数 ≠ 1 → 错误 `DM.csv 必须且只能有 1 个`；DM 的 USUBJID 去空格非空白值排序（按 Unicode 码位）去重为 `subjects`，为空 → 错误 `DM.csv 中没有有效的 USUBJID`；`dm_first_usubjid` 为 DM 行顺序中第一个。
  8. `stats`：`files`（成功读取的文件数）、`subjects`。

- [ ] **Step 1: 写失败测试**（`_write(name, text, encoding="utf-8-sig")` 写临时 CSV）
  - `test_basic_report`：DM（USUBJID 依次 `S2,S1,S3`，含 `DMDTC`、空列 `ARM`）+ AE → `processable`，`subjects == ["S1","S2","S3"]`，`dm_first_usubjid == "S2"`，DM 的 `empty_fields == ["ARM"]`，`date_fields` 含 `DMDTC`。
  - `test_missing_usubjid_blocks`、`test_two_dm_files_error`（两个子文件夹各一个 `dm.csv`，同时有"文件名重复"和"DM.csv 必须且只能有 1 个"两条错误）、`test_duplicate_domain_names_error`。
  - `test_permission_error_other_files_scanned`：patch `read_text` 对 AE 抛 `PermissionError` → 错误含 `无法读取文件（可能已在 Excel 中打开）`，DM 仍出现在 `report.files`。
  - `test_ambiguous_encoding_asks`：AE 用 `"USUBJID,AETERM\nS1,テスト医師\n".encode("cp932")` → `result.encoding_questions` 含 AE，`processable` 为 False；传 `encodings={str(ae): "cp932"}` 再扫 → 无问题，`FileScan.encoding == "cp932"`。
  - `test_all_ambiguous_column_is_date_column`：一列 20 个值全为 `0d/0m/2024` 形式的歧义日期 → 是日期列，且出现在 `ambiguous_columns`，`ambiguous == 20`。
  - `test_detection_thresholds`：5 个值中 4 个日期（样本 < 20 → 要求 100%）→ 不是日期列；25 个值中 20 个日期（0.8）→ 是日期列。
  - `test_ragged_rows`：短行补空；长行 → 错误含 `字段数多于表头`。
  - `test_signature_changes_on_mtime`：`os.utime` 改 mtime 后签名不同；settings 改变签名不同。
  - `test_report_json_has_no_absolute_paths`：`json.dumps(report.to_dict())` 不含临时目录路径。
  - `test_cancel`：`CancelToken` 预先取消 → `Cancelled`。
  - `test_result_data_not_extended`（`test_core.py`）：`a.extend(b)` 后 `a.data` 不变。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): masking scan backend`

---

### Task 5: 执行后端、标准样例、规则说明

**Files:**
- Create: `src/dataforge/tools/masking/execute.py`, `tests/golden/masking/make_fixtures.py`, `tests/golden/masking/{sequential_basic,rule_chain_ambiguous}/...`, `docs/tools/masking.md`
- Modify: `tests/dataforge/golden.py`, `docs/tools/README.md`
- Test: `tests/dataforge/test_masking_execute.py`（并把 v2 `tests/test_data_masking_service.py` 的 6 个用例按新规则改写进来，不用 pandas；v2 测试文件本身不动）

**Interfaces:**
- Consumes: Task 2 `MaskingProfile`；Task 3 `mask_date`、`DateOutcome`、`SlashOrder`；Task 4 `ScanReport`、`read_table`、`find_column`、`is_blank`。
- Produces:
  - `def transform_subject_id(subject: str, profile: MaskingProfile, index: int) -> str`：顺序编号 `f"{prefix}{start + index:0{max(1, width)}d}"`；规则链照抄 v2 `_apply_rule_chain`（op 不区分大小写，未知 op 忽略，计数取非负整数）。
  - `def build_mapping(subjects: Sequence[str], profile: MaskingProfile) -> dict[str, str]`：新 ID 为空 → `DataForgeError(f"新 USUBJID 为空（原 ID：{old}）")`；重复 → `DataForgeError(f"新 USUBJID 重复：{前 10 个，用 ', ' 连接}")`。
  - `def shift_age(text: str, years: int) -> str`：空白原样；去空格后须匹配 `^[+-]?\d+(\.\d+)?$`，否则原样；用 `Decimal` 相加，小于 0 取 0，保留原小数位数（`"45"`→`"43"`，`"1"`→`"0"`，`"30.50"`→`"28.50"`，`"+45"`→`"43"`）。
  - `@dataclass class MaskOptions: profile: MaskingProfile; output_parent: Path | None = None; date_orders: dict[tuple[str, str], SlashOrder] = field(default_factory=dict); now: datetime | None = None`（键为 `(file_name, column)`；`now` 仅供测试固定文件夹时间戳）
  - `def missing_orders(report: ScanReport, date_orders: Mapping[tuple[str, str], SlashOrder]) -> list[AmbiguousColumn]`
  - `def describe_plan(report: ScanReport, profile: MaskingProfile, date_orders: Mapping[tuple[str, str], SlashOrder], output_parent: Path | None) -> list[str]`，文案固定：
    1. `受试者：保留 DM 排序后的前 {k} 个（共 {n} 个），其他受试者的行全部删除`
    2. 顺序编号 `USUBJID：顺序编号 {第一个新ID} … {最后一个新ID}`；规则链 `USUBJID：规则链，例如 {dm_first} → {新ID}`
    3. 勾选时 `SUBJID 列将被清空`，否则 `SUBJID 列保持不变`
    4. `STUDYID：全部改为 {studyid_value}`
    5. `日期：{m} 个日期列偏移 {years:+d} 年，时间部分保留`
    6. 仅当 DM 中该列有值且开关打开：`DM：{字段，用 "、" 连接} 改为 {doctor_value}`、`DM：{site_field} 改为 {site_value}`；DM 中年龄列有值时 `DM：{age_field} 偏移 {age:+d} 岁`
    7. 有未选顺序的列：`还有 {c} 个日期列需要选择 日/月 顺序`
    8. `输出：{output_parent 或 "DM.csv 所在文件夹"} 下新建 masked_output_<时间> 文件夹`
  - `def run(report: ScanReport, options: MaskOptions, progress: ProgressFn, cancel: CancelToken) -> Result`
- 执行规则：
  1. `not report.processable` → `DataForgeError("扫描未通过，无法执行")`；`missing_orders` 非空 → `DataForgeError(f"请先为 {c} 个日期列选择 日/月 顺序")`；`subject_limit < 1` → `DataForgeError("输出受试者数必须大于 0")`。
  2. 受试者 = `subjects[:subject_limit]`，`build_mapping`。
  3. 输出文件夹：父目录 = `output_parent` 或 DM.csv 所在目录；名称 `masked_output_{now:%Y%m%d_%H%M%S}`，已存在则 `_1`、`_2`…（自定义位置同样新建子文件夹）。先写入同目录临时文件夹 `tempfile.mkdtemp(prefix=f".{name}.", suffix=".tmp", dir=parent)`，全部成功后 `os.rename` 为最终名；任何异常（含 `Cancelled`）先 `shutil.rmtree(tmp, ignore_errors=True)` 再重新抛出。
  4. 逐个文件（`progress`，`cancel` 检查）：按 `FileScan.encoding` 重新 `read_table`，失败 → `DataForgeError(f"{name}：读取失败，请重新扫描（{message}）")`，整个执行中止。只保留 USUBJID 去空格后属于受试者集合的行，然后依次：USUBJID → 新 ID；勾选 `include_subjid` 且有 SUBJID 列 → 该列全部置 `""`；有 STUDYID 列 → 全部置 `studyid_value`；每个日期列 `mask_date(value, date_shift_years, date_orders.get((file_name, column)))` 并按结果计数；DM 文件再做：开关打开时 `doctor_fields` 中每个在 DM 扫描时有值的列、非空白单元格 → `doctor_value`，`site_field` 同理 → `site_value`；`age_field` 在 DM 扫描时有值 → `shift_age`。表头原样写出，文件名与输入相同。
  5. 每个日期列的 `UNPARSED` 数 > 0 → 警告（路径为文件名）`{column} 列有 {n} 个值无法识别为日期，已保持原样`。
  6. 另写 `usubjid_mapping.csv`（表头 `OLD_USUBJID,NEW_USUBJID`，按受试者顺序）和 `pattern1_scan_report.json`（`report.to_dict(options.date_orders)`）。
  7. `outputs` = 各域文件、映射文件、报告文件（最终文件夹内的路径）；`stats`：`files`、`subjects`、`rows`（保留的数据行总数）、`dates_shifted`（`SHIFTED`+`FILLED`）、`dates_filled`、`dates_unparsed`。
- 样例（数据虚构）。`params.json` 键：`profile`（传给 `MaskingProfile.from_dict` 的覆盖项）、`date_orders`（`{"AE.csv:AESTDTC": "dmy"}`）、`encodings`（同阶段 2，键为输入相对路径）。适配器：复制 input → `scan` → `run`，`output_parent` 为临时目录、`now=datetime(2026, 1, 2, 3, 4, 5)`；断言生成的文件夹名为 `masked_output_20260102_030405`，再把其中文件复制到 `output_dir` 供比较；`.json` 按字节比较。
  - `sequential_basic`：`subject_limit` 2；DM 3 个受试者（行顺序非排序）、INVNAM/SITEID/AGE 有值、一个整列为空的 `ICINVNAM`；AE 含：第 3 个受试者的行（应删除）、空 USUBJID 行（应删除）、`" S1 "` 行（应保留）、带时间与时区的日期、`YYYY` 与 `YYYY-MM`、`2024-02-29`、含逗号和换行的引号字段、SUBJID 列（应清空）、一个无法解析的日期值（产生警告）。
  - `rule_chain_ambiguous`：规则链（去前 4 位、加前缀 `SKLT`）；`include_subjid: false`；`doctor_replace_enabled: false`；AE 的 `AESTDTC` 含歧义斜杠日期，`date_orders` 选 `dmy`；AE 用 cp932 编码且内容只含半角片假名（自动识别为 cp932，不产生问题）。
- `docs/tools/masking.md`：按 README 模板写全扫描规则、执行规则、输出与报告格式、编码、边界情况；已知限制写明 spec 的两点（RELREC、SUPP 的 IDVARVAL 等列中的 USUBJID 不重新映射；没有 USUBJID 的试验设计域如 TS、TA 不支持），并写明 `nan` 文本按空白处理、4 位纯数字会被识别为年份。`README.md` 的 params 表增加 `profile`、`date_orders` 两行。

- [ ] **Step 1: 写失败测试**
  - `test_end_to_end_v2_rules`（改写 v2 `test_pattern1_default_infer_and_iso_output`）：`subject_limit=2` → 输出 USUBJID 集合 `{"TEST0001","TEST0002"}`；INVNAM 全为 `テスト医師`、ICINVNAM 不变；DMDTC 含 `2022-01-01`、`2022-05-01`；AESTDTC 含 `2022-06-15T13:30:00`（v2 为 `2022-06-15`，本阶段变更）；AE 的 SUBJID 全为 `""`（v2 为映射值，本阶段变更）。
  - `test_extra_doctor_fields_only_in_dm`、`test_dm_overrides_replace_only_non_empty_cells`、`test_dm_overrides_skip_when_disabled`（改写 v2 对应用例）。
  - `test_include_subjid_false_keeps_subjid`。
  - `test_whitespace_and_blank_usubjid`（Review Focus 1）。
  - `test_empty_invnam_column_not_replaced_and_not_described`（Review Focus 3）：DM 的 INVNAM 整列为空 → 输出仍为空，`describe_plan` 中没有含 `INVNAM` 的行。
  - `test_describe_plan_lines`：默认配置、5 个受试者 → 恰好等于按上面 8 条文案拼出的列表（第 7 条不出现）。
  - `test_missing_order_blocks`、`test_order_applied`（`dmy` 时 `03/04/2024` → `2022-04-03`）。
  - `test_duplicate_new_ids`（规则链去前 10 位 → 全为空串 → "新 USUBJID 为空"；去前 4 位后相同 → "新 USUBJID 重复"）。
  - `test_shift_age_values`：上面 4 个例子 + `"abc"` 原样 + `""` 原样。
  - `test_folder_conflict_suffix`：同一 `now` 运行两次 → 第二次为 `masked_output_20260102_030405_1`。
  - `test_cancel_leaves_no_folder`（Review Focus 5）：第 2 个文件的 progress 回调里取消 → `Cancelled`，父目录下无 `masked_output_*`，也无 `.masked_output_*` 临时文件夹。
  - `test_file_changed_after_scan_aborts`：扫描后把 AE 改成无法解码的字节 → `DataForgeError` 含 `请重新扫描`，且无输出文件夹。
  - `test_mapping_and_report_files`：映射文件字节等于 `"﻿OLD_USUBJID,NEW_USUBJID\r\nS1,TEST0001\r\nS2,TEST0002\r\n".encode("utf-8")`；报告 JSON 可解析且 `ambiguous_date_columns[0]["order"] == "dmy"`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现 `execute.py`；写 `make_fixtures.py` 生成两组样例；`golden.py` 加 `masking` 适配器；写文档。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS（含 `test_golden` 中 masking 两例）
- [ ] **Step 5:** Commit：`feat(v3): masking execution, golden samples and rules doc`

---

### Task 6: ToolPage 辅助任务与页面配置注入

**Files:**
- Modify: `src/dataforge/ui/components/tool_page.py`, `src/dataforge/ui/shell.py`
- Test: `tests/dataforge/test_tool_page.py`, `tests/dataforge/test_shell_smoke.py`

**Interfaces:**
- Consumes: Task 4 `Result.data`。
- Produces:
  - `ToolPage.current_job_kind(self) -> str`：默认 `"run"`；`_on_start_requested` 在 `build_job()` 之前调用它，并用 `submit_job(fn, kind)` 提交。
  - `ToolPage.submit_job(self, fn: JobFn, kind: str = "run") -> bool`：提交到 runner；成功时记录 `self._job_kind = kind`，只有 `kind == "run"` 才拍快照；失败时 `InfoBar.warning("无法开始", "已有任务正在运行")` 并返回 False。子类可直接调用（例如扫描后的自动重扫）。
  - `ToolPage.on_aux_finished(self, kind: str, result: Result) -> None`：默认 `raise NotImplementedError`。
  - 辅助任务（`kind != "run"`）完成时：`_end_run()` 后调用 `on_aux_finished(kind, result)`；**不**进入编码重跑流程、**不**弹完成/未生成文件 InfoBar、**不**发 `run_succeeded`。辅助任务失败/取消：与现在相同的 InfoBar（错误 / 已取消），不发 `run_succeeded`。`"run"` 任务的行为完全不变。
  - `shell._ensure_page`：页面类有类属性 `USES_CONFIG = True` 时以 `cls(spec, runner, config=self._config)` 构造，否则不变。`ToolPage` 本身不加此属性。

- [ ] **Step 1: 写失败测试**（测试内定义 `_AuxPage(ToolPage)`：`current_job_kind` 返回 `"scan"`，`build_job` 返回立即完成的任务，`on_aux_finished` 记录参数）
  - `test_aux_finish_calls_hook_without_recent_or_infobar`：patch `InfoBar.success/info/warning/error`，点主按钮 → 钩子收到 `("scan", result)` 且 `result.data` 原样，`run_succeeded` 未发出，四个 InfoBar 均未调用，`set_inputs_locked(False)` 最后被调用。
  - `test_aux_with_encoding_questions_skips_retry`：结果含 `encoding_questions` → 不调用 `ask_encodings`（patch 后断言未调用），钩子照常收到结果。
  - `test_aux_failure_shows_error_no_recent`。
  - `test_submit_job_busy_warns`：runner 忙时 `submit_job` 返回 False 并警告。
  - `test_run_kind_unchanged`：现有 `run` 流程测试全部仍通过（不改断言）。
  - `test_shell_injects_config`：在测试里注册一个 `USES_CONFIG = True` 的假页面类（patch `load_page_class`），打开后其 `config` 参数是 shell 的同一 `ConfigStore` 对象。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` → 全部 PASS
- [ ] **Step 5:** Commit：`feat(v3): auxiliary jobs on ToolPage and config injection`

---

### Task 7: 数据模糊化页面

**Files:**
- Create: `src/dataforge/ui/pages/masking/__init__.py`, `src/dataforge/ui/pages/masking/page.py`, `src/dataforge/ui/pages/masking/scan_view.py`, `src/dataforge/ui/pages/masking/profile_form.py`
- Modify: `src/dataforge/ui/registry.py`
- Test: `tests/dataforge/test_masking_page.py`, `tests/dataforge/test_registry_theme_layout.py`（登记相关断言）

**Interfaces:**
- Consumes: Task 2 `load_profile`/`save_profile`/`legacy_file_candidates`/`LEGACY_FILE_NAME`/`MaskingProfile`；Task 4 `scan`/`scan_signature`/`ScanSettings`/`export_report`；Task 5 `run`/`MaskOptions`/`describe_plan`/`missing_orders`/`transform_subject_id`；Task 6 `current_job_kind`/`submit_job`/`on_aux_finished`/`USES_CONFIG`；阶段 2 `FileInputCard`、`EncodingField`、`OutputLocationField`、`ResponsiveForm`、`ask_encodings`。
- Produces:
  - `registry`：`ToolSpec(id="masking", name="数据模糊化", description="SDTM Pattern1：扫描 → 配置 → 执行", group=ToolGroup.BUSINESS, icon=FluentIcon.HIDE, page="dataforge.ui.pages.masking.page:MaskingPage")`。
  - `class ProfileForm(QWidget)`（`profile_form.py`）：信号 `changed`（任意字段）、`scan_settings_changed`（3 个识别参数）；`set_profile(p: MaskingProfile)`、`profile() -> MaskingProfile`、`set_locked(bool)`、`set_preview_source(usubjid: str | None)`。内含两个 `ResponsiveForm`：`id_form`（输出受试者数 1–100000、STUDYID、编号方式 `ComboBox` 顺序编号/规则链、顺序编号的前缀/位数 1–10/起始号 0–999999、规则链的去前 N 位/去后 N 位 0–100/前加/后加——按方式用 `set_row_visible` 切换、`清空 SUBJID 列` 复选框、示例行 `DM 首条 USUBJID：{x} → {y}` 或 `扫描后显示示例`）和 `dm_form`（日期偏移年 −100–100、年龄偏移 −100–100 + `与日期偏移相同` 复选框（勾选时年龄偏移跟随且不可编辑；加载时两值相等则勾选）、替换医生字段 复选框 + 替换值、替换施设字段 复选框 + 替换值、`自定义字段名` 复选框——勾选后才可编辑医生字段（逗号分隔）/施设字段/年龄字段）；外加 `scan_form`（抽样数 10–20000、最少非空值 1–10000、命中比例 0.0–1.0 步长 0.05）。规则链 UI 读写 `rule_chain_steps` 中每种 op 的第一个，保存时写回标准 4 步。
  - `class ScanResultView(QWidget)`（`scan_view.py`）：信号 `orders_changed`、`rescan_requested`、`export_requested`；`show_report(report: ScanReport | None)`；`orders() -> dict[tuple[str, str], SlashOrder]`；`set_locked(bool)`。内容：状态行（`尚未扫描` / `扫描通过：{n} 个文件，DM 受试者 {m} 个` / `扫描未通过，请查看"警告"和结果区的错误`）、`TableWidget`（列：文件、编码、行数、受试者、有值字段数、空字段数、日期列）、每个 `AmbiguousColumn` 一行 `{file_name} · {column}（{ambiguous} 个无法判断）` + `ComboBox`（`请选择`、`日/月/年`、`月/日/年`）、按钮 `重新扫描`、`导出扫描报告…`（有报告时可用）。
  - `class MaskingPage(ToolPage)`：`USES_CONFIG = True`；`__init__(self, spec, runner, parent=None, config: ConfigStore | None = None)`（`None` 时用 `ConfigStore()`）；加载 `load_profile(config, legacy_file_candidates(LEGACY_FILE_NAME))`（测试 patch 本模块的 `legacy_file_candidates` 返回 `[]`）。
- 页面行为：
  - 卡片顺序：`输入`（`FileInputCard("SDTM CSV 文件", (".csv",))`）→ `扫描设置`（编码 `EncodingField`、`scan_form`、输出位置 `OutputLocationField(same_label="DM.csv 所在文件夹")`）→ `扫描结果`（`ScanResultView`）→ `受试者与 ID`（`id_form`）→ `日期与 DM`（`dm_form` + `恢复默认值` 按钮）→ `执行摘要`（每行一个 `BodyLabel`，无报告时显示 `扫描通过后显示`）。
  - 文件列表、编码、扫描参数任一变化 → 丢弃报告（`show_report(None)`），主按钮文字 `开始扫描`。编码歧义的回答存在 `self._encodings`（以 `str(path)` 为键），文件列表变化时只保留仍在列表中的路径。配置其他字段变化 → 只刷新执行摘要和示例行。
  - `current_job_kind()`：有报告且 `processable` → `"run"`，否则 `"scan"`。主按钮文字随之为 `开始处理` / `开始扫描`。
  - `build_job()`：没有文件 → `InfoBar.warning("请先添加文件", "请先添加 SDTM CSV 文件")` 返回 None。扫描：返回调用 `scan(...)` 的任务。执行：当前 `scan_signature` 与 `report.signature` 不同 → 丢弃报告、`InfoBar.warning("需要重新扫描", "文件或扫描设置已变化，请重新扫描")`、返回 None；`missing_orders` 非空 → `InfoBar.warning("请选择日期顺序", f"还有 {c} 个日期列需要选择 日/月 顺序")` 返回 None；`save_profile` 失败时 `InfoBar.warning("配置未保存", "配置保存失败，本次仍按当前设置执行")`；返回调用 `execute.run(...)` 的任务。
  - `on_aux_finished("scan", result)`：结果区显示 `result`；有 `encoding_questions` → `ask_encodings(self.window(), questions)`，回答并入 `self._encodings`，有回答则 `QTimer.singleShot(0, ...)` 以 `submit_job(扫描任务, "scan")` 自动整批重扫（不是只重扫这些文件：DM 与"只能有 1 个 DM"跨文件）；没有回答则显示该报告（不可执行）。否则 `show_report(result.data)`，刷新摘要和示例行，`processable` 时 `InfoBar.success("扫描通过", ...)`，否则 `InfoBar.warning("扫描未通过", 第一条错误)`。
  - 导出扫描报告：`QFileDialog.getSaveFileName`（筛选 `JSON (*.json);;CSV (*.csv)`）→ `export_report`；失败 `InfoBar.error`。
  - `capture_state()`：`{"files": [...], "encoding": ..., "output_dir": ...}`；`restore_state()` 恢复这三项（缺失文件返回在列表中）并丢弃报告。配置档不进最近使用。`summary()`：`f"{len(files)} 个 CSV"`。
  - `set_inputs_locked(locked)`：锁定文件输入、所有表单、扫描结果视图和恢复默认按钮。

- [ ] **Step 1: 写失败测试**（临时 `ConfigStore`；patch `legacy_file_candidates` → `[]`；patch `InfoBar.*`；用 `wait_until` 等任务结束）
  - `test_registered_in_business_group`：`get_tool("masking")` 的组、图标、名称；`load_page_class` 可导入。
  - `test_scan_then_execute`：DM+AE → 主按钮文字 `开始扫描`；点击 → 扫描完成后文字 `开始处理`，执行摘要含 `SUBJID 列将被清空`，`run_succeeded` 未发出；再点击 → 输出文件夹生成，`run_succeeded` 恰好 1 次；配置文件中出现 `data_masking_pattern1` section。
  - `test_file_change_invalidates_scan`：扫描后再加一个文件 → 文字回到 `开始扫描`。
  - `test_modified_file_requires_rescan`（Review Focus 5）：扫描后 `os.utime` 改 AE 的 mtime → 点 `开始处理` 不提交任务，`InfoBar.warning` 标题为 `需要重新扫描`，文字回到 `开始扫描`。
  - `test_ambiguous_order_required`：AE 有歧义日期列 → 不选时点击被拦截（警告标题 `请选择日期顺序`）；选 `日/月/年` 后执行，输出中 `03/04/2024` 变为 `2022-04-03`。
  - `test_encoding_question_triggers_full_rescan`：AE 为 cp932 歧义字节；patch 本模块 `ask_encodings` 返回 `{str(ae): "cp932"}` → 最终报告 `processable`，AE 的 `encoding == "cp932"`，`ask_encodings` 只被调用 1 次。
  - `test_v2_section_loaded`：配置预置 `{"data_masking_pattern1": {"include_subjid": false, "subject_sort": "x", "subject_limit": 7}}` → `清空 SUBJID 列` 未勾选、受试者数为 7。
  - `test_rule_chain_rows_toggle`：切到规则链后顺序编号行隐藏、规则链行显示。
  - `test_age_follows_date_shift`：勾选 `与日期偏移相同` 时改日期偏移 → 年龄偏移同步且不可编辑。
  - `test_locked_while_running`、`test_narrow_mode_compacts_forms`（`apply_layout_mode(LayoutMode.NARROW)` 后 3 个表单 `is_compact()`）。
  - 每个测试结束关闭页面并 `drain_deleted`。
- [ ] **Step 2:** 运行 → FAIL
- [ ] **Step 3:** 实现；登记到 registry（BUSINESS 组目前只有此工具）。
- [ ] **Step 4:** `.venv/Scripts/python.exe -m pytest tests -q` 连续 3 次 → 全部 PASS，无挂起
- [ ] **Step 5:** Commit：`feat(v3): data masking page`

---

### Task 8: 阶段验收

- [ ] **Step 1:** `.venv/Scripts/python.exe -m pytest tests -q` 连续 3 次 → 全部 PASS，单次不超过 120 秒。
- [ ] **Step 2:** 禁用模式检查（在 `src/dataforge` 下）：`grep -rnE "setStyleSheet|#[0-9a-fA-F]{6}|setFixedWidth|processEvents|DontUseNativeDialog|import pandas|print\(" src/dataforge` → 无输出。
- [ ] **Step 3:** 请作者手动验收（`.venv\Scripts\python -m dataforge`）：
  1. 用一套虚构或脱敏过的真实 SDTM CSV（含 DM）扫描 → 扫描结果表、日期列、受试者数正确；改一个扫描参数后主按钮回到"开始扫描"。
  2. 执行 → `masked_output_<时间>` 文件夹中各域文件、`usubjid_mapping.csv`、`pattern1_scan_report.json` 齐全；带时间的日期保留时间；SUBJID 已清空；INVNAM/SITEID/AGE 按设置处理。
  3. 含 `03/04/2024` 这类日期的列 → 扫描提示选择顺序，未选不能执行。
  4. cp932 日文文件 → 弹出编码选择，选完自动重扫，之后不再询问；下次弹窗默认选中上次的编码。
  5. 打开过 v2 并保存过模糊化配置的电脑上，v3 页面显示的是 v2 保存的值。
- [ ] **Step 4:** 更新 carry-over：新建 `docs/superpowers/plans/2026-10-29-dataforge-v3-phase3-carryover.md`（裁定与遗留项），Commit：`docs(v3): record phase 3 rulings and carry-over items`
