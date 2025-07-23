# Tools Box API 文档

本文档详细说明了工具箱中各个处理器类的接口和使用方法。

## 目录

1. [日期工具 API](#日期工具-api)
2. [CSV转换器 API](#csv转换器-api) 
3. [XLSX转换器 API](#xlsx转换器-api)
4. [全角转半角转换器 API](#全角转半角转换器-api)
5. [数据清洗器 API](#数据清洗器-api)
6. [Codelist处理器 API](#codelist处理器-api)
7. [数据模糊化处理器 API](#数据模糊化处理器-api)
8. [CSV引号去除处理器 API](#csv引号去除处理器-api)
9. [XLSX重构处理器 API](#xlsx重构处理器-api)

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

### `CsvToXlsxConverter`

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
from src.utils.csv_to_xlsx_converter import CsvToXlsxConverter

converter = CsvToXlsxConverter()
success, error = converter.convert_file("data.csv", "output/")
if success:
    print("转换成功")
else:
    print(f"转换失败: {error}")
```

---

## XLSX转换器 API

### `XlsxToCsvConverter`

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
from src.utils.xlsx_to_csv_converter import XlsxToCsvConverter

converter = XlsxToCsvConverter()
success, error = converter.convert_file("data.xlsx")
```

---

## 全角转半角转换器 API

### `FullwidthToHalfwidthConverter`

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
from src.utils.fullwidth_to_halfwidth_converter import FullwidthToHalfwidthConverter

converter = FullwidthToHalfwidthConverter()
result = converter.convert_text("１２３ＡＢＣ")
print(result)  # "123ABC"
```

---

## 数据清洗器 API

### `DataCleaner`

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
from src.utils.data_cleaning import DataCleaner

cleaner = DataCleaner()
cleaner.select_rule_file("rules.xlsx")
success = cleaner.clean_csv_file("data.csv", "output/")
```

---

## Codelist处理器 API

### `CodelistProcessor`

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
from src.utils.codelist_process import CodelistProcessor

processor = CodelistProcessor()
processor.select_codelist_file("codelist.xlsx")
success = processor.process_csv_file("data.csv")
```

---

## 数据模糊化处理器 API

### `DataMaskingProcessor`

SDTM 数据集模糊化处理器。

#### 方法

##### `__init__()`

初始化模糊化处理器。

##### `set_baseline_from_dm(dm_file_path)`

从 DM.csv 文件设置基准 USUBJID 列表。

**参数:**
- `dm_file_path` (str): DM.csv 文件路径

**返回值:**
- `bool`: 设置是否成功

##### `process_file(input_file, output_path=None)`

处理单个 CSV 文件进行模糊化。

**参数:**
- `input_file` (str): 输入文件路径
- `output_path` (str, optional): 输出路径

**返回值:**
- `bool`: 处理是否成功

##### `add_masking_rule(column_name, masking_function)`

添加自定义模糊化规则。

**参数:**
- `column_name` (str): 列名
- `masking_function`: 模糊化函数

#### 内置模糊化规则
- 年龄减值：AGE 相关字段减 2
- USUBJID 过滤：基于基准列表过滤数据

#### 示例
```python
from src.utils.data_masking_processor import DataMaskingProcessor

processor = DataMaskingProcessor()
processor.set_baseline_from_dm("DM.csv")
success = processor.process_file("AE.csv")
```

---

## CSV引号去除处理器 API

### `CsvQuoteRemoverProcessor`

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
from src.utils.csv_quote_remover_processor import CsvQuoteRemoverProcessor

processor = CsvQuoteRemoverProcessor()
success, error = processor.process_file("data.csv")
if success:
    print("处理成功")
```

---

## XLSX重构处理器 API

### `FileRestructure`

XLSX 文件重构为标准 CDISC SDTM 格式。

#### 方法

##### `restructure_file(input_file, output_path=None, study_id="CIRCULATE")`

重构 XLSX 文件为标准格式。

**参数:**
- `input_file` (str): 输入 XLSX 文件路径
- `output_path` (str, optional): 输出路径
- `study_id` (str): 研究ID

**返回值:**
- `bool`: 重构是否成功

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
from src.utils.restructure_xlsx_file import FileRestructure

restructure = FileRestructure()
success = restructure.restructure_file("AB.xlsx", "output/")
```

---

## 通用接口规范

### 错误处理

所有处理器都遵循统一的错误处理模式：

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

部分处理器支持进度回调：

```python
def progress_callback(current, total, message):
    print(f"进度: {current}/{total} - {message}")

processor.process_files(files, callback=progress_callback)
```

---

## 集成示例

### 完整的数据处理流程

```python
from src.utils.data_cleaning import DataCleaner
from src.utils.codelist_process import CodelistProcessor
from src.utils.data_masking_processor import DataMaskingProcessor

# 1. 数据清洗
cleaner = DataCleaner()
cleaner.select_rule_file("rules.xlsx")
cleaner.clean_csv_file("raw_data.csv", "cleaned/")

# 2. Codelist 处理
codelist_processor = CodelistProcessor()
codelist_processor.select_codelist_file("codelist.xlsx")
codelist_processor.process_csv_file("cleaned/C-raw_data.csv", "processed/")

# 3. 数据模糊化
masking_processor = DataMaskingProcessor()
masking_processor.set_baseline_from_dm("DM.csv")
masking_processor.process_file("processed/F-raw_data.csv", "final/")
```

### 批量文件处理

```python
import os
from src.utils.csv_to_xlsx_converter import CsvToXlsxConverter

def batch_convert_csv_to_xlsx(input_dir, output_dir):
    """批量转换CSV文件"""
    converter = CsvToXlsxConverter()
    
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

当前 API 版本：1.5.0

### 向后兼容性
- 1.4.x 版本的 API 完全兼容
- 1.3.x 版本需要注意参数变化
- 1.2.x 及以下版本建议升级

### 废弃通知
- 无当前废弃的 API

### 计划变更
- 2.0.0 版本将支持异步处理
- 2.0.0 版本将增加数据验证 API

---

## 技术支持

如需技术支持，请：

1. 查阅本 API 文档
2. 参考示例代码
3. 检查错误日志
4. 联系开发团队

**联系方式**: [待添加] 