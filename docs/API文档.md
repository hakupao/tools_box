# DataForge Studio API 文档

适用版本：3.0.0。

本文只列出后端中对外稳定的接口，也就是以后用 C# 或 Rust 重写时需要逐一对照的部分：

- `dataforge.core`：结果、异常、进度与取消；
- `dataforge.fileio`：编码识别、读写文本和 CSV、输出路径、原子写入；
- `dataforge.dates`：日期解析和标准化；
- 每个工具的 options dataclass 和 `run` 入口；
- EDC 站点添加的执行接口、`run_segment` 和 `EdcSession`。

界面层（`dataforge.ui`）和配置读写（`dataforge.config`）不属于移植对照范围，见[开发文档](开发文档.md)。

各工具的业务规则（输入要求、默认值的含义、输出命名、边界情况）只写在 [docs/tools/](tools/README.md) 下的规则说明里，本文不重复。下面的签名都是从 `src/dataforge/` 源码中原样复制的。

## 通用约定

- 文件类工具的入口统一为 `run(inputs, options, progress, cancel) -> Result`。
- 后端不导入 Qt，不用 `print`，日志用 `logging.getLogger(__name__)`。工具入口不读应用配置：数据模糊化和 EDC 的配置由页面调用 `load_profile` / `load_config` 读出后作为参数传入。
- 参数非法（例如没有选文件）时抛 `DataForgeError`，整次运行不开始。
- 单个文件出错时记入 `Result.errors`，然后继续处理下一个文件。
- 在每个文件之间、或每处理一批行之后调用 `cancel.raise_if_cancelled()`。取消时抛 `Cancelled`，已经写完的文件保留，正在写的文件不留下半成品。
- 所有文件路径用 `pathlib.Path`；所有单元格值和 CSV 字段都按字符串处理。

## core

### 异常：`dataforge.core.errors`

```python
class DataForgeError(ValueError):
    """Expected input/business error; the message is user-facing (Chinese)."""

class Cancelled(BaseException):
    """Raised when a running task is cancelled by the user."""
```

- `DataForgeError` 的消息直接显示给用户，用中文写。
- `Cancelled` 故意继承 `BaseException`，这样工具里逐文件的 `except Exception` 不会把取消吞掉。工具代码不得捕获 `BaseException`；唯一例外是清理临时文件后立即原样 `raise`。

### 进度与取消：`dataforge.core.progress`

```python
ProgressFn = Callable[[int, int, str], None]

def no_progress(current: int, total: int, label: str) -> None: ...

class CancelToken:
    def __init__(self) -> None: ...
    def cancel(self) -> None: ...
    @property
    def cancelled(self) -> bool: ...
    def raise_if_cancelled(self) -> None: ...
```

- `ProgressFn(current, total, label)`：`label` 一般是正在处理的文件名。
- `CancelToken` 线程安全：界面线程调用 `cancel()`，工作线程调用 `raise_if_cancelled()`，已取消时抛 `Cancelled`。
- `no_progress` 是什么都不做的进度回调，测试和命令行调用时使用。

### 结果：`dataforge.core.result`

```python
@dataclass(frozen=True)
class FileIssue:
    path: str
    message: str

@dataclass(frozen=True)
class EncodingQuestion:
    path: str
    previews: dict[str, str]

@dataclass
class Result:
    outputs: list[Path] = field(default_factory=list)
    warnings: list[FileIssue] = field(default_factory=list)
    errors: list[FileIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    encoding_questions: list[EncodingQuestion] = field(default_factory=list)
    data: Any = None  # structured payload of the task; not merged by extend()

    @property
    def ok(self) -> bool: ...
    def add_output(self, path: Path) -> None: ...
    def warn(self, path: str | Path, message: str) -> None: ...
    def fail(self, path: str | Path, message: str) -> None: ...
    def count(self, key: str, n: int = 1) -> None: ...
    def ask_encoding(self, path: str | Path, previews: dict[str, str]) -> None: ...
    def extend(self, other: Result) -> None: ...
```

