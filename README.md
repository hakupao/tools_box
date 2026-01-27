# Tools Box

一个基于 Python 和 Tkinter 开发的多功能数据处理工具集合，提供拖拽功能和现代化的用户界面。

## 功能特性

- 🖱️ 支持文件拖拽操作
- 🎨 分类卡片式主界面与滚动浏览
- 📦 多工具集成（12个专业工具）
- 🔄 批量文件处理能力
- 📊 数据格式转换与清洗
- 🔍 字段提取与 HTML 死链检测
- 🔧 自动化操作支持
- 🌐 Windows 平台支持

## 工具列表

### 文件处理工具
1. **文件格式转换工具** - 单一界面切换三种模式：CSV 转 XLSX、XLSX 转 CSV(UTF-8 BOM)、CSV 转 UTF-8(BOM)
2. **工作表拆分工具** - 将 Excel 工作表拆分为多个 CSV（UTF-8 BOM）
3. **生成 Data Set 工具** - XLSX 文件重构为标准 CDISC SDTM 格式
4. **获取文件字段工具** - 批量提取 CSV/XLSX 字段并输出汇总
5. **死链检测工具** - 扫描 HTML 文件/文件夹并生成检测报告

### 数据处理工具
6. **数据清洗工具** - 基于仕样书规则进行数据清洗和过滤
7. **Codelist 处理工具** - 编码映射和多语言值转换
8. **数据模糊化工具** - SDTM 数据集隐私保护和模糊化处理
9. **EDC 站点添加工具** - 自动化 EDC 系统的站点批量添加

### 格式转换工具
10. **日期转换工具** - 支持多种日期格式的智能转换
11. **全角转半角工具** - 将全角字符转换为半角字符
12. **CSV 引号去除工具** - 智能清理 CSV 文件中的多余引号

## 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10/11
- **内存**: 建议 4GB 或以上
- **磁盘空间**: 至少 100MB 可用空间
- **网络**: 死链检测功能需要可访问网络

## 安装说明

### 从源码安装

1. 克隆仓库：
```bash
git clone [repository-url]
cd tools_box
```

2. 创建虚拟环境（推荐）：
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

### 使用打包版本

项目提供了打包好的可执行文件（`工具箱.exe`），可以直接运行，无需安装 Python 环境。

## 使用方法

### 开发环境
```bash
python src/main.py
```

### 打包版本
直接双击运行 `工具箱.exe` 文件。

## 项目结构

```
tools_box/
├── src/                    # 源代码目录
│   ├── gui/               # 图形界面相关代码
│   │   ├── main_window.py # 主窗口
│   │   └── widgets/       # 各工具窗口组件
│   │       ├── date_converter.py           # 日期转换窗口
│   │       ├── file_format_converter.py    # 文件格式转换窗口（CSV/XLSX/BOM）
│   │       ├── xlsx_sheet_splitter.py      # 工作表拆分窗口
│   │       ├── file_field_extractor.py     # 获取文件字段窗口
│   │       ├── dead_link_checker.py        # 死链检测窗口
│   │       ├── fullwidth_halfwidth_converter.py # 全角转半角窗口
│   │       ├── data_cleaner.py             # 数据清洗窗口
│   │       ├── codelist_processor.py       # Codelist处理窗口
│   │       ├── data_masking.py             # 数据模糊化窗口
│   │       ├── csv_quote_remover.py        # CSV引号去除窗口
│   │       ├── edc_site_adder.py           # EDC站点添加窗口
│   │       └── xlsx_file_restructuring.py  # XLSX重构窗口
│   └── utils/             # 工具函数和处理器
│       ├── date_utils.py                   # 日期处理工具
│       ├── csv_to_xlsx_converter.py        # CSV转XLSX处理器
│       ├── xlsx_to_csv_converter.py        # XLSX转CSV处理器
│       ├── xlsx_sheet_splitter.py          # 工作表拆分处理器
│       ├── csv_encoding_converter.py       # CSV转UTF-8(BOM)处理器
│       ├── file_field_extractor.py         # 获取文件字段处理器
│       ├── dead_link_checker.py            # 死链检测处理器
│       ├── fullwidth_to_halfwidth_converter.py # 全角转半角处理器
│       ├── data_cleaning.py                # 数据清洗处理器
│       ├── codelist_process.py             # Codelist处理器
│       ├── data_masking_processor.py       # 数据模糊化处理器
│       ├── csv_quote_remover_processor.py  # CSV引号去除处理器
│       └── restructure_xlsx_file.py        # XLSX重构处理器
├── docs/                  # 项目文档
├── requirements.txt       # 项目依赖
├── tools_box.spec        # PyInstaller 打包配置
├── CHANGELOG.md          # 更新日志
└── README.md            # 项目说明
```

## 主要依赖项

### 核心库
- **pandas** (2.1.4) - 数据处理和分析
- **openpyxl** (3.1.2) - Excel 文件读写
- **tkinterdnd2** (0.3.0) - 文件拖拽功能支持

### 网络与解析
- **requests** (>=2.31.0) - 网络请求与链接检测
- **beautifulsoup4** (>=4.12.0) - HTML 解析

### 自动化库
- **pyautogui** (0.9.54) - GUI 自动化控制
- **pygetwindow** (0.0.9) - 窗口管理
- **pywin32** (306) - Windows API 接口
- **mouse** - 鼠标控制
- **keyboard** (0.13.5) - 键盘控制

### 打包工具
- **pyinstaller** (6.3.0) - 程序打包
- **backports.tarfile** (>=1.2.0) - 打包兼容性支持

## 开发说明

### 代码规范
- 遵循 PEP8 代码风格规范
- 使用 4 个空格缩进
- 行长度限制为 100 字符
- 所有函数和类需要添加中文文档字符串

### 测试
1. 确保已安装所有开发依赖
2. 运行单元测试（如果存在）
3. 进行功能测试验证

### 打包发布

1. 清理临时文件：
```powershell
Remove-Item -Path build,dist,temp_tkdnd -Recurse -Force -ErrorAction SilentlyContinue
```

2. 重新打包：
```bash
python -m PyInstaller tools_box.spec --clean
```

## 技术特点

- **现代化界面**: 分类卡片布局与统一的 GUI 风格
- **响应式布局**: 支持窗口大小调整和滚动适配
- **错误处理**: 完善的异常处理和用户提示机制
- **内存优化**: 针对大文件处理进行了内存优化
- **编码兼容**: 统一使用 UTF-8-SIG 编码处理中文

## 许可证

本项目采用 [MIT 许可证](LICENSE)

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

欢迎提交 Issue 和 Pull Request 来帮助改进项目！

## 联系方式

- 项目维护者: Tools Box Team
- 邮箱: [待添加]
- 项目主页: [待添加]

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新历史。
