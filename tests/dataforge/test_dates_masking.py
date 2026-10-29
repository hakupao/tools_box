import unittest

from dataforge.dates import (
    DateOutcome,
    SlashKind,
    SlashOrder,
    is_date_like,
    mask_date,
    slash_kind,
    to_iso8601,
)

SHIFTED = DateOutcome.SHIFTED
FILLED = DateOutcome.FILLED
UNPARSED = DateOutcome.UNPARSED
BLANK = DateOutcome.BLANK
DAY_FIRST = SlashOrder.DAY_FIRST
MONTH_FIRST = SlashOrder.MONTH_FIRST

CASES = [
    ("2024-06-15T13:30:00", None, "2022-06-15T13:30:00", SHIFTED),
    ("2024-06-15 13:30", None, "2022-06-15 13:30", SHIFTED),
    ("2024-06-15T13:30:00Z", None, "2022-06-15T13:30:00Z", SHIFTED),
    ("2024-06-15T13:30:00+09:00", None, "2022-06-15T13:30:00+09:00", SHIFTED),
    ("2024/6/5", None, "2022-06-05", SHIFTED),
    ("2024/06/05 08:00:00", None, "2022-06-05 08:00:00", SHIFTED),
    ("2024-05", None, "2022-05-01", FILLED),
    ("2024", None, "2022-01-01", FILLED),
    ("2024-02-29", None, "2022-02-28", SHIFTED),
    ("25/03/2024", None, "2022-03-25", SHIFTED),
    ("03/25/2024", None, "2022-03-25", SHIFTED),
    ("05/05/2024", None, "2022-05-05", SHIFTED),
    ("03/04/2024", DAY_FIRST, "2022-04-03", SHIFTED),
    ("03/04/2024", MONTH_FIRST, "2022-03-04", SHIFTED),
    ("03/04/2024", None, "03/04/2024", UNPARSED),
    ("25/03/2024", MONTH_FIRST, "2022-03-25", SHIFTED),
    ("2024-13-01", None, "2024-13-01", UNPARSED),
    ("2024-06-15T", None, "2024-06-15T", UNPARSED),
    ("abc", None, "abc", UNPARSED),
    ("", None, "", BLANK),
    ("NaN", None, "NaN", BLANK),
    ("0001-03-01", None, "0001-03-01", UNPARSED),
    ("2024-06-15 10:30 admitted 2024-06-10", None, "2024-06-15 10:30 admitted 2024-06-10", UNPARSED),
    ("2024-06-15T10:30 JOHN", None, "2024-06-15T10:30 JOHN", UNPARSED),
    ("2024-06-15abc", None, "2024-06-15abc", UNPARSED),
    ("2024-06-15Z", None, "2022-06-15Z", SHIFTED),
    ("2024-06-15T13:30:00.123+0900", None, "2022-06-15T13:30:00.123+0900", SHIFTED),
    ("9999-12-31", None, "9999-12-31", UNPARSED),
    ("31/31/2024", None, "31/31/2024", UNPARSED),
    ("  2024-05-01  ", None, "2022-05-01", SHIFTED),
    ("05/05/2024", DAY_FIRST, "2022-05-05", SHIFTED),
    # SDTM reduced precision: hour only, and an hour-only time zone offset
    ("2024-06-15T13", None, "2022-06-15T13", SHIFTED),
    ("2024-06-15T13+09", None, "2022-06-15T13+09", SHIFTED),
    ("2024-06-15T13:30-05", None, "2022-06-15T13:30-05", SHIFTED),
    ("2024-06-15+09", None, "2022-06-15+09", SHIFTED),
    ("2024-06-15T13+9", None, "2024-06-15T13+9", UNPARSED),
    ("2024-06-15T13:", None, "2024-06-15T13:", UNPARSED),
    # known limitation: a missing middle part is not understood
    ("2003---15", None, "2003---15", UNPARSED),
    # mixed separators are accepted
    ("2024-01/15", None, "2022-01-15", SHIFTED),
]


class DatesMaskingTests(unittest.TestCase):
    def test_mask_date_cases(self):
        for text, order, expected, outcome in CASES:
            with self.subTest(text=text, order=order):
                years = 1 if text == "9999-12-31" else -2
                self.assertEqual(mask_date(text, years, order), (expected, outcome))

    def test_unicode_digits_output_ascii(self):
        self.assertEqual(mask_date("２０２４-０１-１５", -2, None), ("2022-01-15", SHIFTED))

    def test_leap_forward(self):
        self.assertEqual(mask_date("2024-02-29", 4, None)[0], "2028-02-29")

    def test_slash_kind(self):
        self.assertIs(slash_kind("03/04/2024"), SlashKind.AMBIGUOUS)
        self.assertIs(slash_kind("25/03/2024"), SlashKind.DAY_FIRST_ONLY)
        self.assertIs(slash_kind("03/25/2024"), SlashKind.MONTH_FIRST_ONLY)
        self.assertIs(slash_kind("05/05/2024"), SlashKind.SAME)
        self.assertIs(slash_kind("31/31/2024"), SlashKind.INVALID)
        self.assertIs(slash_kind("2024-01-01"), SlashKind.NOT_SLASH)

    def test_is_date_like_counts_ambiguous(self):
        self.assertTrue(is_date_like("03/04/2024"))
        self.assertFalse(is_date_like("abc"))

    def test_to_iso8601_unchanged(self):
        self.assertEqual(to_iso8601("2024/2/30"), "2024-02")


if __name__ == "__main__":
    unittest.main()
