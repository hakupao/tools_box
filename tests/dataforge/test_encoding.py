import unittest

from dataforge.fileio.encoding import (
    AmbiguousEncodingError,
    EncodingError,
    detect_encoding,
)

GBK_ONLY = "SUBJID,姓名\nA001,张伟\n".encode("gbk")
CP932_ONLY = "SUBJID,ｼﾒｲ\nA001,ﾔﾏﾀﾞ\n".encode("cp932")
AMBIGUOUS = "テスト医師\n".encode("cp932")
UNDECODABLE = b"A,\x81\n"


class DetectEncodingTests(unittest.TestCase):
    def test_bom(self):
        self.assertEqual(detect_encoding(b"\xef\xbb\xbfa,b\n").encoding, "utf-8-sig")

    def test_utf8_and_empty(self):
        self.assertEqual(detect_encoding("中文".encode("utf-8")).encoding, "utf-8")
        self.assertEqual(detect_encoding(b"").encoding, "utf-8")

    def test_gbk_only(self):
        d = detect_encoding(GBK_ONLY)
        self.assertEqual((d.encoding, d.note), ("gbk", "自动识别为 中文 (GBK)"))

    def test_cp932_only(self):
        self.assertEqual(detect_encoding(CP932_ONLY).encoding, "cp932")

    def test_ambiguous(self):
        with self.assertRaises(AmbiguousEncodingError) as cm:
            detect_encoding(AMBIGUOUS)
        self.assertEqual(set(cm.exception.previews), {"cp932", "gbk"})
        self.assertEqual(cm.exception.previews["cp932"], "テスト医師\n")

    def test_undecodable(self):
        with self.assertRaises(EncodingError) as cm:
            detect_encoding(UNDECODABLE)
        self.assertNotIsInstance(cm.exception, AmbiguousEncodingError)

    def test_forced(self):
        self.assertEqual(detect_encoding(AMBIGUOUS, forced="gbk").encoding, "gbk")
        with self.assertRaises(EncodingError):
            detect_encoding(UNDECODABLE, forced="utf-8")

    def test_preview_limited_to_5_lines(self):
        data = "".join("テスト医師\n" for _ in range(10)).encode("cp932")
        with self.assertRaises(AmbiguousEncodingError) as cm:
            detect_encoding(data)
        for text in cm.exception.previews.values():
            self.assertEqual(len(text.splitlines()), 5)

    def test_forced_utf8_with_bom_becomes_utf8_sig(self):
        self.assertEqual(
            detect_encoding(b"\xef\xbb\xbfa,b\n", forced="utf-8").encoding, "utf-8-sig"
        )

    def test_preview_splits_on_lf_only_and_clips_long_lines(self):
        long_line = "あ" * 300
        data = (long_line + "\r\n" + "x\x0cy\n").encode("cp932")
        with self.assertRaises(AmbiguousEncodingError) as cm:
            detect_encoding(data)
        lines = cm.exception.previews["cp932"].split("\n")
        self.assertEqual(lines[0], "あ" * 200 + "…\r")
        self.assertEqual(lines[1], "x\x0cy")

    def test_had_bom_flag(self):
        self.assertTrue(detect_encoding(b"\xef\xbb\xbfa").had_bom)
        self.assertFalse(detect_encoding(b"a").had_bom)
        self.assertFalse(detect_encoding(b"a", "utf-8-sig").had_bom)
        self.assertTrue(detect_encoding(b"\xef\xbb\xbfa", "utf-8-sig").had_bom)
        self.assertTrue(detect_encoding(b"\xef\xbb\xbfa", "utf-8").had_bom)

    def test_forced_legacy_encoding_on_bom_file_is_overridden(self):
        data = b"\xef\xbb\xbfid,name\n1,x\n"
        for forced in ("gbk", "cp932"):
            with self.subTest(forced=forced):
                d = detect_encoding(data, forced)
                self.assertEqual(d.encoding, "utf-8-sig")
                self.assertEqual(d.note, "文件带 UTF-8 BOM，已忽略手动指定的编码")
                self.assertTrue(d.had_bom)
                self.assertEqual(data.decode(d.encoding), "id,name\n1,x\n")
