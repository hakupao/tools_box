"""把 assets/icons/app_icon.svg 渲染成多尺寸的 assets/icons/favicon.ico。

用法（仓库根目录）：
    .venv\\Scripts\\python scripts\\build_icon.py [--svg 源文件] [--out 输出文件]

每个尺寸以 PNG 记录写入 ico。Qt 没有多尺寸 ico 的写入功能，所以文件头由本脚本自己写。
"""
from __future__ import annotations

import argparse
import logging
import os
import struct
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
SIZES: tuple[int, ...] = (16, 32, 48, 64, 128, 256)


def render_svg(svg_path: Path, size: int) -> QImage:
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise ValueError(f"无法读取 SVG：{svg_path}")
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def encode_png(image: QImage) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buf, "PNG"):
        raise RuntimeError("PNG 编码失败")
    buf.close()
    return bytes(data)


def build_ico(pngs: list[tuple[int, bytes]]) -> bytes:
    count = len(pngs)
    header = struct.pack("<HHH", 0, 1, count)
    entries = b""
    offset = 6 + 16 * count
    for size, png in pngs:
        # 256 在一字节宽高字段里写作 0
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    return header + entries + b"".join(png for _, png in pngs)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把 SVG 图标生成多尺寸 ico")
    parser.add_argument("--svg", default="assets/icons/app_icon.svg")
    parser.add_argument("--out", default="assets/icons/favicon.ico")
    args = parser.parse_args(argv)
    svg = ROOT / args.svg
    out = ROOT / args.out

    _app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    pngs = [(size, encode_png(render_svg(svg, size))) for size in SIZES]
    _atomic_write(out, build_ico(pngs))
    logger.info("已生成 %s（尺寸：%s）", out, ", ".join(map(str, SIZES)))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
