from datetime import date
from decimal import Decimal

from app.invoices.normalization import normalize_amount, normalize_currency, normalize_date, normalize_vat_number
from app.invoices.validation import validate_invoice, weighted_confidence


def test_normalize_eu_and_us_amounts() -> None:
    assert normalize_amount("1 234,56 EUR") == Decimal("1234.56")
    assert normalize_amount("1,234.56") == Decimal("1234.56")
    assert normalize_amount("1234.5") == Decimal("1234.50")


def test_normalize_dates_currency_and_vat() -> None:
    assert normalize_date("23/06/2026") == date(2026, 6, 23)
    assert normalize_date("2026-06-23") == date(2026, 6, 23)
    assert normalize_currency("Total 1200,00 €") == "EUR"
    assert normalize_vat_number("FR 12 345 678 901") == "FR12345678901"


def test_validation_flags_missing_required_and_total_mismatch() -> None:
    warnings = validate_invoice(
        {
            "supplier_name": "",
            "invoice_number": None,
            "invoice_date": date(2026, 6, 23),
            "currency": "EUR",
            "subtotal_amount": Decimal("100.00"),
            "tax_amount": Decimal("20.00"),
            "total_amount": Decimal("125.00"),
        },
        today=date(2026, 6, 24),
    )
    codes = {warning.code for warning in warnings}
    assert "missing_supplier_name" in codes
    assert "missing_invoice_number" in codes
    assert "subtotal_tax_total_mismatch" in codes


def test_weighted_confidence() -> None:
    assert weighted_confidence(
        {
            "invoice_number": Decimal("1"),
            "supplier_name": Decimal("1"),
            "invoice_date": Decimal("1"),
            "total_amount": Decimal("1"),
            "tax_amount": Decimal("1"),
            "subtotal_amount": Decimal("1"),
            "currency": Decimal("1"),
        }
    ) == Decimal("1.0000")
