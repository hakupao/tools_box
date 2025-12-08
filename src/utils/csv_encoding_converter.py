import os
from typing import Iterable, Optional, Tuple


class CsvEncodingConverter:
    """将CSV重新保存为指定编码（默认UTF-8 BOM）的转换器。"""

    def __init__(
        self,
        target_encoding: str = "utf-8-sig",
        fallback_encodings: Optional[Iterable[str]] = None,
    ) -> None:
        self.target_encoding = target_encoding
        self.fallback_encodings = list(fallback_encodings) if fallback_encodings else [
            "utf-8-sig",
            "utf-8",
            "gbk",
            "cp936",
            "latin1",
        ]

    def _read_with_fallback(self, file_path: str) -> str:
        """按序尝试不同编码读取文件，直到成功。"""
        last_error = None
        for encoding in self.fallback_encodings:
            try:
                with open(file_path, "r", encoding=encoding, newline="") as file:
                    return file.read()
            except UnicodeDecodeError as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "无法识别文件编码")

    def convert_file(self, input_file: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """将单个CSV文件转换为目标编码。

        Args:
            input_file: 输入文件路径。
            output_path: 输出目录，None时直接覆盖原文件。

        Returns:
            (是否成功, 错误信息)。
        """
        try:
            content = self._read_with_fallback(input_file)

            if output_path:
                os.makedirs(output_path, exist_ok=True)
                output_file = os.path.join(output_path, os.path.basename(input_file))
            else:
                output_file = input_file

            with open(output_file, "w", encoding=self.target_encoding, newline="") as file:
                file.write(content)

            return True, ""
        except Exception as e:
            return False, str(e)
