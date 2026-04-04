[English](README.md) | [中文](README_CN.md)

<div align="center">

```svg
<svg viewBox="0 0 800 120" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad5" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#a8edea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#fed6e3;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="800" height="120" fill="url(#grad5)" rx="10"/>
  <text x="400" y="70" font-size="48" font-weight="bold" fill="white" text-anchor="middle" font-family="monospace">
    DataForge Studio
  </text>
  <text x="400" y="105" font-size="16" fill="#333333" text-anchor="middle" font-family="sans-serif">
    Windows Desktop Toolbox • SDTM Data Processing • Fluent Design
  </text>
</svg>
```

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Windows](https://img.shields.io/badge/Platform-Windows-0078d4?style=flat-square&logo=windows)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?style=flat-square&logo=qt)
![Fluent Design](https://img.shields.io/badge/Design-Fluent-0078d4?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

**Windows desktop toolbox for SDTM-oriented data processing with Fluent Design UI. Format conversion, data cleaning, masking, extraction, and batch utilities all in one studio.**

[Features](#features) • [Getting Started](#getting-started) • [User Guide](#user-guide) • [Tools](#tools) • [Architecture](#architecture)

</div>

---

## Overview

**DataForge Studio** (工具箱) is a comprehensive Windows desktop application for data professionals working with SDTM and clinical trial datasets. Built with PySide6 and QFluentWidgets, it provides a native Windows 11 Fluent Design interface with powerful data processing capabilities.

**Key Strengths:**
- 🎨 **Windows 11 Fluent Design**: Native, modern UI with smooth animations and dark/light modes
- 📊 **SDTM-Focused**: Specialized tools for clinical data processing
- 🔧 **Format Conversion**: Excel ↔ CSV ↔ SAS ↔ Parquet
- 🧹 **Data Cleaning**: Missing value handling, deduplication, outlier detection
- 🔐 **Data Masking**: PII anonymization, field encryption, value scrambling
- 📋 **Field Extraction**: Pattern matching, subset selection, field mapping
- ⚙️ **Batch Utilities**: Multi-file processing, automation scripts
- 📦 **PyInstaller Build**: Ready-to-deploy .exe executable for Windows

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🎨 **Fluent UI** | Windows 11 Fluent Design System with dark/light themes |
| 📦 **Format Conversion** | XLSX ↔ CSV ↔ SAS ↔ Parquet with encoding support |
| 🧹 **Data Cleaning** | Remove duplicates, handle missing values, outlier detection |
| 🔐 **Data Masking** | PII protection, field-level encryption, value hashing |
| 📊 **Field Extraction** | Regex-based extraction, field mapping, subsetting |
| 🔄 **Batch Processing** | Process multiple files with same rules |
| 📈 **Statistics & Analysis** | Data profiling, quality metrics, summary reports |
| 💾 **Project Workspace** | Save/load processing configurations |
| ⚡ **Multi-Threading** | Non-blocking UI during long operations |
| 📚 **Help & Documentation** | Integrated help, user manual, API docs |

---

## Architecture

```mermaid
graph TB
    A["📁 Input Data<br/>(XLSX/CSV/SAS/Parquet)"] -->|Load| B["🔄 Data Loader"]
    B --> C["📊 Main Window<br/>(DataForge Studio)"]

    C -->|User selects tool| D{["🛠️ Tool Selection"]}

    D -->|Format| E["🔀 Converter<br/>(Format Conversion)"]
    D -->|Cleaning| F["🧹 Cleaner<br/>(Data Cleaning)"]
    D -->|Masking| G["🔐 Masker<br/>(PII Protection)"]
    D -->|Extraction| H["📋 Extractor<br/>(Field Extraction)"]
    D -->|Batch| I["⚙️ Batch Processor<br/>(Multi-file)"]

    E -->|Transform| J["💾 Output Data"]
    F -->|Clean| J
    G -->|Anonymize| J
    H -->|Extract| J
    I -->|Process| J

    J -->|Export| K["📤 Save<br/>(xlsx/csv/sas/parquet)"]

    style A fill:#e3f2fd
    style C fill:#c8e6c9
    style J fill:#fff9c4
    style K fill:#f0f4c3
```

### Component Architecture

```
DataForge Studio
├── GUI Layer (PySide6 + QFluentWidgets)
│   ├── Main Window
│   ├── Tool Selection Panel
│   ├── Preview Pane
│   └── Status/Progress Bar
│
├── Tools Layer
│   ├── Converter (format conversion)
│   ├── Cleaner (data quality)
│   ├── Masker (PII protection)
│   ├── Extractor (field ops)
│   └── BatchProcessor (multi-file)
│
├── Data Layer (pandas/numpy)
│   ├── DataLoader (multi-format read)
│   ├── DataProcessor (transform)
│   └── DataExporter (multi-format write)
│
└── Config Layer (JSON/TOML)
    ├── Project config
    ├── Tool presets
    └── User preferences
```

---

## Getting Started

### Prerequisites

- **Windows 7 or newer** (Windows 11 recommended for full Fluent Design)
- **Python 3.11+**
- **~200 MB disk space**

### Installation

#### Option 1: Python Installation (For Developers)

```bash
# Clone repository
git clone https://github.com/hakupao/tools_box.git
cd tools_box

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e .

# Launch
python -m tools_box
```

#### Option 2: Standalone .exe (For End Users)

Download the latest release from [Releases](https://github.com/hakupao/tools_box/releases).

```bash
# Just double-click DataForge_Studio.exe
# No Python installation required!
```

### 5-Minute Quick Start

```
1. Launch DataForge Studio
2. Click "Load Data" → select your CSV/Excel file
3. Choose a tool from the left panel:
   - Format Conversion
   - Data Cleaning
   - Data Masking
   - Field Extraction
   - Batch Processing
4. Configure options in the tool panel
5. Click "Process" or "Preview"
6. Export results via "Save As"
```

---

## User Guide

### Loading Data

1. **File Menu** → **Open** or drag & drop file
2. Supported formats: `XLSX`, `CSV`, `SAS7BDAT`, `Parquet`
3. Encoding auto-detected; can override if needed
4. Preview shows first 100 rows

### Format Conversion

**Convert between data formats:**

```
XLSX → CSV          Excel to comma-separated values
CSV → XLSX          CSV to Excel workbook
CSV → SAS          CSV to SAS dataset
Parquet → CSV      Parquet to CSV
```

**Options:**
- Delimiter (,, ;, \t, |)
- Encoding (utf-8, latin1, cp1252, etc.)
- Decimal separator (., ,)
- Sheet selection (for XLSX)

### Data Cleaning

**Remove data quality issues:**

- **Remove Duplicates**: Exact or fuzzy matching
- **Handle Missing Values**: Delete rows, fill forward, mean imputation
- **Outlier Detection**: IQR method, z-score method
- **Data Type Correction**: Auto-detect and convert types
- **Trim Whitespace**: Remove leading/trailing spaces

**Configuration:**
```json
{
  "duplicates": {
    "enabled": true,
    "method": "exact",
    "subset": ["USUBJID", "VISIT"]
  },
  "missing": {
    "method": "delete_row",
    "threshold": 0.5
  },
  "outliers": {
    "detect": true,
    "method": "iqr",
    "action": "flag"
  }
}
```

### Data Masking

**Protect PII and sensitive information:**

- **Field Masking**: Replace values (e.g., names → "XXX")
- **Hashing**: SHA-256 hash sensitive fields
- **Encryption**: AES-256 field encryption
- **Date Shifting**: Add random days to dates
- **Value Scrambling**: Shuffle/randomize values

**Example:**
```json
{
  "fields_to_mask": {
    "SUBJID": "hash",
    "FNAME": "replace",
    "LNAME": "replace",
    "DOB": "date_shift",
    "ADDRESS": "encryption"
  },
  "encryption_key": "use-key-from-vault"
}
```

### Field Extraction

**Extract and manipulate specific fields:**

- **Regex Extraction**: Pattern matching (e.g., extract area codes)
- **Column Selection**: Keep/drop specific columns
- **Field Mapping**: Rename columns
- **Calculated Fields**: Create new fields from formulas
- **Value Substitution**: Find & replace values

**Example:**
```
Extract area code from phone number
Pattern: (\d{3})-\d{3}-\d{4}
Replace: $1
Result: "555-123-4567" → "555"
```

### Batch Processing

**Process multiple files with the same rules:**

1. **Select Tool** (Format Conversion, Cleaning, etc.)
2. **Select Input Folder** (all matching files)
3. **Configure Tool Options**
4. **Click "Start Batch"**
5. Progress shown per file
6. All results saved to output folder

---

## Tools Overview

### Format Converter
Convert between Excel, CSV, SAS, Parquet with full control over encoding and delimiters.

### Data Cleaner
Remove duplicates, handle missing values, detect outliers, auto-correct data types.

### Data Masker
Anonymize PII through masking, hashing, encryption, and date shifting.

### Field Extractor
Extract patterns, select columns, create calculated fields, map/rename columns.

### Batch Processor
Apply any tool to multiple files with progress tracking.

---

## Project Structure

<details>
<summary><b>📁 Complete Directory Layout</b></summary>

```
tools_box/
│
├── 📄 README.md & README_CN.md
├── 📄 pyproject.toml           # Python project config
├── 📄 requirements.txt
├── 📄 CHANGELOG.md
│
├── 🎨 tools_box/ (Package)
│   ├── __main__.py             # Entry point
│   ├── __init__.py
│   ├── main_window.py          # Main GUI window
│   ├── config.py               # Configuration management
│   │
│   ├── gui/
│   │   ├── main_panel.py       # Main workspace
│   │   ├── tool_selector.py    # Tool selection panel
│   │   ├── preview_pane.py     # Data preview
│   │   ├── status_bar.py       # Status & progress
│   │   ├── dialogs.py          # File dialogs, settings
│   │   └── styles.css          # Fluent Design styles
│   │
│   ├── tools/
│   │   ├── base_tool.py        # Base tool class
│   │   ├── converter.py        # Format conversion
│   │   ├── cleaner.py          # Data cleaning
│   │   ├── masker.py           # Data masking
│   │   ├── extractor.py        # Field extraction
│   │   └── batch_processor.py  # Batch operations
│   │
│   ├── data/
│   │   ├── loader.py           # Multi-format data loading
│   │   ├── processor.py        # Data transformation
│   │   ├── exporter.py         # Multi-format export
│   │   └── validator.py        # Data validation
│   │
│   ├── utils/
│   │   ├── crypto.py           # Encryption utilities
│   │   ├── regex.py            # Pattern matching
│   │   ├── hash.py             # Hashing functions
│   │   └── logging.py          # Logging setup
│   │
│   └── resources/
│       ├── icons/
│       ├── themes/
│       └── config_templates/
│
├── 📚 docs/
│   ├── 用户手册.md             # User manual (Chinese)
│   ├── API文档.md              # API documentation
│   ├── 开发文档.md             # Developer guide
│   ├── QUICK_START.md
│   └── assets/
│       ├── gui_screenshot.png
│       └── tutorial.md
│
├── 📦 packaging/
│   ├── pyinstaller_config.spec # PyInstaller spec
│   ├── build_executable.py     # Build script
│   └── installer_config.nsi    # NSIS installer
│
└── ✅ tests/
    ├── test_converter.py
    ├── test_cleaner.py
    ├── test_masker.py
    ├── test_extractor.py
    └── test_batch_processor.py
```

</details>

---

## Advanced Usage

<details>
<summary><b>🎛️ Custom Tool Development</b></summary>

Create custom tools by extending `BaseTool`:

```python
from tools_box.tools.base_tool import BaseTool

class MyCustomTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="My Custom Tool",
            description="Does something useful"
        )

    def process(self, dataframe, **options):
        # Your processing logic
        df = dataframe.copy()
        # ... transformation code ...
        return df

    def get_options_ui(self):
        # Return QWidget with options UI
        pass
```

</details>

<details>
<summary><b>🤖 Automation Scripts</b></summary>

Run DataForge Studio via Python API:

```python
from tools_box.data.loader import DataLoader
from tools_box.tools.converter import Converter

# Load data
loader = DataLoader()
df = loader.load("input.xlsx")

# Convert format
converter = Converter()
result = converter.process(
    df,
    input_format="xlsx",
    output_format="csv",
    encoding="utf-8"
)

# Export
loader.save(result, "output.csv")
```

</details>

<details>
<summary><b>🔐 Encryption Key Management</b></summary>

Secure encryption keys:

```python
import os
from tools_box.utils.crypto import EncryptionManager

# Load key from environment variable (recommended)
key = os.environ.get("DATAFORGE_ENCRYPTION_KEY")

manager = EncryptionManager(key)
encrypted_data = manager.encrypt("sensitive_value")
decrypted_data = manager.decrypt(encrypted_data)
```

</details>

---

## Dependencies

```
PySide6>=6.5              # Qt GUI framework
QFluentWidgets>=0.4.4    # Fluent Design UI components
pandas>=2.0              # Data manipulation
numpy>=1.21              # Numerical operations
openpyxl>=3.0            # Excel I/O
pyarrow>=10.0            # Parquet support
cryptography>=38.0       # Encryption
```

---

## Building Executable

### Using PyInstaller

```bash
# Install build dependencies
pip install pyinstaller

# Build executable
python packaging/build_executable.py

# Output: dist/DataForge_Studio.exe
```

### Creating Installer

```bash
# Install NSIS (Nullsoft Installer System)
# Download from https://nsis.sourceforge.io/

# Build installer
makensis packaging/installer_config.nsi

# Output: dist/DataForge_Studio_Installer.exe
```

---

## Configuration & Settings

### User Settings (JSON)

Located in: `%APPDATA%/DataForge Studio/config.json`

```json
{
  "theme": "dark",
  "language": "en",
  "recent_files": [
    "C:/Data/file1.csv",
    "C:/Data/file2.xlsx"
  ],
  "tool_presets": {
    "cleaning": {
      "remove_duplicates": true,
      "handle_missing": "delete"
    }
  }
}
```

---

## Performance Tips

- 📊 **Large Files**: Use Parquet format for better performance
- 🔄 **Batch Processing**: Process files in batches of 100-1000
- 💾 **Memory**: Monitor RAM when processing files > 500 MB
- 🚀 **Threading**: UI remains responsive during processing
- 📈 **Optimization**: Enable caching for repeated operations

---

## Troubleshooting

<details>
<summary><b>Common Issues</b></summary>

| Issue | Solution |
|-------|----------|
| File won't open | Check encoding, try auto-detect |
| Data shows as corrupted | Verify file format, check delimiters |
| GUI freezes during processing | Wait for operation to complete (check taskbar) |
| Out of memory error | Process file in smaller chunks or use Parquet |
| Encryption key lost | Keep backup in secure vault (e.g., Azure Key Vault) |

</details>

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
# Development setup
git clone https://github.com/hakupao/tools_box.git
cd tools_box
pip install -e ".[dev]"
pytest tests/
```

---

## Roadmap

- [ ] Database connector (SQL Server, PostgreSQL)
- [ ] Advanced visualization (charts, profiling reports)
- [ ] Machine learning features (clustering, classification)
- [ ] REST API server mode
- [ ] Cloud storage integration (Azure, AWS)
- [ ] Real-time data validation rules

---

## License

MIT License © 2024 hakupao

---

## Citation

```bibtex
@software{dataforge2024,
  author = {hakupao},
  title = {DataForge Studio: Windows Desktop Toolbox for SDTM Data Processing},
  url = {https://github.com/hakupao/tools_box},
  year = {2024}
}
```

---

## Support

- 📧 **Issues**: [GitHub Issues](https://github.com/hakupao/tools_box/issues)
- 📖 **Documentation**: [docs/](docs/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/hakupao/tools_box/discussions)
- 📚 **User Manual**: [docs/用户手册.md](docs/用户手册.md)

---

<div align="center">

**[⬆ Back to Top](#-dataforge-studio)**

Built with precision for data professionals

</div>
