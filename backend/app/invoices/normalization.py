from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

DATE_PATTERNS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y")
CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP", "د.م.": "MAD"}
CURRENCY_CODES = {"EUR", "USD", "GBP", "MAD"}


def normalize_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    clean = str(value).strip()
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(clean, pattern).date()
        except ValueError:
            continue
    return None


def normalize_amount(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if isinstance(value, int):
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if isinstance(value, float):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    clean = str(value).strip()
    clean = re.sub(r"(EUR|USD|GBP|MAD|TTC|HT|TVA|VAT|TOTAL|€|\$|£)", "", clean, flags=re.IGNORECASE)
    clean = clean.replace("\u00a0", " ").replace(" ", "").replace("'", "")
    clean = re.sub(r"[^0-9,.\-]", "", clean)
    if not clean:
        return None

    if "," in clean and "." in clean:
        if clean.rfind(",") > clean.rfind("."):
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif "," in clean:
        parts = clean.split(",")
        if len(parts[-1]) in {1, 2}:
            clean = "".join(parts[:-1]) + "." + parts[-1]
        else:
            clean = clean.replace(",", "")
    elif clean.count(".") > 1:
        parts = clean.split(".")
        clean = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return Decimal(clean).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def normalize_currency(value: str | None) -> str | None:
    if not value:
        return None
    upper = value.strip().upper()
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in value:
            return code
    for code in CURRENCY_CODES:
        if code in upper:
            return code
    return None


def normalize_vat_number(value: str | None) -> str | None:
    if not value:
        return None
    clean = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    return clean or None


def normalize_supplier_name(value: str | None) -> str | None:
    if not value:
        return None
    clean = re.sub(r"\s+", " ", value).strip(" -:\t\r\n")
    if len(clean) < 2:
        return None
    return clean
