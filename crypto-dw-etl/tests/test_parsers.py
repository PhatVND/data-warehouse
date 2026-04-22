import os
import sys
import unittest
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "scripts"))

from parsers import parse_date, parse_number, parse_volume


class TestDataParsers(unittest.TestCase):
    SAMPLE_KLINES = [
        [
            "1713830400000",
            "66819.32000000",
            "67183.01000000",
            "65765.81000000",
            "66414.00000000",
            "22599.90004000",
        ],
        [
            "1713916800000",
            "66414.00000000",
            "67070.43000000",
            "63606.06000000",
            "64289.59000000",
            "33595.69637000",
        ],
        [
            "1714003200000",
            "64289.58000000",
            "65297.94000000",
            "62794.00000000",
            "64498.34000000",
            "31341.46338000",
        ],
        [
            "1714089600000",
            "64498.34000000",
            "64734.78000000",
            "63376.00000000",
            "63783.62000000",
            "20118.56082000",
        ],
        [
            "1714176000000",
            "63783.62000000",
            "64929.00000000",
            "62500.00000000",
            "64347.99000000",
            "22841.45790000",
        ],
    ]

    def test_parse_number_valid(self):
        self.assertEqual(parse_number("2,434.19"), 2434.19)
        self.assertEqual(parse_number(" -10.5 "), -10.5)

    def test_parse_number_invalid(self):
        self.assertIsNone(parse_number("—"))
        self.assertIsNone(parse_number("nan"))

    def test_parse_volume_suffixes(self):
        self.assertEqual(parse_volume("1.5M"), 1500000.0)
        self.assertEqual(parse_volume("900K"), 900000.0)

    def test_parse_volume_crypto_precision(self):
        self.assertEqual(parse_volume("0.01575800"), 0.015758)
        self.assertEqual(parse_volume("148976.11427815"), 148976.11427815)

    def test_parse_date_epoch_binance(self):
        self.assertEqual(parse_date("1499040000000"), date(2017, 7, 3))

    def test_parse_date_string_formats(self):
        self.assertEqual(parse_date("2024-12-01"), date(2024, 12, 1))
        self.assertEqual(parse_date("2024/12/01"), date(2024, 12, 1))
        self.assertEqual(parse_date("01/12/2024"), date(2024, 12, 1))
        self.assertEqual(parse_date("12/01/2024"), date(2024, 1, 12))

    def test_parse_date_invalid(self):
        self.assertIsNone(parse_date("not a date"))
        self.assertIsNone(parse_date(""))

    def test_parse_five_mock_binance_klines(self):
        parsed_dates = [parse_date(kline[0]) for kline in self.SAMPLE_KLINES]
        parsed_opens = [parse_number(kline[1]) for kline in self.SAMPLE_KLINES]
        parsed_closes = [parse_number(kline[4]) for kline in self.SAMPLE_KLINES]
        parsed_volumes = [parse_volume(kline[5]) for kline in self.SAMPLE_KLINES]

        self.assertEqual(len(parsed_dates), 5)
        self.assertEqual(parsed_dates[0], date(2024, 4, 23))
        self.assertEqual(parsed_dates[-1], date(2024, 4, 27))
        self.assertEqual(parsed_opens[0], 66819.32)
        self.assertEqual(parsed_closes[1], 64289.59)
        self.assertEqual(parsed_volumes[2], 31341.46338)
        self.assertTrue(
            all(value is not None for value in parsed_dates + parsed_opens + parsed_closes + parsed_volumes)
        )


if __name__ == "__main__":
    unittest.main()
