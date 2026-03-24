# DataForge Studio API 文档

本文档详细说明了工具箱中各个服务类的接口和使用方法。

适用版本：`v2.0.1`（2026-03-24）

## 目录

1. [日期工具 API](#日期工具-api)
2. [CSV转换器 API](#csv转换器-api)
3. [CSV编码转换器 API](#csv编码转换器-api)
4. [XLSX转换器 API](#xlsx转换器-api)
5. [工作表拆分器 API](#工作表拆分器-api)
6. [全角转半角转换器 API](#全角转半角转换器-api)
7. [数据清洗器 API](#数据清洗器-api)
8. [Codelist处理器 API](#codelist处理器-api)
9. [数据模糊化处理器 API](#数据模糊化处理器-api)
10. [CSV引号去除处理器 API](#csv引号去除处理器-api)
11. [XLSX重构处理器 API](#xlsx重构处理器-api)
12. [文件字段提取器 API](#文件字段提取器-api)
13. [死链检测器 API](#死链检测器-api)

---

## 日期工具 API

### `date_utils.convert_to_iso8601()`

将各种格式的日期字符串转换为 ISO 8601 格式。

#### 参数
- `date_string` (str): 输入的日期字符串

#### 返回值
- `str`: ISO 8601 格式的日期字符串 (YYYY-MM-DD)

#### 示例
```python
from src.utils.date_utils import convert_to_iso8601

result = convert_to_iso8601("2024/12/19")
print(result)  # "2024-12-19"
```

#### 支持的输入格式
- `YYYY-MM-DD`
- `YYYY/MM/DD`
- `DD/MM/YYYY`
- `MM/DD/YYYY`
- `DD-MM-YYYY`
- 其他常见日期格式

---

## CSV转换器 API

### `CsvToXlsxConverterService`

将 CSV 文件转换为 XLSX 格式。

#### 方法

##### `convert_file(input_file, output_path=None)`

转换单个 CSV 文件为 XLSX 格式。

**参数:**
- `input_file` (str): 输入 CSV 文件路径
- `output_path` (str, optional): 输出目录路径

**返回值:**
- `Tuple[bool, str]`: (是否成功, 错误信息)

#### 示例
```python
from src.utils.csv_to_xlsx_converter_service import CsvToXlsxConverterService

converter = CsvToXlsxConverterService()
success, error = converter.convert_file("data.csv", "output/")
if success:
    print("转换成功")
else:
    print(f"转换失败: {error}")
```

---

## CSV编码转换器 API

### `CsvEncodingConverterService`

将 CSV 文件重新保存为目标编码（默认 UTF-8 BOM）。

#### 方法

##### `convert_file(input_file, output_path=None)`

将单个 CSV 文件转换为目标编码。

**参数:**
- `input_file` (str): 输入 CSV 文件路径
- `output_path` (str, optional): 输出目录路径，None 时覆盖原文件

**返回值:**
- `Tuple[bool, str]`: (是否成功, 错误信息)

#### 示例
```python
from src.utils.csv_encoding_converter_service import CsvEncodingConverterService

converter = CsvEncodingConverterService()
success, error = converter.convert_file("data.csv")
```

---

## XLSX转换器 API

### `XlsxToCsvConverterService`

将 XLSX 文件转换为 CSV 格式。

#### 方法

##### `convert_file(input_file, output_path=None)`

转换单个 XLSX 文件为 CSV 格式。

**参数:**
- `input_file` (str): 输入 XLSX 文件路径
- `output_path` (str, optional): 输出目录路径

**返回值:**
- `Tuple[bool, str]`: (是否成功, 错误信息)

#### 特性
- 自动处理多个工作表
- 使用 UTF-8-SIG 编码
- 保持 NA 值不变

#### 示例
```python
from src.utils.xlsx_to_csv_converter_service import XlsxToCsvConverterService

converter = XlsxToCsvConverterService()
success, error = converter.convert_file("data.xlsx")
```

---

## 工作表拆分器 API

### `XlsxSheetSplitterService`

将 Excel 文件按工作表拆分为 CSV 文件。

#### 方法

##### `split_file(input_file, output_path=None, progress_callback=None)`

将单个 Excel 文件拆分为多个 CSV 文件。

**参数:**
- `input_file` (str): 输入 Excel 文件路径
- `output_path` (str, optional): 输出目录路径，None 时输出到原目录
- `progress_callback` (callable, optional): 进度回调 `(current, total, sheet_name)`

**返回值:**
- `dict`: 包含 `output_dir`、`output_files`、`errors`、`total_sheets`、`success`

#### 处理特性
- 工作表名作为 CSV 文件名，非法字符替换为 `_`
- 若替换后文件名重复，会自动追加序号
- 空表与隐藏表也会输出
- 输出编码为 UTF-8-SIG

#### 示例
```python
from src.utils.xlsx_sheet_splitter_service import XlsxSheetSplitterService

splitter = XlsxSheetSplitterService()
result = splitter.split_file("data.xlsx", "output/")
print(result["output_files"])
```

---

## 全角转半角转换器 API

### `FullwidthHalfwidthService`

将文本中的全角字符转换为半角字符。

#### 方法

##### `__init__()`

初始化转换器，建立字符映射表。

##### `convert_text(text)`

转换文本中的全角字符。

**参数:**
- `text` (str): 要转换的文本

**返回值:**
- `str`: 转换后的文本

##### `convert_file(input_file_path, output_path=None)`

转换 Excel 文件中的全角字符。

**参数:**
- `input_file_path` (str): 输入文件路径
- `output_path` (str, optional): 输出目录路径

**返回值:**
- `bool`: 转换是否成功

#### 转换映射

| 类型 | 全角 | 半角 |
|------|------|------|
| 数字 | ０-９ | 0-9 |
| 大写字母 | Ａ-Ｚ | A-Z |
| 小写字母 | ａ-ｚ | a-z |
| 空格 | 　 | 空格 |
| 符号 | ！？（） | !?() |

#### 示例
```python
from src.utils.fullwidth_halfwidth_service import FullwidthHalfwidthService

converter = FullwidthHalfwidthService()
result = converter.convert_text("１２３ＡＢＣ")
print(result)  # "123ABC"
```

---

## 数据清洗器 API

### `DataCleanerService`

基于仕样书规则进行数据清洗。

#### 属性
- `NEED_KEY`: 需要处理的标记符号列表 `['○','〇','◯']`

#### 方法

##### `__init__()`

初始化数据清洗器。

##### `select_rule_file(file_path)`

选择并加载仕样书规则文件。

**参数:**
- `file_path` (str): 仕样书 Excel 文件路径

**功能:**
- 从 Patients 表读取患者ID
- 从 Process 表读取字段规则
- 建立过滤规则

##### `clean_csv_file(csv_file_path, output_path=None)`

清洗单个 CSV 文件。

**参数:**
- `csv_file_path` (str): CSV 文件路径
- `output_path` (str, optional): 输出路径

**返回值:**
- `bool`: 清洗是否成功

#### 清洗规则
1. 患者过滤：只保留 PAT 集合中的患者
2. 列过滤：只保留 KEEP 字典中指定的字段
3. 行过滤：应用自定义行过滤逻辑
4. 空行清理：删除除主体ID外全为空的行

#### 示例
```python
from src.utils.data_cleaner_service import DataCleanerService

cleaner = DataCleanerService()
cleaner.select_rule_file("rules.xlsx")
success = cleaner.clean_csv_file("data.csv", "output/")
```

---

## Codelist处理器 API

### `CodelistService`

根据 Codelist 文件进行编码映射。

#### 方法

##### `__init__()`

初始化 Codelist 处理器。

##### `select_codelist_file(file_path)`

选择并加载 Codelist 文件。

**参数:**
- `file_path` (str): Codelist Excel 文件路径

**返回值:**
- `bool`: 加载是否成功

**文件要求:**
- Process 表：字段映射规则
- CodeList 表：编码映射关系
- Files 表：SUBJID 字段映射

##### `process_csv_file(input_file, output_path=None)`

处理 CSV 文件进行编码映射。

**参数:**
- `input_file` (str): 输入 CSV 文件路径
- `output_path` (str, optional): 输出路径

**返回值:**
- `bool`: 处理是否成功

#### 处理功能
- 编码到值的自动映射
- 多语言值转换
- 日期格式标准化
- SUBJID 字段重命名
- 文件前缀处理

#### 示例
```python
from src.utils.codelist_service import CodelistService

processor = CodelistService()
processor.select_codelist_file("codelist.xlsx")
success = processor.process_csv_file("data.csv")
```

---

## 数据模糊化处理器 API

### `DataMaskingService`

SDTM Pattern1 数据模糊化处理器（扫描 + 执行两阶段）。

#### 方法

##### `__init__(config_path=None)`

初始化处理器并加载 Pattern1 配置。

**参数:**
- `config_path` (str, optional): 配置文件路径，默认使用系统用户配置目录下的 `tools_box_config.json`（`data_masking_pattern1` section）

##### `load_profile()`

读取并返回 `Pattern1Profile`。

##### `save_profile(profile=None)`

保存配置到 JSON 文件。

**参数:**
- `profile` (`Pattern1Profile`, optional): 可选，传入后覆盖当前配置

**返回值:**
- `bool`: 保存是否成功

##### `reset_profile()`

重置为默认配置并持久化。

**返回值:**
- `Pattern1Profile`: 重置后的配置对象

##### `scan_pattern1(file_paths, profile=None)`

扫描 CSV 文件集，输出结构信息、字段有值/空值分布、USUBJID 统计和日期字段识别结果。

**参数:**
- `file_paths` (list[str]): 待处理文件路径集合
- `profile` (`Pattern1Profile`, optional): 扫描参数（日期识别抽样阈值等）

**返回值:**
- `Pattern1ScanReport`: 扫描报告对象（含 `files_summary`、`errors`、`selected_subjects` 等）

##### `run_pattern1(file_paths, output_dir=None, profile=None, scan_report=None, progress_callback=None)`

按扫描结果执行 Pattern1 脱敏，输出脱敏后的 CSV、映射表和扫描报告。

**参数:**
- `file_paths` (list[str]): 待处理文件路径集合
- `output_dir` (str, optional): 输出目录
- `profile` (`Pattern1Profile`, optional): 执行配置
- `scan_report` (`Pattern1ScanReport`, optional): 已有扫描结果
- `progress_callback` (callable, optional): 进度回调 `(current, total, filename)`

**返回值:**
- `Pattern1RunResult`: 执行结果对象（输出目录、文件列表、映射文件、日期统计等）

#### `Pattern1Profile` 关键字段（节选）
- `doctor_fields` (`list[str]`): DM 人名字段列表，默认 `["INVNAM"]`
- `doctor_value` (`str`): DM 人名替换值
- `doctor_replace_enabled` (`bool`): 是否启用人名替换，默认 `True`
- `site_field` (`str`): DM 施设字段，默认 `SITEID`
- `site_value` (`str`): DM 施设替换值
- `site_replace_enabled` (`bool`): 是否启用施设替换，默认 `True`
- `age_field` (`str`): DM 年龄字段，默认 `AGE`
- `age_shift_years` (`int`): 年龄偏移值

##### `export_scan_report(report, target_path)`

导出扫描报告为 JSON 或 CSV。

**参数:**
- `report` (`Pattern1ScanReport`): 扫描报告对象
- `target_path` (str): 目标路径（`.json` / `.csv`）

##### `format_scan_report(report)`

将扫描报告格式化为可读文本，用于 UI 预览。

##### `transform_subject_id(subject, profile, index=0)`

根据当前配置计算单个 `USUBJID` 的脱敏结果（用于规则预览与映射构建）。

#### 示例
```python
from src.utils.data_masking_service import DataMaskingService, Pattern1Profile

processor = DataMaskingService()
profile = Pattern1Profile(subject_limit=100)

report = processor.scan_pattern1(["DM.csv", "AE.csv"], profile)
if report.errors:
    raise ValueError(report.errors)

result = processor.run_pattern1(
    ["DM.csv", "AE.csv"],
    output_dir="final/",
    profile=profile,
    scan_report=report,
)
print(result.mapping_file)
```

---

## CSV引号去除处理器 API

### `CsvQuoteRemoverService`

CSV 文件引号清理处理器。

#### 方法

##### `process_file(input_file, output_path=None)`

处理 CSV 文件，去除多余引号。

**参数:**
- `input_file` (str): 输入 CSV 文件路径
- `output_path` (str, optional): 输出路径

**返回值:**
- `Tuple[bool, str]`: (是否成功, 错误信息)

##### `validate_csv_file(file_path)`

验证是否为有效的 CSV 文件。

**参数:**
- `file_path` (str): 文件路径

**返回值:**
- `bool`: 是否为有效 CSV

#### 处理特性
- 智能检测 CSV 分隔符
- 处理多层引号嵌套
- 保持 CSV 结构完整
- 处理引号转义字符

#### 示例
```python
from src.utils.csv_quote_remover_service import CsvQuoteRemoverService

processor = CsvQuoteRemoverService()
success, error = processor.process_file("data.csv")
if success:
    print("处理成功")
```

---

## XLSX重构处理器 API

### `XlsxRestructureService`

XLSX 文件重构为标准 CDISC SDTM 格式。

#### 方法

##### `file_restructure(input_file, output_path=None, studyid="CIRCULATE", patients_mapping=None)`

重构 XLSX 文件为标准格式。

**参数:**
- `input_file` (str): 输入 XLSX 文件路径
- `output_path` (str, optional): 输出路径
- `studyid` (str): 研究ID
- `patients_mapping` (dict, optional): SUBJID 到 USUBJID 的映射字典

**返回值:**
- `Tuple[bool, str]`: (是否成功, 错误信息)

#### 支持的域类型

| 类别 | 域 | 说明 |
|------|-----|------|
| 临床域 | AG, CM, EC, EX, ML, PR, SU | 给药、用药、暴露等 |
| 事件域 | AE, BE, CE, DS, DV, HO, MH | 不良事件、处置等 |
| 检查域 | BS, CP, CV, DA, EG, FT, LB, MB, VS | 实验室、生命体征等 |
| 其他域 | DM, SE, SM, CO | 人口统计学、评论等 |

#### 处理功能
- 多表数据合并
- 字段自动补全和排序
- 序号字段生成
- 日期格式标准化
- 数据类型转换

#### 文件命名要求
- 文件名：字母开头（如 AB.xlsx）
- 工作表：域名+数字 或 Sheet+数字

#### 示例
```python
from src.utils.xlsx_restructure_service import XlsxRestructureService

success, error = XlsxRestructureService.file_restructure("AB.xlsx", "output/")
if not success:
    print(error)
```

---

## 文件字段提取器 API

### `FileFieldExtractorService`

批量提取 CSV / Excel 文件的字段名称并输出汇总结果。

#### 方法

##### `extract_fields(folder_path, include_subfolders=False, header_row=1, progress_callback=None)`

从文件夹中提取字段信息。

**参数:**
- `folder_path` (str): 目标文件夹
- `include_subfolders` (bool): 是否递归子文件夹
- `header_row` (int): 列名所在行（从 1 开始）
- `progress_callback` (callable, optional): 进度回调

**返回值:**
- `dict`: 包含 `output_file`、`details`、`processed_files`、`errors`、`total_fields`

#### 示例
```python
from src.utils.file_field_extractor_service import FileFieldExtractorService

extractor = FileFieldExtractorService()
result = extractor.extract_fields("data/", include_subfolders=True)
print(result["output_file"])
```

---

## 死链检测器 API

### `DeadLinkCheckerService`

检测 HTML 文件中的链接有效性。

#### 方法

##### `check_html_file(file_path, base_url="", progress_callback=None)`

检测单个 HTML 文件。

**参数:**
- `file_path` (str): HTML 文件路径
- `base_url` (str, optional): 基础 URL，用于解析相对链接
- `progress_callback` (callable, optional): 进度回调

**返回值:**
- `dict`: 检测结果（包含统计与详情）

##### `check_folder(folder_path, base_url="", include_subfolders=False, progress_callback=None)`

检测文件夹内所有 HTML 文件。

**参数:**
- `folder_path` (str): 目标文件夹
- `base_url` (str, optional): 基础 URL
- `include_subfolders` (bool): 是否递归子文件夹
- `progress_callback` (callable, optional): 进度回调

**返回值:**
- `dict`: 文件夹检测汇总结果

##### `generate_report(results, output_file)`

生成检测报告文本文件。

**参数:**
- `results` (dict): 检测结果
- `output_file` (str): 报告输出路径

#### 示例
```python
from src.utils.dead_link_checker_service import DeadLinkCheckerService

checker = DeadLinkCheckerService(timeout=10)
results = checker.check_html_file("index.html")
checker.generate_report(results, "dead_link_report.txt")
```

---

## 通用接口规范

### 错误处理

所有服务都遵循统一的错误处理模式：

```python
try:
    # 处理逻辑
    result = process_data()
    return True, result
except FileNotFoundError as e:
    return False, f"文件未找到: {str(e)}"
except PermissionError as e:
    return False, f"权限错误: {str(e)}"
except Exception as e:
    return False, f"处理失败: {str(e)}"
```

### 编码规范

- **输入编码**: 自动检测 UTF-8, UTF-8-SIG, GBK
- **输出编码**: 统一使用 UTF-8-SIG
- **数据类型**: 统一使用字符串类型保持格式

### 路径处理

- 支持相对路径和绝对路径
- 自动创建输出目录
- 处理中文路径和文件名
- 避免路径分隔符问题

### 进度回调

部分服务支持进度回调：

```python
def progress_callback(current, total, message):
    print(f"进度: {current}/{total} - {message}")

extractor = FileFieldExtractorService()
extractor.extract_fields("data/", include_subfolders=True, progress_callback=progress_callback)
```

---

## 集成示例

说明：`v2.0.1` 的 GUI 入口已通过 `SpecWorkflowPage` 统一封装“Data Set / 数据清洗 / Codelist”三种流程，以下示例展示对应的服务层串联调用方式。

### 完整的数据处理流程

```python
from src.utils.data_cleaner_service import DataCleanerService
from src.utils.codelist_service import CodelistService
from src.utils.data_masking_service import DataMaskingService

# 1. 数据清洗
cleaner = DataCleanerService()
cleaner.select_rule_file("rules.xlsx")
cleaner.clean_csv_file("raw_data.csv", "cleaned/")

# 2. Codelist 处理
codelist_processor = CodelistService()
codelist_processor.select_codelist_file("codelist.xlsx")
codelist_processor.process_csv_file("cleaned/C-raw_data.csv", "processed/")

# 3. 数据模糊化
masking_processor = DataMaskingService()
masking_profile = masking_processor.load_profile()
scan_report = masking_processor.scan_pattern1(
    ["DM.csv", "processed/F-raw_data.csv"],
    masking_profile,
)
if scan_report.errors:
    raise ValueError(scan_report.errors)
masking_processor.run_pattern1(
    ["DM.csv", "processed/F-raw_data.csv"],
    output_dir="final/",
    profile=masking_profile,
    scan_report=scan_report,
)
```

### 批量文件处理

```python
import os
from src.utils.csv_to_xlsx_converter_service import CsvToXlsxConverterService

def batch_convert_csv_to_xlsx(input_dir, output_dir):
    """批量转换CSV文件"""
    converter = CsvToXlsxConverterService()
    
    for filename in os.listdir(input_dir):
        if filename.endswith('.csv'):
            input_path = os.path.join(input_dir, filename)
            success, error = converter.convert_file(input_path, output_dir)
            
            if success:
                print(f"✓ {filename} 转换成功")
            else:
                print(f"✗ {filename} 转换失败: {error}")

# 使用示例
batch_convert_csv_to_xlsx("input/", "output/")
```

---

## 版本兼容性

当前 API 版本：2.0.1

### 向后兼容性
- 1.8.x 的核心服务接口保持可用，页面入口已合并为统一工作流（`SpecWorkflowPage`）。
- 1.7.x 及以下版本建议按本文档示例更新导入路径与调用方式。

### 废弃通知
- `DataMaskingService` 旧版兼容接口已移除：`set_baseline_from_dm`、`process_file`、`add_masking_rule`
- 数据模糊化请统一使用 `scan_pattern1` + `run_pattern1` 两阶段流程
- GUI 层已移除旧独立页面：`data_cleaner_page.py`、`codelist_processor_page.py`、`xlsx_restructure_page.py`、`csv_quote_remover_page.py`

### 计划变更
- 2.1.x 版本计划支持更细粒度的异步处理接口
- 2.1.x 版本计划补充数据校验辅助 API

---

## 技术支持

如需技术支持，请：

1. 查阅本 API 文档
2. 参考示例代码
3. 检查错误日志
4. 联系开发团队

**联系方式**: [待添加]

