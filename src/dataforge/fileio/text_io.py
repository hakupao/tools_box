"""Text reading and CSV/text writing with the project's encoding conventions."""
from __future__ import annotations

import csv
import logging
from collections.abc import Iterable, Sequence
from pathlib import Path

from dataforge.fileio.atomic import atomic_path
from dataforge.fileio.encoding import EncodingDecision, detect_encoding

logger = logging.getLogger(__name__)


def read_text(path: Path, encoding: str | None = None) -> tuple[str, EncodingDecision]:
    """Read ``path`` as text, keeping line endings exactly as stored."""
    data = path.read_bytes()
    decision = detect_encoding(data, encoding)
    logger.info(
        "%s: 编码 %s（%s）", path.name, decision.encoding, "手动指定" if encoding else "自动识别"
    )
    return data.decode(decision.encoding), decision


def write_csv_rows(
    rows: Iterable[Sequence[str]], path: Path, *, delimiter: str = ","
) -> None:
    with atomic_path(path) as tmp:
        # explicit BOM: utf-8-sig emits nothing for an empty file
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write("\ufeff")
            csv.writer(f, delimiter=delimiter, lineterminator="\r\n").writerows(rows)


def write_text(text: str, path: Path) -> None:
    with atomic_path(path) as tmp:
        # explicit BOM: utf-8-sig may emit nothing for an empty file
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write("\ufeff")
            f.write(text)