| 字段 / 方法 | 说明 |
| --- | --- |
| `outputs` | 生成的文件（或文件夹）路径，按生成顺序 |
| `warnings` / `errors` | 每条是 `FileIssue(path, message)`；`path` 可以为空字符串，表示不针对某个文件 |
| `stats` | 计数，键名见下文各工具 |
| `encoding_questions` | 编码有歧义、本次没有处理的文件。`previews` 的键是编码名（`cp932`、`gbk`），值是该编码下的前 5 行预览 |
| `data` | 工具特有的结构化结果，含义见各工具；没有时为 `None` |
| `ok` | `errors` 为空时为 `True` |
| `count(key, n)` | `stats[key] += n`，键不存在时从 0 开始 |
| `extend(other)` | 把 `other` 的 `outputs`、`warnings`、`errors`、`encoding_questions` 追加进来，`stats` 逐键相加；**不合并 `data`** |

编码重跑的约定：第一次运行时，有歧义的文件只记入 `encoding_questions`，不算失败。界面让用户为这些文件选好编码后，只用这些文件和选定的编码再运行一次，再把两次的 `Result` 合并（获取字段例外，见下文）。

## fileio

### 编码识别：`dataforge.fileio.encoding`

```python
LEGACY_ENCODINGS = ("cp932", "gbk")
ENCODING_LABELS = {
    "utf-8-sig": "UTF-8 (BOM)",
    "utf-8": "UTF-8",
    "cp932": "日文 (cp932)",
    "gbk": "中文 (GBK)",
}

class EncodingError(DataForgeError):
    """The file encoding cannot be determined or decoded."""

class AmbiguousEncodingError(EncodingError):
    """Both cp932 and GBK decode the data; the user must choose."""
    def __init__(self, message: str, previews: dict[str, str]) -> None: ...
    # self.previews: dict[str, str]

@dataclass(frozen=True)
class EncodingDecision:
    encoding: str
    note: str | None
    had_bom: bool = False

def detect_encoding(data: bytes, forced: str | None = None) -> EncodingDecision: ...
```

