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
_BOM = b"\xef\xbb\xbf"
_PREVIEW_LINES = 5
_PREVIEW_CHARS = 200


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
    had_bom: bool = False


def _preview(text: str) -> str:
    """First 5 lines (split on LF only, endings kept), each clipped to 200 characters."""
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return "".join(_clip(line) for line in lines[:_PREVIEW_LINES])


def _clip(line: str) -> str:
    body = line.rstrip("\n")
    ending = line[len(body) :]
    if body.endswith("\r"):
        body, ending = body[:-1], "\r" + ending
    if len(body) > _PREVIEW_CHARS:
        body = body[:_PREVIEW_CHARS] + "…"
    return body + ending


def detect_encoding(data: bytes, forced: str | None = None) -> EncodingDecision:
    had_bom = data.startswith(_BOM)
    if had_bom and forced in LEGACY_ENCODINGS:
        # a BOM always wins: decoding it as GBK/cp932 corrupts the first field
        return EncodingDecision(
            "utf-8-sig", "文件带 UTF-8 BOM，已忽略手动指定的编码", had_bom=True
        )
    if forced == "utf-8" and had_bom:
        forced = "utf-8-sig"
    if forced:
        try:
            data.decode(forced)
        except (UnicodeDecodeError, LookupError) as e:
            raise EncodingError(f"无法按 {forced} 解码") from e
        return EncodingDecision(forced, None, had_bom=had_bom)
    if had_bom:
        return EncodingDecision("utf-8-sig", None, had_bom=True)
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
