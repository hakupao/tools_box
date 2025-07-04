﻿# XLSX文件制作规范

本文档详细说明了制作符合XLSX文件重构工具要求的文件规范和注意事项。

## 1. 文件命名规范

### 1.1 基本要求
- **文件名格式**：必须以字母开头，如 `AB.xlsx`、`CM.xlsx`、`LB.xlsx` 等
- **域名识别**：程序会从文件名提取域名（如AB、CM、LB），用作最终CSV文件的DOMAIN字段值
- **扩展名**：必须为 `.xlsx` 格式

### 1.2 示例
```
✅ 正确示例：
AB.xlsx
CM.xlsx
LB.xlsx
AE.xlsx

❌ 错误示例：
123.xlsx     # 不能以数字开头
test.xlsx    # 域名不在支持列表中
AB.xls       # 扩展名错误
```

## 2. 工作表命名规范

### 2.1 支持的命名方式
程序支持两种工作表命名方式：

#### 标准命名（推荐）
- **格式**：`域名+数字`
- **示例**：`AB1`、`AB2`、`CM1`、`CM2` 等
- **说明**：数字部分会被用作内部序号（SUPPSEQ）

#### 默认命名
- **格式**：`Sheet+数字`
- **示例**：`Sheet1`、`Sheet2`、`Sheet3` 等
- **说明**：Excel默认的工作表命名方式

### 2.2 重要提醒
- **不符合命名规范的工作表将被跳过处理**
- 建议使用标准命名方式以提高可读性
- 工作表顺序会影响最终的SUPPSEQ值

## 3. 数据字段要求

### 3.1 标准字段
每个域都有预定义的标准字段列表，包括但不限于：

#### 通用字段
- `STUDYID`：研究ID（程序自动填充）
- `DOMAIN`：域名（程序自动填充）
- `USUBJID`：受试者唯一标识符
- `[域名]SEQ`：序号字段（程序自动生成）

#### 域特定字段
不同域有不同的标准字段，如：
- **AE域**：`AETERM`、`AEDECOD`、`AESEV`、`AESER` 等
- **CM域**：`CMTRT`、`CMDECOD`、`CMCAT`、`CMSCAT` 等
- **LB域**：`LBTESTCD`、`LBTEST`、`LBORRES`、`LBORRESU` 等

### 3.2 字段处理规则
- **缺失字段**：程序会自动补充标准字段，缺失的字段填充为空值
- **SUBJID字段**：如果存在`SUBJID`字段，会自动重命名为`USUBJID`
- **额外字段**：非标准字段会保留，并按字母顺序排列在标准字段之后

## 4. 数据格式要求

### 4.1 日期格式
- **自动检测**：程序会自动检测日期列
- **标准化格式**：所有日期会被格式化为 `YYYY-MM-DD` 格式
- **建议**：原始数据使用Excel标准日期格式，避免文本格式的日期

### 4.2 数据类型
- **最终格式**：所有数据最终会转换为字符串格式
- **空值处理**：空值会被填充为空字符串
- **数值数据**：数值会保持原有精度，转换为字符串

### 4.3 特殊字符
- 避免使用特殊字符，如制表符、换行符等
- 如需使用逗号，注意CSV格式的兼容性

## 5. 数据内容要求

### 5.1 必需数据
- **USUBJID**：每行数据必须有受试者标识符
- **关键字段**：根据域的特性，确保关键字段有数据

### 5.2 数据一致性
- **编码一致性**：同一概念的编码在不同工作表中应保持一致
- **格式一致性**：同类型数据的格式应保持一致
- **单位一致性**：数值数据的单位应明确且一致

## 6. 支持的域类型

### 6.1 临床域
- **AG**：伴随给药
- **CM**：伴随用药
- **EC**：暴露检查
- **EX**：暴露
- **ML**：里程碑
- **PR**：程序
- **SU**：物质使用

### 6.2 事件域
- **AE**：不良事件
- **BE**：生物等效性事件
- **CE**：临床事件
- **DS**：处置
- **DV**：偏离
- **HO**：医疗保健遭遇
- **MH**：病史

### 6.3 检查域
- **BS**：生物样本
- **CP**：细胞表型
- **CV**：心血管检查
- **DA**：药物浓度
- **EG**：心电图
- **FT**：功能测试
- **LB**：实验室检查
- **MB**：微生物学
- **VS**：生命体征

### 6.4 其他域
- **DM**：人口统计学
- **SE**：研究元素
- **SM**：研究里程碑
- **CO**：评论

## 7. 数据排序规则

程序会根据预定义的排序键对数据进行排序：

### 7.1 常见排序规则
- **主排序**：通常按 `USUBJID` 排序
- **次排序**：按 `SUPPSEQ`（工作表序号）排序
- **其他排序**：根据域的特性，可能包括日期、类别等字段

### 7.2 排序示例
```
IE域排序：USUBJID → SUPPSEQ → IETESTCD → IECAT → IESCAT
AE域排序：USUBJID → SUPPSEQ → AESTDTC → AEENDY → AEDUR
CM域排序：USUBJID → SUPPSEQ → EPOCH → CMCAT → CMSCAT → CMSTDTC
```

## 8. 最佳实践建议

### 8.1 数据准备
1. **数据完整性检查**：确保关键字段有数据
2. **格式统一**：统一日期、数值、编码格式
3. **数据验证**：检查数据的逻辑一致性

### 8.2 文件组织
1. **命名规范**：严格按照要求命名文件和工作表
2. **结构清晰**：每个工作表代表一个数据集合
3. **版本管理**：建立文件版本管理机制

### 8.3 质量控制
1. **数据备份**：转换前备份原始文件
2. **结果验证**：转换后检查CSV文件内容
3. **错误处理**：记录和处理转换过程中的错误

## 9. 常见问题及解决方案

### 9.1 工作表被跳过
**问题**：某些工作表没有被处理
**原因**：工作表命名不符合规范
**解决**：重命名工作表为标准格式（如AB1、AB2）或默认格式（如Sheet1、Sheet2）

### 9.2 日期格式异常
**问题**：日期显示不正确
**原因**：原始数据中日期为文本格式
**解决**：在Excel中将日期列格式设置为日期类型

### 9.3 字段缺失
**问题**：输出文件中某些字段为空
**原因**：原始数据缺少标准字段
**解决**：这是正常现象，程序会自动补充标准字段并填充空值

### 9.4 数据排序异常
**问题**：输出数据排序不符合预期
**原因**：排序字段数据格式不一致
**解决**：确保排序字段（如USUBJID、日期字段）格式一致

## 10. 输出文件说明

### 10.1 文件特征
- **格式**：CSV文件，UTF-8编码
- **命名**：与原XLSX文件同名，扩展名为.csv
- **内容**：所有工作表数据合并为单个表格

### 10.2 字段顺序
1. **标准字段**：按预定义顺序排列
2. **SUPPSEQ字段**：已删除（仅用于内部处理）
3. **其他字段**：按字母顺序排列在标准字段之后

---

**注意**：本规范基于当前版本的XLSX文件重构工具，如有更新请及时调整文件制作方式。