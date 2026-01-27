import csv
import os
from typing import Callable, Dict, Iterable, List, Optional

import pandas as pd


class FileFieldExtractor:
    """Extract field names from supported flat files and spreadsheets."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}

    def __init__(self, encodings: Optional[Iterable[str]] = None) -> None:
        self.encodings = list(encodings) if encodings else [
            "utf-8-sig",
            "utf-8",
            "gbk",
            "latin1",
        ]

    def extract_fields(
        self,
        folder_path: str,
        include_subfolders: bool = False,
        header_row: int = 1,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, object]:
        """
        Extract field names from supported files within a folder.

        Args:
            folder_path: The target directory containing files.
            include_subfolders: Whether to traverse subfolders recursively.
            header_row: 1-based row index used as header names.
            progress_callback: Optional callable to report progress. Receives
                the current index (1-based), total files count, and current file name.

        Returns:
            A dictionary containing the output CSV path, extraction details,
            processed file count, error list, and total extracted field count.

        Raises:
            ValueError: If the folder does not exist or contains no supported files.
        """
        if not os.path.isdir(folder_path):
            raise ValueError("请选择有效的文件夹路径。")

        if header_row < 1:
            raise ValueError("列名行号必须大于等于 1。")

        files = self._collect_files(folder_path, include_subfolders)
        if not files:
            raise ValueError("在该文件夹中未找到支持的文件类型。")

        details: Dict[str, List[str]] = {}
        errors: List[str] = []
        total_fields = 0
        total_files = len(files)

        for idx, file_path in enumerate(files, 1):
            if progress_callback:
                progress_callback(idx, total_files, os.path.basename(file_path))

            try:
                fields = self._extract_fields_from_file(file_path, header_row)
                details[file_path] = fields
                total_fields += len(fields)
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"{file_path}: {exc}")
                details[file_path] = []

        output_path = self._write_result_csv(folder_path, details)
        return {
            "output_file": output_path,
            "details": details,
            "processed_files": total_files,
            "errors": errors,
            "total_fields": total_fields,
        }

    def _collect_files(self, folder_path: str, include_subfolders: bool) -> List[str]:
        files: List[str] = []
        if include_subfolders:
            for root, _, filenames in os.walk(folder_path):
                for name in filenames:
                    if self._is_supported(name):
                        files.append(os.path.join(root, name))
        else:
            for name in os.listdir(folder_path):
                candidate = os.path.join(folder_path, name)
                if os.path.isfile(candidate) and self._is_supported(name):
                    files.append(candidate)
        files.sort()
        return files

    def _is_supported(self, filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in self.SUPPORTED_EXTENSIONS

    def _extract_fields_from_file(self, file_path: str, header_row: int) -> List[str]:
        extension = os.path.splitext(file_path)[1].lower()
        if extension == ".csv":
            return self._extract_from_csv(file_path, header_row)
        if extension in {".xlsx", ".xlsm"}:
            return self._extract_from_excel(file_path, header_row)
        raise ValueError(f"暂不支持的文件类型: {extension}")

    def _extract_from_csv(self, file_path: str, header_row: int) -> List[str]:
        last_exception: Optional[Exception] = None
        for encoding in self.encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    nrows=0,
                    encoding=encoding,
                    dtype=str,
                    on_bad_lines="skip",
                    header=header_row - 1,
                )
                return [str(col) for col in df.columns]
            except Exception as exc:  # pylint: disable=broad-except
                last_exception = exc
        raise ValueError(f"无法解析CSV文件（编码可能不受支持）: {last_exception}")

    def _extract_from_excel(self, file_path: str, header_row: int) -> List[str]:
        fields: List[str] = []
        try:
            excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"无法读取Excel文件: {exc}") from exc

        for sheet in excel_file.sheet_names:
            try:
                df = excel_file.parse(sheet, nrows=0, dtype=str, header=header_row - 1)
                fields.extend([f"{sheet}: {col}" for col in df.columns])
            except Exception as exc:  # pylint: disable=broad-except
                fields.append(f"{sheet}: 读取失败 ({exc})")
        return fields

    def _write_result_csv(self, folder_path: str, details: Dict[str, List[str]]) -> str:
        output_path = self._build_output_path(folder_path)
        with open(output_path, "w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["文件名", "字段名"])
            for absolute_path, fields in details.items():
                relative_name = os.path.relpath(absolute_path, folder_path)
                if fields:
                    for field in fields:
                        writer.writerow([relative_name, field])
                else:
                    writer.writerow([relative_name, ""])
        return output_path

    def _build_output_path(self, folder_path: str) -> str:
        base_name = "file_fields_summary.csv"
        output_path = os.path.join(folder_path, base_name)
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(
                folder_path, f"file_fields_summary_{counter}.csv"
            )
            counter += 1
        return output_path
