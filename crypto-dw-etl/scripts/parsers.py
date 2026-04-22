import re
from datetime import datetime, timezone


def is_empty(v):
    """Replace pandas.isna() with a lightweight helper."""
    if v is None:
        return True
    s = str(v).strip().lower()
    return s in ["", "-", "—", "nan", "null", "none"]


def parse_volume(v):
    """
    Parse volume values for crypto data.
    Keep float precision instead of coercing to int.
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
    """Normalize numeric strings and convert to float."""
    if is_empty(s):
        return None

    v = str(s).strip().replace(",", "").replace(" ", "")
    try:
        return float(v)
    except Exception:
        return None


def parse_date(s):
    """
    Parse standard date strings and Binance epoch milliseconds.
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

    try:
        from dateutil import parser

        return parser.parse(v, dayfirst=True).date()
    except Exception:
        return None
