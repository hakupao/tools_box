# 工具规则说明与标准样例

每个工具一份规则说明（`docs/tools/<tool_id>.md`），写法与语言无关，以后 C#/Rust 版本可直接照着实现，并用同一组标准样例对照。

## 规则说明模板

1. 输入：支持的文件类型、读取方式。
2. 参数与默认值。
3. 处理步骤。
4. 输出位置与命名：默认输出到原文件所在目录，目标已存在时自动加 `_1`、`_2`……；绝不静默覆盖原文件，除非用户显式勾选"覆盖原文件"并二次确认。
5. 编码：CSV 写出一律 `utf-8-sig`；读取规则见各工具。
6. 边界情况。
7. 已知限制。

## 标准样例

目录格式：

```
tests/golden/<tool_id>/<case>/
    params.json      工具参数（JSON，不含路径；输出目录由测试框架指定）
    input/           输入文件
    expected/        期望输出文件（文件名即工具实际生成的文件名）
```

- 样例数据必须是虚构的。
- 期望输出由手写字面值生成，不得用被测代码生成。
- `tests/golden/width_convert/make_fixtures.py` 是 Excel 样例的生成脚本，在仓库根目录运行即可重新生成。

比较规则（`tests/dataforge/golden.py` 的 `assert_dirs_equal`）：

- 文件名集合必须一致。
- `.csv`、`.txt`、`.json`：逐字节相等。
- `.xlsx`、`.xlsm`：sheet 名称（按顺序）、两个 sheet 范围并集内每个单元格的值、`data_type`、`number_format`、合并区域（排序后的区域字符串）逐项相等。
- `expected/` 不存在或为空，表示该样例不应产生任何输出文件（例如 CSV 转 BOM 时输入已带 BOM）。

`params.json` 的键（都可省略，未写按默认值）：

| 键 | 适用工具 | 含义 |
| --- | --- | --- |
| `mode` | format_convert | `csv_to_xlsx`、`xlsx_to_csv`、`csv_to_bom`、`csv_unquote` |
| `all_sheets` | format_convert | `xlsx_to_csv` 时导出全部工作表，默认 `false`（只导出第一个） |
| `encoding` | format_convert、field_extract | 统一指定编码（如 `gbk`），默认自动识别 |
| `encodings` | format_convert、field_extract、masking | 按文件指定编码，键是相对 `input/` 的路径（用 `/` 分隔），值是编码名；优先于 `encoding` |
| `header_row` | field_extract | 列名行号，默认 1 |
| `include_subfolders` | field_extract | 是否包含子文件夹，默认 `false` |
| `overwrite_source` | format_convert | 覆盖原文件；此时把被改写的输入文件当作输出，与 `expected/` 对照 |
| `profile` | masking | 覆盖默认配置的项（键同配置 `data_masking_pattern1` 节，例如 `{"subject_limit": 2}`）；未写的项用默认值 |
| `date_orders` | masking | 有歧义日期列的 日/月 顺序，键为 `文件名:列名`（按第一个 `:` 拆分），值为 `dmy` 或 `mdy`，例如 `{"AE.csv:AESTDTC": "dmy"}` |

其他语言的版本：把 `input/` 复制到临时目录，按 `params.json` 运行，把输出写入空目录，再按上述规则与 `expected/` 对照。

## 取消规则

- `Cancelled` 继承自 `BaseException`，这样逐文件的 `except Exception` 不会吞掉取消。
- 工具代码不得捕获 `BaseException`（也不要写裸 `except:`）。唯一例外：只为清理临时文件/文件夹而捕获，并且清理后立即原样重新抛出（`except BaseException: 清理; raise`），例如 `atomic_path` 和数据模糊化的输出文件夹。
- 在方便的位置（例如每个文件开始前）调用 `cancel.raise_if_cancelled()`。

## 编码规则

读取文本类文件（CSV/TXT）时按以下顺序识别编码，不使用 latin1 兜底：

1. 以 UTF-8 BOM（`EF BB BF`）开头 → `utf-8-sig`。
2. 整体能按 UTF-8 解码（空文件也算）→ `utf-8`。
3. 否则分别尝试 cp932 与 GBK：
   - 只有一种能解码 → 采用该编码，并给出提示"自动识别为 日文 (cp932)"或"自动识别为 中文 (GBK)"。
   - 两种都能解码 → 歧义：该文件不处理，列出两种编码下的前 5 行（每行最多 200 字符）供用户选择；提示"无法确定编码（日文 cp932 / 中文 GBK 均可解码）"。
   - 两种都不能 → 报错"无法识别文件编码（已尝试 UTF-8、cp932、GBK）"。
4. 页面手动指定编码时跳过自动识别；解码失败报错"无法按 <编码> 解码"。手动指定 UTF-8 而文件带 BOM 时按 `utf-8-sig` 处理；手动指定 GBK/cp932 而文件带 BOM 时 BOM 优先，同样按 `utf-8-sig` 处理并提示"文件带 UTF-8 BOM，已忽略手动指定的编码"。每个文件读取时写一条日志，记录所用编码及来源（自动识别/手动指定）。

写出：CSV/文本一律 `utf-8-sig`，CSV 换行为 `\r\n`；所有输出先写同目录临时文件，再原子替换到目标。
