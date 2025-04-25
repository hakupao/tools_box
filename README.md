# Windows 工具箱

这是一个基于 Python 的 Windows 工具箱程序，提供了多个实用工具功能，旨在提高日常工作效率。

## 项目结构

```plaintext
tools_box/
├── src/                    # 源代码目录
│   ├── __init__.py
│   ├── main.py            # 主程序入口
│   ├── gui/               # GUI 相关代码
│   │   ├── __init__.py
│   │   ├── main_window.py # 主窗口
│   │   └── widgets/       # 自定义控件
│   │       ├── __init__.py
│   │       ├── csv_converter.py  # CSV 转换工具
│   │       ├── date_converter.py # 日期转换工具
│   │       ├── data_cleaner.py   # 数据清洗工具
│   │       ├── xlsx_converter.py # XLSX 转换工具
│   │       ├── edc_site_adder.py # EDC 站点添加工具
│   │       ├── xlsx_file_restructuring.py # XLSX 文件重构工具
│   │       └── additional_widgets.py # 其他自定义控件
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── csv_converter_utils.py # CSV 转换工具函数
│       ├── date_utils.py         # 日期处理工具函数
│       ├── data_cleaning.py      # 数据清洗工具函数
│       ├── restructure_xlsx_file.py # XLSX 文件重构工具函数
│       └── additional_utils.py   # 其他工具函数
├── requirements.txt       # 项目依赖
├── tools_box.spec         # PyInstaller 打包配置
├── build/                 # 构建目录
│   └── tools_box/         # 构建输出
├── dist/                  # 分发目录
├── temp_tkdnd/            # tkdnd 临时文件
│   └── tkdnd/
└── README.md              # 项目说明
```

## 功能特点

- **日期转换工具**
  - 支持将日期格式转换为 ISO8601 格式
  - 自动补零
  - 保留空行和非日期数据
  - 支持批量转换

- **CSV 转换工具**
  - 支持 CSV 文件的格式转换
  - 提供数据清洗和格式化功能

- **XLSX 转换工具**
  - 支持 XLSX 文件的格式转换
  - 提供多表合并和数据提取功能

- **XLSX 文件重构工具**
  - 支持多表合并为单一 CSV 文件
  - 按预定义字段顺序和排序规则重构数据
  - 自动生成序号字段
  - 支持拖拽文件和文件夹
  - 支持自定义输出路径
  - 实时显示转换进度和错误提示

- **数据清洗工具**
  - 支持根据仕样书进行数据清洗
  - 自动过滤非目标患者数据
  - 根据配置规则保留特定字段
  - 应用自定义行过滤逻辑
  - 清理空行数据
  - 支持拖拽文件和文件夹
  - 输出文件自动添加前缀标识
  - 支持自定义输出路径
  - 实时显示处理进度

- **EDC 站点添加工具**
  - 支持自动添加 EDC 站点
  - 可配置点击坐标和循环次数
  - 实时显示处理日志
  - 支持 ESC 键随时终止处理
  - 提供友好的用户界面

## 安装说明

1. 确保已安装 Python 3.10.11。
2. 安装依赖包：

   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 运行主程序：

   ```bash
   python -m src.main
   ```

2. 在主界面点击相应的功能按钮使用工具。

## 系统要求

- Windows 操作系统
- Python 3.10.11
- tkinter（Python 标准库）

## 开发说明

- 新增功能时，请在 `src/gui/widgets/` 目录下创建新的窗口类。
- 工具函数应放在 `src/utils/` 目录下。
- 主窗口类在 `src/gui/main_window.py` 中维护。
- 确保新增功能的代码符合项目的代码风格，并添加必要的注释和文档。

## 贡献指南

欢迎对本项目进行贡献！请遵循以下步骤：

1. Fork 本仓库。
2. 创建一个新的分支：

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. 提交代码并推送到你的分支：

   ```bash
   git commit -m "Add your feature description"
   git push origin feature/your-feature-name
   ```

4. 提交 Pull Request。

## 许可证

本项目基于 MIT 许可证开源，详情请参阅 LICENSE 文件。

## 写给作者

打包更新方法

1. 清理所有临时文件和构建目录：

   ```powershell
   Remove-Item -Path build,dist,temp_tkdnd -Recurse -Force -ErrorAction SilentlyContinue
   ```

2. 重新打包：

   ```bash
   python -m PyInstaller tools_box.spec --clean
   ```
