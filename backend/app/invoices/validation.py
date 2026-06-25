from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.invoices.normalization import normalize_vat_number


@dataclass(frozen=True)
class ValidationWarning:
    code: str
    severity: str
    message: str


def validate_invoice(values: dict[str, object], today: date | None = None) -> list[ValidationWarning]:
    today = today or date.today()
    warnings: list[ValidationWarning] = []

    required = {
        "supplier_name": "Supplier name is missing.",
        "invoice_number": "Invoice number is missing.",
        "invoice_date": "Invoice date is missing.",
        "currency": "Currency is missing.",
        "total_amount": "Total amount is missing.",
    }
    for field, message in required.items():
        if values.get(field) in (None, ""):
            warnings.append(ValidationWarning(f"missing_{field}", "error", message))

    subtotal = values.get("subtotal_amount")
    tax = values.get("tax_amount")
    total = values.get("total_amount")
    if isinstance(subtotal, Decimal) and isinstance(tax, Decimal) and isinstance(total, Decimal):
        if abs((subtotal + tax) - total) > Decimal("0.02"):
            warnings.append(
                ValidationWarning(
                    "subtotal_tax_total_mismatch",
                    "warning",
                    "Subtotal plus VAT does not match the total within 0.02.",
                )
            )

    invoice_date = values.get("invoice_date")
    due_date = values.get("due_date")
    if isinstance(invoice_date, date) and isinstance(due_date, date) and due_date < invoice_date:
        warnings.append(
            ValidationWarning("due_date_before_invoice_date", "warning", "Due date is before invoice date.")
        )

    if isinstance(invoice_date, date):
        if invoice_date > today + timedelta(days=1):
            warnings.append(ValidationWarning("invoice_date_in_future", "warning", "Invoice date is in the future."))
        if invoice_date < today - timedelta(days=3650):
            warnings.append(ValidationWarning("invoice_date_implausibly_old", "warning", "Invoice date is unusually old."))

    vat_number = values.get("supplier_vat_number")
    if isinstance(vat_number, str) and vat_number:
        normalized = normalize_vat_number(vat_number)
        if normalized and not _looks_like_vat(normalized):
            warnings.append(ValidationWarning("invalid_vat_format", "warning", "Supplier VAT number format looks invalid."))

    confidence = values.get("extraction_confidence")
    if isinstance(confidence, Decimal) and confidence < Decimal("0.60"):
        warnings.append(ValidationWarning("low_extraction_confidence", "warning", "Extraction confidence is low."))

    return warnings


def _looks_like_vat(value: str) -> bool:
    if len(value) < 8 or len(value) > 16:
        return False
    return value[:2].isalpha() and any(character.isdigit() for character in value[2:])


def weighted_confidence(confidence: dict[str, Decimal | float | int | None]) -> Decimal:
    weights = {
        "invoice_number": Decimal("0.15"),
        "supplier_name": Decimal("0.20"),
        "invoice_date": Decimal("0.15"),
        "total_amount": Decimal("0.25"),
        "tax_amount": Decimal("0.10"),
        "subtotal_amount": Decimal("0.10"),
        "currency": Decimal("0.05"),
    }
    total = Decimal("0")
    for field, weight in weights.items():
        value = confidence.get(field)
        if value is None:
            value_decimal = Decimal("0")
        else:
            value_decimal = Decimal(str(value))
        total += value_decimal * weight
    return total.quantize(Decimal("0.0001"))
