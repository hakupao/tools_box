from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QIcon

from tests.dataforge.qt_helpers import qapp

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_icon", ROOT / "scripts" / "build_icon.py")
build_icon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_icon)

TEST_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
    '<rect x="32" y="32" width="192" height="192" fill="#ff0000"/></svg>'
)


class BuildIconTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.svg = self.tmp / "t.svg"
        self.svg.write_text(TEST_SVG, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_render_transparent_corners(self) -> None:
        for size in build_icon.SIZES:
            image = build_icon.render_svg(self.svg, size)
            self.assertEqual((image.width(), image.height()), (size, size))
            self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
            center = image.pixelColor(size // 2, size // 2)
            self.assertEqual(center.alpha(), 255)
            self.assertGreater(center.red(), 200)

    def test_header_layout(self) -> None:
        data = build_icon.build_ico([(16, b"A" * 10), (256, b"B" * 20)])
        self.assertEqual(struct.unpack_from("<HHH", data, 0), (0, 1, 2))
        w, h, _, _, planes, bpp, length, offset = struct.unpack_from("<BBBBHHII", data, 6)
        self.assertEqual((w, h, planes, bpp, length, offset), (16, 16, 1, 32, 10, 38))
        w, h, _, _, _, _, length, offset = struct.unpack_from("<BBBBHHII", data, 22)
        self.assertEqual((w, h, length, offset), (0, 0, 20, 48))
        self.assertEqual(data[38:48], b"A" * 10)
        self.assertEqual(data[48:68], b"B" * 20)

    def test_qt_reads_back_all_sizes(self) -> None:
        out = self.tmp / "x.ico"
        self.assertEqual(build_icon.main(["--svg", str(self.svg), "--out", str(out)]), 0)
        sizes = {s.width() for s in QIcon(str(out)).availableSizes()}
        self.assertEqual(sizes, set(build_icon.SIZES))


class SmallSvgTests(unittest.TestCase):
    def test_small_svg_used_for_small_sizes(self) -> None:
        qapp()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            big = tmp / "big.svg"
            small = tmp / "small.svg"
            big.write_text(TEST_SVG, encoding="utf-8")
            small.write_text(TEST_SVG.replace("#ff0000", "#0000ff"), encoding="utf-8")
            out = tmp / "x.ico"
            argv = ["--svg", str(big), "--svg-small", str(small), "--out", str(out)]
            self.assertEqual(build_icon.main(argv), 0)
            icon = QIcon(str(out))
            for size in build_icon.SIZES:
                color = icon.pixmap(size, size).toImage().pixelColor(size // 2, size // 2)
                if size in build_icon.SMALL_SIZES:
                    self.assertGreater(color.blue(), 200, size)
                else:
                    self.assertGreater(color.red(), 200, size)


class CommittedIconTests(unittest.TestCase):
    FAVICON = ROOT / "assets" / "icons" / "favicon.ico"
    SVG = ROOT / "assets" / "icons" / "app_icon.svg"
    SMALL_SVG = ROOT / "assets" / "icons" / "app_icon_small.svg"

    def setUp(self) -> None:
        qapp()

    def _favicon_image(self, size: int):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage

        image = QIcon(str(self.FAVICON)).pixmap(QSize(size, size)).toImage()
        return image.convertToFormat(QImage.Format.Format_ARGB32)

    def test_favicon_corners_transparent(self) -> None:
        sizes = {s.width() for s in QIcon(str(self.FAVICON)).availableSizes()}
        self.assertEqual(sizes, set(build_icon.SIZES))
        for size in build_icon.SIZES:
            image = self._favicon_image(size)
            self.assertEqual(image.width(), size)
            last = size - 1
            for x, y in ((0, 0), (last, 0), (0, last), (last, last)):
                self.assertEqual(image.pixelColor(x, y).alpha(), 0, f"{size}px corner {x},{y}")

    def test_favicon_matches_svg(self) -> None:
        from PySide6.QtGui import QImage

        for size in build_icon.SIZES:
            svg = self.SMALL_SVG if size in build_icon.SMALL_SIZES else self.SVG
            want = build_icon.render_svg(svg, size).convertToFormat(QImage.Format.Format_ARGB32)
            got = self._favicon_image(size)
            worst = 0
            for y in range(size):
                for x in range(size):
                    a, b = want.pixelColor(x, y), got.pixelColor(x, y)
                    worst = max(
                        worst,
                        abs(a.red() - b.red()),
                        abs(a.green() - b.green()),
                        abs(a.blue() - b.blue()),
                        abs(a.alpha() - b.alpha()),
                    )
            self.assertLessEqual(worst, 8, f"{size}px differs from app_icon.svg; rerun scripts/build_icon.py")


if __name__ == "__main__":
    unittest.main()
