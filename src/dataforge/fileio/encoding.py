"""Text encoding detection (UTF-8 BOM, UTF-8, then cp932 / GBK)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from dataforge.core.errors import DataForgeError

logger = logging.getLogger(__name__)

LEGACY_ENCODINGS = ("cp932", "gbk")
ENCODING_LABELS = {
    "utf-8-sig": "UTF-8 (BOM)",
    "utf-8": "UTF-8",
    "cp932": "日文 (cp932)",
    "gbk": "中文 (GBK)",
}
_PREVIEW_LINES = 5


class EncodingError(DataForgeError):
    """The file encoding cannot be determined or decoded."""


class AmbiguousEncodingError(EncodingError):
    """Both cp932 and GBK decode the data; the user must choose."""

    def __init__(self, message: str, previews: dict[str, str]) -> None:
        super().__init__(message)
        self.previews = previews


@dataclass(frozen=True)
class EncodingDecision:
    encoding: str
    note: str | None


def _preview(text: str) -> str:
    return "".join(text.splitlines(keepends=True)[:_PREVIEW_LINES])


def detect_encoding(data: bytes, forced: str | None = None) -> EncodingDecision:
    if forced:
        try:
            data.decode(forced)
        except (UnicodeDecodeError, LookupError) as e:
            raise EncodingError(f"无法按 {forced} 解码") from e
        return EncodingDecision(forced, None)
    if data.startswith(b"\xef\xbb\xbf"):
        return EncodingDecision("utf-8-sig", None)
    try:
        data.decode("utf-8")
        return EncodingDecision("utf-8", None)
    except UnicodeDecodeError:
        pass
    decoded: dict[str, str] = {}
    for enc in LEGACY_ENCODINGS:
        try:
            decoded[enc] = data.decode(enc)
        except UnicodeDecodeError:
            continue
    if len(decoded) == 1:
        enc = next(iter(decoded))
        return EncodingDecision(enc, f"自动识别为 {ENCODING_LABELS[enc]}")
    if decoded:
        raise AmbiguousEncodingError(
            "无法确定编码（日文 cp932 / 中文 GBK 均可解码）",
            previews={enc: _preview(text) for enc, text in decoded.items()},
        )
    raise EncodingError("无法识别文件编码（已尝试 UTF-8、cp932、GBK）")
