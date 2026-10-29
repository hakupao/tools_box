"""Full-width to half-width conversion for Excel workbooks."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.cell.rich_text import CellRichText, TextBlock

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.fileio.paths import plan_output

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")

_FULL_START, _FULL_END = 0xFF01, 0xFF5E
_OFFSET = 0xFEE0
_TABLE = {cp: cp - _OFFSET for cp in range(_FULL_START, _FULL_END + 1)}
_TABLE[0x3000] = 0x20


@dataclass
class WidthOptions:
    output_dir: Path | None = None
    overwrite_source: bool = False


def to_halfwidth(text: str) -> str:
    """U+FF01-U+FF5E -> U+0021-U+007E and U+3000 -> U+0020; everything else unchanged."""
    return text.translate(_TABLE)


def _convert_workbook(path: Path) -> tuple[object, int]:
    keep_vba = path.suffix.lower() == ".xlsm"
    wb = load_workbook(path, keep_vba=keep_vba, rich_text=True)
    changed = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell) or cell.data_type != "s":
                    continue
                value = cell.value
                if isinstance(value, CellRichText):
                    runs = []
                    run_changed = False
                    for part in value:
                        if isinstance(part, TextBlock):
                            text = to_halfwidth(part.text)
                            run_changed |= text != part.text
                            runs.append(TextBlock(part.font, text))
                        else:
                            text = to_halfwidth(str(part))
                            run_changed |= text != part
                            runs.append(text)
                    if run_changed:
                        cell.value = CellRichText(*runs)
                        changed += 1
                    continue
                if not isinstance(value, str):
                    continue
                converted = to_halfwidth(value)
                if converted != value:
                    cell.value = converted
                    changed += 1
    return wb, changed


def run(
    files: list[Path],
    options: WidthOptions,
    progress: ProgressFn,
    cancel: CancelToken,
) -> Result:
    if not files:
        raise DataForgeError("请先选择要转换的 Excel 文件")
    result = Result()
    total = len(files)
    for index, src in enumerate(files):
        progress(index, total, src.name)
        cancel.raise_if_cancelled()
        tmp: Path | None = None
        try:
            wb, changed = _convert_workbook(src)
            if changed == 0:
                result.warn(src, "未发现需要转换的全角字符，未生成文件")
                continue
            target = plan_output(
                src,
                new_name=f"{src.stem}_halfwidth{src.suffix}",
                output_dir=options.output_dir,
                overwrite_source=options.overwrite_source,
            )
            tmp = target.parent / f".{target.stem}.{os.getpid()}.tmp{target.suffix}"
            wb.save(tmp)
            os.replace(tmp, target)
            tmp = None
        except PermissionError:
            logger.warning("Cannot write output for %s", src, exc_info=True)
            result.fail(src, "无法写入输出文件（可能已在 Excel 中打开）")
            continue
        except Exception as e:  # noqa: BLE001 - per-file isolation
            logger.exception("Width conversion failed for %s", src)
            result.fail(src, f"转换失败：{e}")
            continue
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
        result.add_output(target)
        result.count("files")
        result.count("cells_changed", changed)
    progress(total, total, "")
    return result
