import re
from datetime import datetime, timezone

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None


def is_empty(v):
    """Lightweight empty-value check used across parser helpers."""
    if v is None:
        return True
    s = str(v).strip().lower()
    return s in ["", "-", "—", "nan", "null", "none"]


def parse_volume(v):
    """
    Parse volume values while preserving crypto precision.
    Supports numeric strings and K/M/B suffixes.
    """
    if is_empty(v):
        return None

    s = str(v).strip().replace(",", "").replace(" ", "")
    m = re.match(r"^(-?[\d\.]+)([KkMmBb]?)$", s)
    if m:
        num = float(m.group(1))
        suf = m.group(2).upper()
        if suf == "K":
            return num * 1_000.0
        if suf == "M":
            return num * 1_000_000.0
        if suf == "B":
            return num * 1_000_000_000.0
        return num

    try:
        return float(s)
    except Exception:
        return None


def parse_number(s):
    """Normalize a numeric string and convert it to float."""
    if is_empty(s):
        return None

    v = str(s).strip().replace(",", "").replace(" ", "")
    try:
        return float(v)
    except Exception:
        return None


def parse_date(s):
    """
    Parse dates from Binance epoch values or common string formats.
    ISO-style formats are prioritized so YYYY-MM-DD is preserved correctly.
    """
    if is_empty(s):
        return None

    v = str(s).strip()

    if v.isdigit():
        try:
            num = int(v)
            if num > 1e11:
                return datetime.fromtimestamp(num / 1000.0, tz=timezone.utc).date()
            return datetime.fromtimestamp(num, tz=timezone.utc).date()
        except Exception:
            pass

    iso_like_patterns = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in iso_like_patterns:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue

    common_patterns = [
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]
    for fmt in common_patterns:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue

    if date_parser is None:
        return None

    try:
        return date_parser.parse(v).date()
    except Exception:
        return None