- `detect_encoding` 按 [编码规则](tools/README.md#编码规则) 判断编码：BOM → UTF-8 → cp932 / GBK，不用 latin1 兜底。
- `forced` 是页面上手动指定的编码，此时跳过自动识别。例外：文件带 UTF-8 BOM 时 BOM 优先——指定 `utf-8` 按 `utf-8-sig` 处理；指定 `cp932` / `gbk` 时仍返回 `utf-8-sig`，并在 `note` 中说明"文件带 UTF-8 BOM，已忽略手动指定的编码"。
- 返回的 `note` 是需要提示用户的说明（例如"自动识别为 中文 (GBK)"），工具一般把它记成一条警告；不需要提示时为 `None`。
- 两种旧编码都能解码时抛 `AmbiguousEncodingError`，其 `previews` 用于构造 `EncodingQuestion`；工具捕获后调用 `result.ask_encoding(path, exc.previews)`，跳过这个文件。
- 无法识别或无法按指定编码解码时抛 `EncodingError`。

### 读写文本和 CSV：`dataforge.fileio.text_io`

```python
def read_text(path: Path, encoding: str | None = None) -> tuple[str, EncodingDecision]: ...

def write_csv_rows(
    rows: Iterable[Sequence[str]], path: Path, *, delimiter: str = ","
) -> None: ...

def write_text(text: str, path: Path) -> None: ...
```

- `read_text`：读入整个文件，用 `detect_encoding` 决定编码后解码，行尾原样保留，并写一条日志（文件名、编码、自动识别还是手动指定）。CSV 的拆分由各工具用标准 CSV 规则完成。
- `write_csv_rows`：以 UTF-8 BOM 写出，行尾 `\r\n`，标准 CSV 引号规则。即使没有任何行也会写出 BOM。
- `write_text`：以 UTF-8 BOM 写出文本，换行不做转换。
- 两个写出函数都通过 `atomic_path` 写入。

### 原子写入：`dataforge.fileio.atomic`

```python
@contextmanager
def atomic_path(target: Path) -> Iterator[Path]: ...
```

- 给出一个与 `target` 同目录的临时文件路径，名称形如 `.<stem>.<pid>.<8 位十六进制>.tmp<suffix>`。
- `with` 块正常结束时用 `os.replace` 替换到 `target`；出现任何异常（包括 `Cancelled`）时删除临时文件并原样抛出。
- `target` 所在目录必须已经存在。

### 输出路径和输入展开：`dataforge.fileio.paths`

```python
def plan_output(
    source: Path,
    *,
    new_name: str,
    output_dir: Path | None = None,
    overwrite_source: bool = False,
) -> Path: ...

def iter_input_files(
    paths: Iterable[Path], extensions: tuple[str, ...], recursive: bool = False
) -> list[Path]: ...
```

- `plan_output`：
  - `overwrite_source=True` 时直接返回 `source`；
  - 否则输出到 `output_dir`（为 `None` 时用 `source` 所在目录，不存在则创建），文件名为 `new_name`；
  - 目标已存在时依次尝试 `<stem>_1<suffix>`、`<stem>_2<suffix>`……，返回第一个不存在的路径。
- `iter_input_files`：把文件和文件夹展开成文件列表。
  - 只保留扩展名在 `extensions` 中的文件（不区分大小写）；
  - 跳过 `~$` 开头的 Office 锁文件和 `atomic_path` 遗留的临时文件；
  - 同一个文件只出现一次；不存在的路径忽略；
  - 文件夹内按（所在目录，文件名）排序，`recursive=True` 时包含子文件夹。

## dates

模块 `dataforge.dates` 集中了所有日期解析。各工具只调用这里，不得另写一套。

```python
def to_iso8601(value: str) -> str: ...

class SlashOrder(Enum):
    DAY_FIRST = "dmy"
    MONTH_FIRST = "mdy"

class SlashKind(Enum):
    NOT_SLASH = "not_slash"
    DAY_FIRST_ONLY = "day_first_only"
    MONTH_FIRST_ONLY = "month_first_only"
    SAME = "same"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"

class DateOutcome(Enum):
    BLANK = "blank"
    SHIFTED = "shifted"
    FILLED = "filled"
    UNPARSED = "unparsed"

@dataclass(frozen=True)
class ParsedDate:
    value: date
    partial: bool
    suffix: str

def slash_kind(text: str) -> SlashKind: ...
def parse_mask_date(text: str, order: SlashOrder | None = None) -> ParsedDate | None: ...
def is_date_like(text: str) -> bool: ...
def shift_years(value: date, years: int) -> date | None: ...
def mask_date(text: str, years: int, order: SlashOrder | None) -> tuple[str, DateOutcome]: ...
```

| 函数 | 用途 | 规则说明 |
| --- | --- | --- |
| `to_iso8601` | 把 `YYYY/M/D` 一类文本转为 ISO 8601，解析不了的部分逐级退化 | [date_convert.md](tools/date_convert.md) |
| `slash_kind` | 判断 `a/b/YYYY` 形式按 日/月 和 月/日 两种读法哪种成立 | [masking.md 的"日期规则"](tools/masking.md#日期规则) |
| `parse_mask_date` | 解析数据模糊化中的日期；有歧义且没给 `order` 时返回 `None` | 同上 |
| `is_date_like` | 扫描时判断一个值像不像日期（有歧义的 `a/b/YYYY` 也算） | 同上 |
| `shift_years` | 按年偏移，2 月 29 日落到平年时取当月最后一天；超出 1–9999 年返回 `None` | 同上 |
| `mask_date` | 对一个单元格做日期偏移，返回新值和结果类别 | 同上 |

`ParsedDate.partial` 为 `True` 表示原值只有年或年月（按 1 日补齐）；`suffix` 是日期后面保留下来的时间部分。

## 各工具入口

### 格式转换：`dataforge.tools.format_convert`

```python
class ConvertMode(str, Enum):
    CSV_TO_XLSX = "csv_to_xlsx"
    XLSX_TO_CSV = "xlsx_to_csv"
    CSV_TO_BOM = "csv_to_bom"
    CSV_UNQUOTE = "csv_unquote"

MODE_EXTENSIONS: dict[ConvertMode, tuple[str, ...]]

@dataclass
class FormatOptions:
    mode: ConvertMode
    output_dir: Path | None = None
    overwrite_source: bool = False
    all_sheets: bool = False
    encoding: str | None = None
    encodings: dict[str, str] = field(default_factory=dict)

def run(
    files: list[Path], options: FormatOptions, progress: ProgressFn, cancel: CancelToken
) -> Result: ...
```

- `mode` 必填，没有默认值。
- `encoding` 对全部 CSV 统一指定编码；`encodings` 按文件指定（键是 `str(文件路径)`），优先于 `encoding`。获取字段的 `FieldOptions` 同样如此。
- `all_sheets` 只对 `XLSX_TO_CSV` 有效。
- `files` 为空时抛 `DataForgeError`。扩展名与模式不符的文件记一条错误后跳过。
- `stats`：`files`（有输出的文件数）、`skipped`（既没有输出也没有出错的文件数，例如 CSV 转 UTF-8 BOM 时输入已经带 BOM）。等待选择编码的文件两者都不计入。
- 规则：[format_convert.md](tools/format_convert.md)。

### 工作表拆分：`dataforge.tools.sheet_split`

```python
SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")

@dataclass
class SplitOptions:
    output_dir: Path | None = None

def run(
    files: list[Path], options: SplitOptions, progress: ProgressFn, cancel: CancelToken
) -> Result: ...
```

- 每个工作表导出为一个 CSV。格式转换的 `XLSX_TO_CSV` 模式也复用这里的导出逻辑：调用同一模块的 `export_workbook(src, *, all_sheets, output_dir, result, cancel)`，输出和错误记入传入的 `result`。
- `stats`：`sheets`（导出的工作表数）、`files`（没有出错的工作簿数）。
- 规则：[sheet_split.md](tools/sheet_split.md)。

### 获取字段：`dataforge.tools.field_extract`

```python
SUMMARY_NAME = "file_fields_summary.csv"
SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xlsm")

@dataclass
class FieldOptions:
    header_row: int = 1
    include_subfolders: bool = False
    output_dir: Path | None = None
    encoding: str | None = None
    encodings: dict[str, str] = field(default_factory=dict)

def run(folder: Path, options: FieldOptions, progress: ProgressFn, cancel: CancelToken) -> Result: ...
```

- 输入是一个文件夹，不是文件列表。`folder` 不是文件夹、`header_row < 1`，或文件夹中没有可处理的 CSV / Excel 文件时抛 `DataForgeError`。
- 已有的汇总文件（`file_fields_summary.csv`、`file_fields_summary_1.csv`……）不作为输入。
- 编码重跑时不合并两次的 `Result`：界面带上选定的 `encodings` 对整个文件夹再运行一次，生成完整的新汇总，再替换第一次的汇总。
- `stats`：`files`、`fields`。
- 规则：[field_extract.md](tools/field_extract.md)。

### 数据模糊化：`dataforge.tools.masking`

数据模糊化分两步：先扫描（`scan.scan`），扫描通过后再执行（`execute.run`）。执行只依据扫描报告，不重新读取文件列表。

#### 配置：`masking.profile`

```python
CONFIG_SECTION = "data_masking_pattern1"

@dataclass
class RuleStep:
    op: str
    value: Any

@dataclass
class MaskingProfile:
    studyid_value: str = "[UAT]CIRCULATE"
    subject_limit: int = 100
    usubjid_mode: str = "sequential"  # sequential | rule_chain
    rule_chain_steps: list[RuleStep] = field(default_factory=_default_steps)
    sequential_prefix: str = "TEST"
    sequential_width: int = 4
    sequential_start: int = 1
    date_shift_years: int = -2
    age_shift_years: int = -2
    date_detect_sample_size: int = 200
    date_detect_min_non_empty: int = 20
    date_detect_success_ratio: float = 0.8
    doctor_fields: list[str] = field(default_factory=lambda: ["INVNAM"])
    doctor_value: str = "テスト医師"
    doctor_replace_enabled: bool = True
    site_field: str = "SITEID"
    site_value: str = "テスト施設"
    site_replace_enabled: bool = True
    age_field: str = "AGE"
    include_subjid: bool = True

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> MaskingProfile: ...
    def to_dict(self) -> dict[str, Any]: ...
```

- `_default_steps()` 返回 `[RuleStep("remove_prefix", 4), RuleStep("remove_suffix", 0), RuleStep("prepend", "SKLT"), RuleStep("append", "")]`。
- `from_dict` 按 v2 的规则容错读取配置节：类型不对的项用默认值，`usubjid_mode` 只接受 `sequential`、`rule_chain`，已废弃的键忽略。`to_dict` 的结果就是配置文件中 `data_masking_pattern1` 节的内容。

#### 扫描：`masking.scan`

```python
@dataclass(frozen=True)
class ScanSettings:
    sample_size: int = 200
    min_non_empty: int = 20
    ratio: float = 0.8

    @classmethod
    def from_profile(cls, p: MaskingProfile) -> ScanSettings: ...

@dataclass
class FileScan:
    path: Path
    file_name: str
    encoding: str
    row_count: int
    unique_usubjid_count: int
    non_empty_fields: list[str]
    empty_fields: list[str]
    date_fields: list[str]

@dataclass
class AmbiguousColumn:
    file_name: str
    column: str
    ambiguous: int
    day_first_only: int
    month_first_only: int

@dataclass
class ScanReport:
    files: list[FileScan]
    dm_file: str | None
    dm_first_usubjid: str | None
    subjects: list[str]
    ambiguous_columns: list[AmbiguousColumn]
    settings: ScanSettings
    errors: list[str]
    warnings: list[str]
    signature: str

    @property
    def processable(self) -> bool: ...
    def to_dict(
        self, date_orders: Mapping[tuple[str, str], SlashOrder] | None = None
    ) -> dict[str, Any]: ...

def scan(
    paths: Sequence[Path],
    settings: ScanSettings,
    encoding: str | None,
    encodings: Mapping[str, str],
    progress: ProgressFn,
    cancel: CancelToken,
) -> Result: ...

def scan_signature(
    paths: Sequence[Path],
    settings: ScanSettings,
    encoding: str | None,
    encodings: Mapping[str, str],
) -> str: ...

def export_report(
    report: ScanReport,
    target: Path,
    date_orders: Mapping[tuple[str, str], SlashOrder] | None = None,
) -> Path: ...
```

- `scan` 返回的 `Result.data` 是 `ScanReport`。`ScanReport.errors` 不为空或没有受试者时，`processable` 为 `False`，不能执行。
- `ambiguous_columns` 是含有无法判断 日/月 顺序的日期列，执行前必须为每一列选定顺序。
- `signature` 由文件路径、大小、修改时间、扫描设置和编码选择算出。执行前用 `scan_signature` 重新计算，不一致说明文件或设置变了，需要重新扫描。
- `export_report` 按 `target` 的扩展名导出 JSON 或 CSV 格式的扫描报告。
- `stats`：`files`、`subjects`。

#### 执行：`masking.execute`

```python
REPORT_FILE = "pattern1_scan_report.json"
FOLDER_PREFIX = "masked_output_"

@dataclass
class MaskOptions:
    profile: MaskingProfile
    output_parent: Path | None = None
    date_orders: dict[tuple[str, str], SlashOrder] = field(default_factory=dict)
    now: datetime | None = None  # tests only: fixes the folder time stamp

def missing_orders(
    report: ScanReport, date_orders: Mapping[tuple[str, str], SlashOrder]
) -> list[AmbiguousColumn]: ...

def describe_plan(
    report: ScanReport,
    profile: MaskingProfile,
    date_orders: Mapping[tuple[str, str], SlashOrder],
    output_parent: Path | None,
) -> list[str]: ...

def run(
    report: ScanReport, options: MaskOptions, progress: ProgressFn, cancel: CancelToken
) -> Result: ...
```

- `profile` 必填。`date_orders` 的键是 `(文件名, 列名)`。
- `run` 的输入是扫描报告，不是文件列表。以下情况抛 `DataForgeError`：扫描未通过、还有日期列没选顺序、`subject_limit < 1`、新 USUBJID 为空或重复、某个文件的 USUBJID 列重复、无法创建输出文件夹、无法写入输出文件。扫描之后文件读不了或缺少 USUBJID 列时抛它的子类 `StaleScanError`，界面据此要求重新扫描。
- 同一模块的 `transform_subject_id(subject, profile, index) -> str` 按 `usubjid_mode` 算出一个新 USUBJID，界面用它显示预览；`masking.scan.select_files(paths)` 从输入中取出要处理的 CSV 文件，扫描和界面计算签名时都用它。
- 输出是一个新文件夹，全部写完后才整体改名为最终名称；出错或取消时不留下任何输出。`Result.data` 是这个输出文件夹的 `Path`，`outputs` 是其中的各个文件。
- `describe_plan` 生成界面"执行摘要"中的说明文字，每行一条。
- `stats`：`files`、`subjects`、`rows`、`dates_shifted`、`dates_filled`、`dates_unparsed`。
- 规则：[masking.md](tools/masking.md)。

### 全角转半角：`dataforge.tools.width_convert`

```python
SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")

@dataclass
class WidthOptions:
    output_dir: Path | None = None
    overwrite_source: bool = False

def to_halfwidth(text: str) -> str: ...

def run(
    files: list[Path],
    options: WidthOptions,
    progress: ProgressFn,
    cancel: CancelToken,
) -> Result: ...
```

- `to_halfwidth`：U+FF01–U+FF5E 转为 U+0021–U+007E，U+3000 转为 U+0020，其他字符不变。
- `stats`：`files`、`cells_changed`。
- 规则：[width_convert.md](tools/width_convert.md)。

### 日期转换：`dataforge.tools.date_convert`

```python
def convert_text(text: str) -> str: ...
```

- 即时工具，没有 options、进度和取消。逐行调用 `dates.to_iso8601`，结果用 `\n` 连接。
- 规则：[date_convert.md](tools/date_convert.md)。

## EDC 站点添加

EDC 站点添加会实际操作鼠标、键盘、剪贴板和 Excel。为了能在不碰真实屏幕的情况下测试，所有外部动作都通过"执行接口"（ports）注入：真实运行时用 `edc.live` 中基于 pywin32、pyautogui、pyperclip 的实现，测试和标准样例用假实现记录动作序列。

规则（11 个步骤、停止条件、3 个选择、汇总、目标窗口匹配、动作序列格式）见 [edc_site_adder.md](tools/edc_site_adder.md)。

### 配置：`dataforge.tools.edc.config`

```python
CONFIG_SECTION = "edc_site_adder"
STEP_KEYS = ("新建", "查找", "搜索框", "搜索", "选择", "ok", "确认")
DEFAULT_POSITIONS: dict[str, tuple[int, int]] = {
    "新建": (241, 212),
    "查找": (1137, 460),
    "搜索框": (817, 409),
    "搜索": (1040, 406),
    "选择": (699, 471),
    "ok": (1121, 758),
    "确认": (1038, 728),
}
MAX_LOOPS_RANGE = (1, 9999)
STEP_DELAY_RANGE = (0.1, 5.0)

@dataclass
class EdcConfig:
    max_loops: int = 100
    step_delay: float = 0.3
    click_positions: dict[str, tuple[int, int]] = field(
        default_factory=lambda: dict(DEFAULT_POSITIONS)
    )
    target_window: WindowInfo | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> EdcConfig: ...
    def to_dict(self) -> dict[str, Any]: ...
```

- `from_dict` 只接受范围内的 `max_loops`、`step_delay`，以及形如 `{"x": int, "y": int}` 的点击位置；不合法的项用默认值。v2 的 `retry_count` 忽略。

### 窗口：`dataforge.tools.edc.windows`

```python
@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    process: str

def find_target(target: WindowInfo, candidates: Sequence[WindowInfo]) -> WindowInfo | None: ...
def list_windows(exclude_pid: int | None = None) -> list[WindowInfo]: ...
def window_at(x: int, y: int) -> WindowInfo | None: ...
def activate_window(hwnd: int) -> None: ...
```

- `find_target` 是纯函数，按规则说明"目标窗口"一节的顺序在候选窗口中匹配。
- 其余三个函数调用 Win32 API：列出可见、有标题的顶层窗口；取屏幕坐标所在的顶层窗口；激活窗口。

### 执行接口：`dataforge.tools.edc.loop`

```python
@dataclass(frozen=True)
class CellRef:
    workbook: str
    sheet: str
    row: int
    column: int

    def address(self) -> str: ...
    def at_row(self, row: int) -> CellRef: ...

class ExcelPort(Protocol):
    def selection(self) -> CellRef: ...
    def text(self, cell: CellRef) -> str: ...
    def focus(self, cell: CellRef) -> None: ...

class ScreenPort(Protocol):
    def click(self, x: int, y: int) -> None: ...
    def paste(self) -> None: ...

class ClipboardPort(Protocol):
    def copy(self, text: str) -> None: ...

class WindowPort(Protocol):
    def activate(self, target: WindowInfo) -> None: ...

class StopFlag(Protocol):
    def is_set(self) -> bool: ...

@dataclass
class EdcPorts:
    excel: ExcelPort
    screen: ScreenPort
    clipboard: ClipboardPort
    window: WindowPort
    sleep: Callable[[float], None]
```

- `CellRef.row`、`column` 从 1 开始。`address()` 返回列字母加行号，例如 `A5`、`AA12`。
- `ExcelPort.selection()` 返回当前选区左上角的单元格；`text()` 读单元格显示文本；`focus()` 切回 Excel 并选中该单元格。
- `ScreenPort.paste()` 发送 Ctrl+V。
- `StopFlag` 是 ESC 标志，`threading.Event` 即满足；它和 `CancelToken` 不同：ESC 让当前行在下一步开始前停下并等待用户选择，`CancelToken` 是强制中止（例如关闭程序）。
- 真实实现：`dataforge.tools.edc.live.open_live_ports()` 是一个上下文管理器，连接正在运行的 Excel 并返回 `EdcPorts`；找不到 Excel 时抛 `DataForgeError`。

### 一段运行：`run_segment`

```python
STEP_NAMES: tuple[str, ...] = (
    "读取单元格",
    "复制到剪贴板",
    "激活目标窗口",
    "点击【新建】",
    "点击【查找】",
    "点击【搜索框】并粘贴",
    "点击【搜索】",
    "点击【选择】",
    "点击【ok】",
    "点击【确认】",
    "切回 Excel 并选中下一行",
)

@dataclass(frozen=True)
class RowDone:
    cell: CellRef
    value: str

@dataclass(frozen=True)
class RowStop:
    cell: CellRef
    value: str
    step: int  # 1-based index into STEP_NAMES; 1 means nothing was done for this row
    reason: str
    by_user: bool

    @property
    def step_name(self) -> str: ...

@dataclass
class Segment:
    start: CellRef
    end_row: int
    done: list[RowDone]
    stop: RowStop | None
    reached: str  # "empty" | "limit" | "stopped"

def run_segment(
    config: EdcConfig,
    ports: EdcPorts,
    start: CellRef | None,
    end_row: int | None,
    stop: StopFlag,
    progress: ProgressFn,
    cancel: CancelToken,
) -> Result: ...
```

- `start` 为 `None` 时从 Excel 当前选区开始；`end_row` 为 `None` 时取 `start.row + config.max_loops`（不含这一行）。
- 逐行执行 11 个步骤，遇到空单元格、到达 `end_row` 或第一次停下时结束。出错时不自动重试。
- 返回的 `Result.data` 是 `Segment`；`stats`：`succeeded`。
- `config.target_window` 为 `None`、或读取 Excel 选区失败时抛 `DataForgeError`，不开始运行。

### 整次运行：`EdcSession`

```python
class StopChoice(Enum):
    REDO = "redo"
    SKIP = "skip"
    END = "end"

@dataclass
class EdcSession:
    first: CellRef
    end_row: int
    done: list[RowDone] = field(default_factory=list)
    skipped: list[RowStop] = field(default_factory=list)
    failed: list[RowStop] = field(default_factory=list)

    @classmethod
    def begin(cls, segment: Segment) -> EdcSession: ...
    def absorb(self, segment: Segment) -> None: ...
    def resolve(self, stop: RowStop, choice: StopChoice) -> CellRef | None: ...
    def to_result(self) -> Result: ...
    def done_lines(self) -> list[str]: ...
```

调用顺序：

1. 第一段：`run_segment(..., start=None, end_row=None, ...)`，用返回的 `Segment` 调用 `EdcSession.begin(segment)`。
2. 如果 `segment.stop` 不为 `None`，让用户选择，调用 `session.resolve(segment.stop, choice)`：
   - 返回 `CellRef`：从这个单元格开始下一段，`end_row` 用 `session.end_row`；下一段的结果用 `session.absorb(segment)` 合并，再回到第 2 步；
   - 返回 `None`：整次运行结束。
3. 结束后调用 `session.to_result()` 得到汇总：`stats` 为 `succeeded`、`skipped`、`failed`，跳过的行记为警告，出错的行记为错误，`data` 是 session 本身。`done_lines()` 返回成功行的 `<地址> <值>` 列表。

`first`、`end_row` 必填，由 `begin` 从第一段取得。
