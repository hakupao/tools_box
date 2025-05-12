# Tools Box

一个基于 Python 和 Tkinter 开发的实用工具集合，提供拖拽功能和现代化的用户界面。

## 功能特性

- 支持文件拖拽操作
- 现代化的用户界面
- 多工具集成
  - 日期转换工具
  - CSV/XLSX格式互转
  - EDC站点自动添加
  - 数据集生成
  - 数据清洗
  - Codelist处理
- 跨平台支持（Windows）

## 系统要求

- Python 3.8 或更高版本
- Windows 操作系统

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

项目提供了打包好的可执行文件，可以直接运行，无需安装 Python 环境。

## 使用方法

1. 运行程序：
```bash
python src/main.py
```

2. 或者直接运行打包后的可执行文件。

## 项目结构

```
tools_box/
├── src/                # 源代码目录
│   ├── gui/           # 图形界面相关代码
│   ├── utils/         # 工具函数
│   ├── main.py        # 主程序入口
│   └── version.py     # 版本信息
├── requirements.txt   # 项目依赖
└── tools_box.spec    # PyInstaller 打包配置
```

## 依赖项

- pandas: 数据处理
- openpyxl: Excel 文件处理
- tkinterdnd2: 拖拽功能支持
- pyinstaller: 程序打包
- pyautogui: 自动化控制
- pygetwindow: 窗口管理
- pywin32: Windows API 接口
- mouse: 鼠标控制
- keyboard: 键盘控制

## 开发说明

1. 确保已安装所有开发依赖
2. 遵循项目代码规范
3. 提交代码前运行测试

## 许可证

[在此添加许可证信息]

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

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

## 联系方式

[在此添加联系方式]
