"""AWS Textract AnalyzeExpense extraction provider.

Uses ``boto3`` to call ``textract.analyze_expense()`` and maps the
Textract response into the application's ``ExtractionResult`` schema.

Requires the following environment variables:
    AWS_REGION
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY

Set ``EXTRACTION_PROVIDER=textract`` to enable.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

from app.core.config import Settings, get_settings
from app.extraction.base import (
    ExtractedField,
    ExtractedLineItem,
    ExtractedParty,
    ExtractionProvider,
    ExtractionResult,
)
from app.invoices.normalization import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_supplier_name,
    normalize_vat_number,
)
from app.invoices.validation import weighted_confidence

logger = logging.getLogger(__name__)

# Textract field type → our internal field name mapping
_HEADER_FIELD_MAP: dict[str, str] = {
    "INVOICE_RECEIPT_ID": "invoice_number",
    "INVOICE_RECEIPT_DATE": "invoice_date",
    "DUE_DATE": "due_date",
    "SUBTOTAL": "subtotal_amount",
    "TAX": "tax_amount",
    "TOTAL": "total_amount",
    "VENDOR_NAME": "supplier_name",
    "VENDOR_VAT_NUMBER": "supplier_vat_number",
    "VENDOR_ADDRESS": "supplier_address",
    "RECEIVER_NAME": "customer_name",
    "RECEIVER_ADDRESS": "customer_address",
    "PAYMENT_TERMS": "payment_terms",
    "ACCOUNT_NUMBER": "iban",
}

# Textract line-item field type → our internal line-item field name mapping
_LINE_ITEM_FIELD_MAP: dict[str, str] = {
    "ITEM": "description",
    "DESCRIPTION": "description",
    "QUANTITY": "quantity",
    "UNIT_PRICE": "unit_price",
    "PRICE": "total_amount",
    "PRODUCT_CODE": "product_code",
    "TAX": "tax_amount",
    "TAX_RATE": "tax_rate",
}


class TextractExtractionProvider(ExtractionProvider):
    """Invoice extraction using AWS Textract AnalyzeExpense API."""

    name = "textract"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _get_client(self):  # noqa: ANN201 (boto3 types are optional)
        import boto3

        return boto3.client(
            "textract",
            region_name=self._settings.AWS_REGION or "us-east-1",
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
        )

    def extract(self, content: bytes, filename: str, mime_type: str) -> ExtractionResult:
        client = self._get_client()

        response = client.analyze_expense(
            Document={"Bytes": content},
        )

        # Optionally store raw JSON for debugging
        raw_json = json.dumps(response, default=str)
        self._store_raw_result(filename, raw_json)

        return self._parse_response(response, raw_json)

    def _store_raw_result(self, filename: str, raw_json: str) -> None:
        """Best-effort storage of raw Textract output to the ocr-raw bucket."""
        try:
            from app.storage import get_storage_backend

            key = f"ocr-raw/{filename}.textract.json"
            get_storage_backend().save_bytes(key, raw_json.encode("utf-8"))
        except Exception as exc:
            logger.warning("Failed to store raw Textract result: %s", exc)

    def _parse_response(self, response: dict, raw_json: str) -> ExtractionResult:
        """Map the Textract AnalyzeExpense response → ExtractionResult."""
        warnings: list[dict[str, str]] = []
        header_fields: dict[str, dict] = {}
        line_items: list[ExtractedLineItem] = []

        expense_documents = response.get("ExpenseDocuments", [])
        if not expense_documents:
            warnings.append({
                "code": "ocr_provider_failed",
                "severity": "error",
                "message": "Textract returned no expense documents.",
            })
            return ExtractionResult(
                provider=self.name,
                fields={},
                warnings=warnings,
            )

        # Process only the first expense document (single-invoice upload)
        doc = expense_documents[0]

        # ── Header / summary fields ──────────────────────────────────
        for summary_field in doc.get("SummaryFields", []):
            field_type = (summary_field.get("Type") or {}).get("Text", "")
            mapped = _HEADER_FIELD_MAP.get(field_type)
            if not mapped:
                continue

            value_block = summary_field.get("ValueDetection") or {}
            raw_value = value_block.get("Text")
            confidence = _decimal_confidence(value_block.get("Confidence"))

            if mapped in header_fields:
                # Keep the higher-confidence value
                if confidence > header_fields[mapped]["confidence"]:
                    header_fields[mapped] = {
                        "raw_value": raw_value,
                        "confidence": confidence,
                    }
            else:
                header_fields[mapped] = {
                    "raw_value": raw_value,
                    "confidence": confidence,
                }

        # ── Line items ────────────────────────────────────────────────
        for li_group in doc.get("LineItemGroups", []):
            for li in li_group.get("LineItems", []):
                item_data: dict[str, object] = {}
                item_confidence = Decimal("0.0")
                count = 0
                for expense_field in li.get("LineItemExpenseFields", []):
                    field_type = (expense_field.get("Type") or {}).get("Text", "")
                    mapped = _LINE_ITEM_FIELD_MAP.get(field_type)
                    if not mapped:
                        continue
                    value_block = expense_field.get("ValueDetection") or {}
                    raw = value_block.get("Text")
                    conf = _decimal_confidence(value_block.get("Confidence"))
                    item_confidence += conf
                    count += 1
                    item_data[mapped] = raw

                avg_confidence = (item_confidence / count) if count else Decimal("0.0")

                line_items.append(ExtractedLineItem(
                    line_number=len(line_items) + 1,
                    description=str(item_data.get("description") or ""),
                    quantity=_to_decimal(item_data.get("quantity")),
                    unit_price=_to_decimal(item_data.get("unit_price")),
                    tax_rate=_to_decimal(item_data.get("tax_rate")),
                    tax_amount=_to_decimal(item_data.get("tax_amount")),
                    total_amount=_to_decimal(item_data.get("total_amount")),
                    confidence=avg_confidence,
                ))

        # ── Build normalized fields dict ──────────────────────────────
        fields: dict[str, ExtractedField] = {}
        values: dict[str, str | None] = {}

        for name, data in header_fields.items():
            raw = data["raw_value"]
            confidence = data["confidence"]
            normalized = _normalize_field(name, raw)
            values[name] = normalized
            fields[name] = ExtractedField(
                raw_value=raw,
                normalized_value=normalized,
                confidence=confidence,
                source=self.name,
            )

        # Detect currency from raw text / field values
        raw_text_blob = " ".join(
            str(d.get("raw_value", "")) for d in header_fields.values()
        )
        if "currency" not in fields:
            detected_currency = normalize_currency(raw_text_blob)
            if detected_currency:
                fields["currency"] = ExtractedField(
                    raw_value=detected_currency,
                    normalized_value=detected_currency,
                    confidence=Decimal("0.80"),
                    source=self.name,
                )
                values["currency"] = detected_currency

        # Compute overall confidence
        confidence_map = {name: field.confidence for name, field in fields.items()}
        overall = weighted_confidence(confidence_map)
        fields["overall"] = ExtractedField(
            raw_value=None,
            normalized_value=str(overall),
            confidence=overall,
            source=self.name,
        )

        # ── Build parties ─────────────────────────────────────────────
        supplier_name = values.get("supplier_name")
        supplier_vat = values.get("supplier_vat_number")
        supplier = ExtractedParty(
            name=normalize_supplier_name(supplier_name) if supplier_name else None,
            vat_number=normalize_vat_number(supplier_vat) if supplier_vat else None,
        )

        customer_name = values.get("customer_name")
        customer = ExtractedParty(name=customer_name) if customer_name else ExtractedParty()

        # ── Line-item warnings ────────────────────────────────────────
        if not line_items:
            warnings.append({
                "code": "line_items_not_extracted",
                "severity": "info",
                "message": "Line items were not extracted for this invoice.",
            })

        return ExtractionResult(
            provider=self.name,
            fields=fields,
            supplier=supplier,
            customer=customer,
            line_items=line_items,
            raw_text=raw_json[:20000],
            warnings=warnings,
        )


# ── Helpers ───────────────────────────────────────────────────────────


def _decimal_confidence(value: object) -> Decimal:
    """Convert a Textract confidence float (0-100) to 0-1 Decimal."""
    try:
        return (Decimal(str(value)) / Decimal("100")).quantize(Decimal("0.0001"))
    except (InvalidOperation, TypeError):
        return Decimal("0.0")


def _to_decimal(value: object) -> Decimal | None:
    """Parse a string amount into a Decimal, tolerating OCR noise."""
    if value is None:
        return None
    return normalize_amount(str(value))


def _normalize_field(name: str, raw: str | None) -> str | None:
    """Normalize a header field value based on field name."""
    if raw is None:
        return None

    if name in ("invoice_date", "due_date"):
        parsed = normalize_date(raw)
        return parsed.isoformat() if parsed else raw

    if name in ("subtotal_amount", "tax_amount", "total_amount"):
        amount = normalize_amount(raw)
        return f"{amount:.2f}" if amount is not None else raw

    if name == "supplier_vat_number":
        return normalize_vat_number(raw)

    if name == "supplier_name":
        return normalize_supplier_name(raw) or raw

    if name == "currency":
        return normalize_currency(raw) or raw

    return raw
