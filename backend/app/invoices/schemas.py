from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    role: str
    plan: str
    subscription_status: str


class MeOut(BaseModel):
    user: dict[str, str | None]
    organizations: list[OrganizationOut]
    active_organization_id: str | None


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = None


class WarningOut(BaseModel):
    code: str
    severity: str
    message: str


class PartyOut(BaseModel):
    name: str | None = None
    vat_number: str | None = None
    tax_id: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None


class LineItemOut(BaseModel):
    line_number: int | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    confidence: Decimal | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    status: str
    original_filename: str
    file_mime_type: str
    file_size_bytes: int
    page_count: int | None = None
    duplicate_of_invoice_id: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = None
    subtotal_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    iban: str | None = None
    payment_terms: str | None = None
    raw_text: str | None = None
    extraction_confidence: Decimal | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    supplier: PartyOut
    customer: PartyOut | None = None
    confidence: dict[str, Decimal]
    warnings: list[WarningOut]
    line_items: list[LineItemOut]
    file_preview_url: str | None = None


class InvoiceListOut(BaseModel):
    items: list[InvoiceOut]
    page: int
    page_size: int
    total: int


class InvoiceUploadOut(BaseModel):
    id: str
    status: str
    original_filename: str


class SupplierPatch(BaseModel):
    name: str | None = None
    vat_number: str | None = None
    tax_id: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None


class InvoicePatch(BaseModel):
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = None
    subtotal_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    iban: str | None = None
    payment_terms: str | None = None
    supplier: SupplierPatch | None = None


class ExportCreate(BaseModel):
    organization_id: str
    format: str = Field(pattern="^(csv|xlsx)$")
    status: str = "approved"
    from_date: date | None = Field(default=None, alias="from")
    to_date: date | None = Field(default=None, alias="to")


class ExportOut(BaseModel):
    id: str
    export_job_id: str
    status: str
    format: str
    row_count: int | None = None
    download_url: str | None = None


class SupplierOut(BaseModel):
    id: str
    name: str
    normalized_name: str | None = None
    vat_number: str | None = None
    tax_id: str | None = None
    iban: str | None = None
    default_expense_category: str | None = None
    invoice_count: int = 0
    total_amount: Decimal | None = None


class BillingSummaryOut(BaseModel):
    plan: str
    subscription_status: str
    invoices_used: int
    invoices_limit: int
    usage_period_start: date | None = None
    usage_period_end: date | None = None
    stripe_configured: bool
    available_plans: list[dict[str, Any]]
