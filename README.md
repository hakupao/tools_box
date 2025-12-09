# Tools Box

一个基于 Python 和 Tkinter 开发的多功能数据处理工具集合，提供拖拽功能和现代化的用户界面。

## 功能特性

- 🖱️ 支持文件拖拽操作
- 🎨 现代化的用户界面设计
- 📦 多工具集成（9个专业工具）
- 🔄 批量文件处理能力
- 📊 数据格式转换与清洗
- 🔧 自动化操作支持
- 🌐 跨平台支持（Windows）

## 工具列表

### 数据转换工具
1. **日期转换工具** - 支持多种日期格式的智能转换
2. **文件格式转换工具** - 单一界面切换三种模式：CSV 转 XLSX、XLSX 转 CSV(UTF-8 BOM)、CSV 转 UTF-8(BOM)
3. **全角转半角工具** - 将全角字符转换为半角字符

### 数据处理工具
4. **数据清洗工具** - 基于仕样书规则进行数据清洗和过滤
5. **Codelist处理工具** - 编码映射和多语言值转换
6. **数据模糊化工具** - SDTM数据集隐私保护和模糊化处理
7. **CSV引号去除工具** - 智能清理CSV文件中的多余引号

### 专业工具
8. **EDC站点添加工具** - 自动化EDC系统的站点批量添加
9. **生成Data Set工具** - XLSX文件重构为标准CDISC SDTM格式

## 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10/11
- **内存**: 建议 4GB 或以上
- **磁盘空间**: 至少 100MB 可用空间

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
│   ├── utils/             # 工具函数和处理器
│   ├── main.py            # 主程序入口
│   └── version.py         # 版本信息
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

### 自动化库
- **pyautogui** (0.9.54) - GUI 自动化控制
- **pygetwindow** (0.0.9) - 窗口管理
- **pywin32** (306) - Windows API 接口
- **mouse** - 鼠标控制
- **keyboard** (0.13.5) - 键盘控制

### 打包工具
- **pyinstaller** (6.3.0) - 程序打包

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

- **现代化界面**: 采用现代化的 GUI 设计风格
- **响应式布局**: 支持窗口大小调整和适配
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
