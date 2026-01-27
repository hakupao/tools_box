import os
import re
from typing import Callable, Dict, List, Optional, Set

import pandas as pd


class XlsxSheetSplitter:
    """Excel 工作表拆分处理器。"""

    INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')
    CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1f]')
    RESERVED_NAMES = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    def __init__(self, output_encoding: str = "utf-8-sig") -> None:
        self.output_encoding = output_encoding

    def split_file(
        self,
        input_file: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, object]:
        """将单个 Excel 文件拆分为多个 CSV（按工作表）。

        Args:
            input_file: 输入 Excel 文件路径（.xlsx）。
            output_path: 输出目录，None 时输出到原文件所在目录。
            progress_callback: 进度回调 (current, total, sheet_name)。

        Returns:
            dict: 包含 output_dir、output_files、errors、total_sheets、success。
        """
        if not os.path.isfile(input_file):
            raise FileNotFoundError(f"文件不存在: {input_file}")

        output_dir = output_path or os.path.dirname(input_file)
        os.makedirs(output_dir, exist_ok=True)

        excel_file = pd.ExcelFile(input_file, engine="openpyxl")
        sheet_names = list(excel_file.sheet_names)
        total = len(sheet_names)

        used_names: Set[str] = set()
        output_files: List[str] = []
        sheet_outputs: List[Dict[str, str]] = []
        errors: List[str] = []

        for index, sheet_name in enumerate(sheet_names, 1):
            if progress_callback:
                progress_callback(index, total, sheet_name)

            safe_name = self._sanitize_sheet_name(sheet_name)
            safe_name = self._make_unique_name(safe_name, used_names)
            output_file = os.path.join(output_dir, f"{safe_name}.csv")

            try:
                df = excel_file.parse(sheet_name, dtype=str, na_filter=False)
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"{sheet_name}: {exc}")
                df = pd.DataFrame()

            try:
                df.to_csv(output_file, index=False, encoding=self.output_encoding)
                output_files.append(output_file)
                sheet_outputs.append({"sheet": sheet_name, "output_file": output_file})
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"{sheet_name}: {exc}")

        return {
            "input_file": input_file,
            "output_dir": output_dir,
            "total_sheets": total,
            "output_files": output_files,
            "sheet_outputs": sheet_outputs,
            "errors": errors,
            "success": len(errors) == 0,
        }

    @classmethod
    def _sanitize_sheet_name(cls, name: str) -> str:
        sanitized = cls.INVALID_CHARS_PATTERN.sub("_", name)
        sanitized = cls.CONTROL_CHARS_PATTERN.sub("_", sanitized)
        sanitized = sanitized.rstrip(" .")

        if sanitized in {"", ".", ".."}:
            sanitized = "Sheet"

        if sanitized.upper() in cls.RESERVED_NAMES:
            sanitized = f"{sanitized}_"

        return sanitized

    @staticmethod
    def _make_unique_name(name: str, used_names: Set[str]) -> str:
        if name not in used_names:
            used_names.add(name)
            return name

        counter = 1
        while True:
            candidate = f"{name}_{counter}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            counter += 1
