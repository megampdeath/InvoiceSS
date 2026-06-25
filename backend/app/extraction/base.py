from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class ExtractedField:
    raw_value: str | None
    normalized_value: str | None
    confidence: Decimal
    source: str = "mock"
    page_number: int | None = 1
    bbox_json: str | None = None


@dataclass(frozen=True)
class ExtractedParty:
    name: str | None = None
    vat_number: str | None = None
    tax_id: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None


@dataclass(frozen=True)
class ExtractedLineItem:
    line_number: int | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    confidence: Decimal | None = None


@dataclass(frozen=True)
class ExtractionResult:
    provider: str
    fields: dict[str, ExtractedField]
    supplier: ExtractedParty = field(default_factory=ExtractedParty)
    customer: ExtractedParty = field(default_factory=ExtractedParty)
    line_items: list[ExtractedLineItem] = field(default_factory=list)
    raw_text: str | None = None
    warnings: list[dict[str, str]] = field(default_factory=list)


class ExtractionProvider:
    name = "base"

    def extract(self, content: bytes, filename: str, mime_type: str) -> ExtractionResult:
        raise NotImplementedError
