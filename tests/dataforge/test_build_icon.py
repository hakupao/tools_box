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


if __name__ == "__main__":
    unittest.main()
