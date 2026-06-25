from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal

from app.extraction.base import ExtractedField, ExtractedParty, ExtractionProvider, ExtractionResult
from app.invoices.normalization import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_supplier_name,
    normalize_vat_number,
)
from app.invoices.validation import weighted_confidence


class MockExtractionProvider(ExtractionProvider):
    name = "mock"

    def extract(self, content: bytes, filename: str, mime_type: str) -> ExtractionResult:
        raw_text = _decode_invoice_text(content)
        today = date.today()

        supplier_name = _find_supplier(raw_text) or "Example SARL"
        supplier_vat = _find_first(
            raw_text,
            [
                r"(?:VAT|TVA|N[°o]\s*TVA|Tax ID)\s*[:#-]?\s*([A-Z]{2}\s?[A-Z0-9]{2}\s?\d{9,12})",
                r"\b([A-Z]{2}\s?[A-Z0-9]{2}\s?\d{9,12})\b",
            ],
        )
        invoice_number = _find_first(
            raw_text,
            [
                r"(?:Invoice|Facture|No\.?|N[°o])\s*(?:number|num[eé]ro)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,})",
                r"\b(FA[-\/]?\d{4,}[-\/]?\d*)\b",
            ],
        ) or f"DEMO-{today:%Y%m%d}"
        invoice_date = _find_labeled_date(raw_text, ["invoice date", "date facture", "date"])
        due_date = _find_labeled_date(raw_text, ["due date", "echeance", "échéance"])
        if not invoice_date:
            invoice_date = today
        if not due_date:
            due_date = invoice_date + timedelta(days=30)

        subtotal = _find_labeled_amount(raw_text, ["subtotal", "total ht", "montant ht", "net"])
        tax = _find_labeled_amount(raw_text, ["vat", "tva", "tax"])
        total = _find_labeled_amount(raw_text, ["total ttc", "grand total", "total due", "total"])
        if total is None:
            total = Decimal("1200.00")
        if subtotal is None and tax is not None:
            subtotal = total - tax
        if tax is None and subtotal is not None:
            tax = total - subtotal
        if subtotal is None:
            subtotal = Decimal("1000.00")
        if tax is None:
            tax = total - subtotal

        currency = _detect_currency(raw_text) or "EUR"
        iban = _find_first(raw_text, [r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b"])

        confidences = {
            "supplier_name": Decimal("0.72") if supplier_name == "Example SARL" else Decimal("0.88"),
            "invoice_number": Decimal("0.76") if invoice_number.startswith("DEMO") else Decimal("0.92"),
            "invoice_date": Decimal("0.82"),
            "due_date": Decimal("0.76"),
            "currency": Decimal("0.90"),
            "subtotal_amount": Decimal("0.82"),
            "tax_amount": Decimal("0.80"),
            "total_amount": Decimal("0.90"),
            "supplier_vat_number": Decimal("0.86") if supplier_vat else Decimal("0.0"),
            "iban": Decimal("0.82") if iban else Decimal("0.0"),
        }

        values = {
            "supplier_name": supplier_name,
            "supplier_vat_number": normalize_vat_number(supplier_vat),
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.isoformat(),
            "due_date": due_date.isoformat() if due_date else None,
            "currency": currency,
            "subtotal_amount": f"{subtotal:.2f}",
            "tax_amount": f"{tax:.2f}",
            "total_amount": f"{total:.2f}",
            "iban": iban,
            "payment_terms": "30 days" if due_date else None,
        }
        fields = {
            name: ExtractedField(
                raw_value=values[name],
                normalized_value=values[name],
                confidence=confidences.get(name, Decimal("0.75")),
                source=self.name,
            )
            for name in values
        }
        fields["overall"] = ExtractedField(
            raw_value=None,
            normalized_value=str(weighted_confidence(confidences)),
            confidence=weighted_confidence(confidences),
            source=self.name,
        )

        return ExtractionResult(
            provider=self.name,
            fields=fields,
            supplier=ExtractedParty(name=supplier_name, vat_number=normalize_vat_number(supplier_vat)),
            raw_text=raw_text[:20000] if raw_text else None,
            warnings=[
                {
                    "code": "line_items_not_extracted",
                    "severity": "info",
                    "message": "Line items were not extracted for this invoice.",
                }
            ],
        )


def _decode_invoice_text(content: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            printable_ratio = sum(character.isprintable() or character.isspace() for character in text) / max(len(text), 1)
            if printable_ratio > 0.75:
                return text
        except UnicodeDecodeError:
            continue
    return ""


def _find_first(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def _find_supplier(text: str) -> str | None:
    labeled = _find_first(text, [r"(?:Supplier|Vendor|Fournisseur)\s*[:#-]?\s*(.+)"])
    if labeled:
        return normalize_supplier_name(labeled)
    for line in text.splitlines()[:8]:
        clean = normalize_supplier_name(line)
        if clean and not re.search(r"(invoice|facture|date|total|vat|tva)", clean, flags=re.IGNORECASE):
            return clean
    return None


def _find_labeled_date(text: str, labels: list[str]) -> date | None:
    date_pattern = r"(\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})"
    for label in labels:
        match = re.search(rf"{re.escape(label)}\s*[:#-]?\s*{date_pattern}", text, flags=re.IGNORECASE)
        if match:
            parsed = normalize_date(match.group(1))
            if parsed:
                return parsed
    first = re.search(date_pattern, text)
    return normalize_date(first.group(1)) if first else None


def _find_labeled_amount(text: str, labels: list[str]) -> Decimal | None:
    amount_pattern = r"(-?\d[\d\s\u00a0'.,]*\d|\d)"
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:#-]?\s*(?:EUR|USD|GBP|MAD|€|\$|£)?\s*{amount_pattern}"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            parsed = normalize_amount(match.group(1))
            if parsed is not None:
                return parsed
    return None


def _detect_currency(text: str) -> str | None:
    return normalize_currency(text)
