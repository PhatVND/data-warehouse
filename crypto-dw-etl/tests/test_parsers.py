import unittest
from datetime import date
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "scripts"))

from parsers import parse_number, parse_date, parse_volume


class TestDataParsers(unittest.TestCase):
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
        self.assertEqual(parse_date("2024-12-01"), date(2024, 1, 12))
        self.assertEqual(parse_date("01/12/2024"), date(2024, 12, 1))

    def test_parse_date_invalid(self):
        self.assertIsNone(parse_date("not a date"))
        self.assertIsNone(parse_date(""))


if __name__ == "__main__":
    unittest.main()
