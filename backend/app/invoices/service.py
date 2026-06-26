from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import Principal
from app.db.bootstrap import ensure_user_and_default_org
from app.db.models import (
    AuditLog,
    ExportJob,
    ExtractionField,
    ExtractionJob,
    ExtractionWarning,
    Invoice,
    InvoiceLineItem,
    InvoiceParty,
    Organization,
    OrganizationMember,
    Supplier,
    UsageEvent,
    new_uuid,
    now_utc,
)
from app.extraction.base import ExtractionResult
from app.invoices.normalization import normalize_supplier_name, normalize_vat_number
from app.invoices.validation import ValidationWarning, validate_invoice
from app.storage import get_storage_backend

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/tif",
}

UPLOAD_ROLES = {"owner", "admin", "member"}
REVIEW_ROLES = {"owner", "admin", "member"}
EXPORT_ROLES = {"owner", "admin", "member"}
OWNER_ROLES = {"owner"}
PLAN_LIMITS = {"free": 20, "starter": 200, "pro": 1000, "business": 1000000}


def require_member(
    db: Session,
    principal: Principal,
    organization_id: str,
    roles: set[str] | None = None,
    settings: Settings | None = None,
) -> OrganizationMember:
    if settings is not None:
        ensure_user_and_default_org(db, principal, settings)
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == principal.user_id,
        )
        .one_or_none()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this organization.")
    if roles and member.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot perform this action.")
    return member


def require_invoice_access(
    db: Session,
    principal: Principal,
    invoice_id: str,
    roles: set[str] | None = None,
    settings: Settings | None = None,
) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    require_member(db, principal, invoice.organization_id, roles, settings)
    return invoice


def safe_filename(filename: str) -> str:
    name = Path(filename or "invoice").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name or "invoice"


def preview_token(invoice: Invoice, settings: Settings) -> str:
    message = f"{invoice.id}:{invoice.storage_key}:{invoice.document_hash or ''}:{settings.PREVIEW_TOKEN_SECRET}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:40]


def export_token(export_job: ExportJob, settings: Settings) -> str:
    message = f"{export_job.id}:{export_job.storage_key or ''}:{settings.PREVIEW_TOKEN_SECRET}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:40]


def validate_upload(file: UploadFile, content: bytes, settings: Settings) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG, PNG, and TIFF invoice files are supported.",
        )
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is larger than 25 MB.")


def count_pages(content: bytes, mime_type: str) -> int:
    if mime_type == "application/pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            return len(reader.pages)
        except Exception:
            return 1
    return 1


def assert_plan_limit(db: Session, organization: Organization) -> None:
    limit = PLAN_LIMITS.get(organization.plan, PLAN_LIMITS["free"])
    used = (
        db.query(func.coalesce(func.sum(UsageEvent.quantity), 0))
        .filter(
            UsageEvent.organization_id == organization.id,
            UsageEvent.event_type == "invoice_uploaded",
            UsageEvent.created_at >= datetime.combine(organization.usage_period_start, datetime.min.time(), tzinfo=UTC)
            if organization.usage_period_start
            else True,
        )
        .scalar()
    )
    if int(used or 0) >= limit:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Plan invoice limit has been reached.")


def create_invoice_upload(
    db: Session,
    principal: Principal,
    organization_id: str,
    file: UploadFile,
    content: bytes,
    settings: Settings,
) -> Invoice:
    member = require_member(db, principal, organization_id, UPLOAD_ROLES, settings)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    assert_plan_limit(db, organization)
    validate_upload(file, content, settings)
    page_count = count_pages(content, file.content_type or "application/octet-stream")
    if page_count > settings.MAX_UPLOAD_PAGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice exceeds the 50 page limit.")

    digest = hashlib.sha256(content).hexdigest()
    duplicate = (
        db.query(Invoice)
        .filter(Invoice.organization_id == organization_id, Invoice.document_hash == digest)
        .order_by(Invoice.created_at.asc())
        .first()
    )

    invoice_id = new_uuid()
    filename = safe_filename(file.filename or "invoice")
    storage_key = f"{organization_id}/originals/{invoice_id}/{filename}"
    get_storage_backend().save_bytes(storage_key, content)

    invoice = Invoice(
        id=invoice_id,
        organization_id=organization_id,
        uploaded_by_user_id=principal.user_id,
        status="uploaded",
        original_filename=filename,
        file_mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        storage_key=storage_key,
        page_count=page_count,
        document_hash=digest,
        duplicate_of_invoice_id=duplicate.id if duplicate else None,
    )
    db.add(invoice)
    db.flush()
    db.add(
        ExtractionJob(
            invoice_id=invoice.id,
            status="queued",
            provider=settings.EXTRACTION_PROVIDER,
            queued_at=now_utc(),
        )
    )
    db.add(UsageEvent(organization_id=organization_id, event_type="invoice_uploaded", quantity=1))
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=member.user_id,
            action="invoice.uploaded",
            target_type="invoice",
            target_id=invoice.id,
        )
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def apply_extraction_result(
    db: Session,
    invoice: Invoice,
    result: ExtractionResult,
    overwrite_existing: bool = True,
) -> None:
    field_values = {name: field.normalized_value for name, field in result.fields.items()}
    invoice.invoice_number = _choose(invoice.invoice_number, field_values.get("invoice_number"), overwrite_existing)
    invoice.invoice_date = _choose(invoice.invoice_date, _date_value(field_values.get("invoice_date")), overwrite_existing)
    invoice.due_date = _choose(invoice.due_date, _date_value(field_values.get("due_date")), overwrite_existing)
    invoice.currency = _choose(invoice.currency, field_values.get("currency"), overwrite_existing)
    invoice.subtotal_amount = _choose(
        invoice.subtotal_amount,
        _decimal_value(field_values.get("subtotal_amount")),
        overwrite_existing,
    )
    invoice.tax_amount = _choose(invoice.tax_amount, _decimal_value(field_values.get("tax_amount")), overwrite_existing)
    invoice.total_amount = _choose(invoice.total_amount, _decimal_value(field_values.get("total_amount")), overwrite_existing)
    invoice.iban = _choose(invoice.iban, field_values.get("iban"), overwrite_existing)
    invoice.payment_terms = _choose(invoice.payment_terms, field_values.get("payment_terms"), overwrite_existing)
    invoice.raw_text = result.raw_text or invoice.raw_text
    overall = result.fields.get("overall")
    invoice.extraction_confidence = overall.confidence if overall else invoice.extraction_confidence

    replace_party(
        db,
        invoice,
        "supplier",
        {
            "name": result.supplier.name,
            "vat_number": result.supplier.vat_number,
            "tax_id": result.supplier.tax_id,
            "address_line1": result.supplier.address_line1,
            "address_line2": result.supplier.address_line2,
            "postal_code": result.supplier.postal_code,
            "city": result.supplier.city,
            "country_code": result.supplier.country_code,
        },
    )
    if result.supplier.name:
        supplier = upsert_supplier(db, invoice.organization_id, result.supplier.name, result.supplier.vat_number, invoice.iban)
        invoice.supplier_id = supplier.id

    db.query(ExtractionField).filter(ExtractionField.invoice_id == invoice.id).delete()
    for name, field in result.fields.items():
        if name == "overall":
            continue
        db.add(
            ExtractionField(
                invoice_id=invoice.id,
                field_name=name,
                raw_value=field.raw_value,
                normalized_value=field.normalized_value,
                confidence=field.confidence,
                source=field.source,
                page_number=field.page_number,
                bbox_json=field.bbox_json,
            )
        )

    db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice.id).delete()
    for line_item in result.line_items:
        db.add(InvoiceLineItem(invoice_id=invoice.id, **line_item.__dict__))

    validation_warnings = validate_invoice(invoice_values(invoice))
    provider_warnings = [
        ValidationWarning(item["code"], item["severity"], item["message"])
        for item in result.warnings
        if {"code", "severity", "message"} <= set(item.keys())
    ]
    if invoice.duplicate_of_invoice_id:
        validation_warnings.append(
            ValidationWarning("duplicate_invoice_detected", "warning", "This file matches another invoice in the organization.")
        )
    replace_warnings(db, invoice.id, [*validation_warnings, *provider_warnings])


def apply_invoice_patch(db: Session, invoice: Invoice, payload: object) -> Invoice:
    update = payload.model_dump(exclude_unset=True)
    supplier_patch = update.pop("supplier", None)
    for key, value in update.items():
        setattr(invoice, key, value)
    if supplier_patch:
        replace_party(db, invoice, "supplier", supplier_patch)
        if supplier_patch.get("name"):
            supplier = upsert_supplier(
                db,
                invoice.organization_id,
                supplier_patch["name"],
                supplier_patch.get("vat_number"),
                invoice.iban,
            )
            invoice.supplier_id = supplier.id
    replace_warnings(db, invoice.id, validate_invoice(invoice_values(invoice)))
    db.commit()
    db.refresh(invoice)
    return invoice


def approve_invoice(db: Session, invoice: Invoice, principal: Principal) -> Invoice:
    if invoice.status != "needs_review":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only invoices needing review can be approved.")
    blocking = [
        warning
        for warning in validate_invoice(invoice_values(invoice))
        if warning.severity == "error"
    ]
    if blocking:
        replace_warnings(db, invoice.id, blocking)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Required invoice fields are missing.")
    invoice.status = "approved"
    invoice.reviewed_by_user_id = principal.user_id
    invoice.reviewed_at = now_utc()
    db.add(
        AuditLog(
            organization_id=invoice.organization_id,
            actor_user_id=principal.user_id,
            action="invoice.approved",
            target_type="invoice",
            target_id=invoice.id,
        )
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def archive_invoice(db: Session, invoice: Invoice, principal: Principal) -> Invoice:
    invoice.status = "archived"
    db.add(
        AuditLog(
            organization_id=invoice.organization_id,
            actor_user_id=principal.user_id,
            action="invoice.archived",
            target_type="invoice",
            target_id=invoice.id,
        )
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def hard_delete_invoice(db: Session, invoice: Invoice, principal: Principal) -> None:
    storage_key = invoice.storage_key
    organization_id = invoice.organization_id
    invoice_id = invoice.id
    db.delete(invoice)
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            action="invoice.deleted",
            target_type="invoice",
            target_id=invoice_id,
        )
    )
    db.commit()
    get_storage_backend().delete(storage_key)


def replace_party(db: Session, invoice: Invoice, party_type: str, values: dict[str, object]) -> None:
    party = (
        db.query(InvoiceParty)
        .filter(InvoiceParty.invoice_id == invoice.id, InvoiceParty.party_type == party_type)
        .one_or_none()
    )
    if party is None:
        party = InvoiceParty(invoice_id=invoice.id, party_type=party_type)
        db.add(party)
    for key, value in values.items():
        if hasattr(party, key):
            setattr(party, key, normalize_vat_number(value) if key == "vat_number" and isinstance(value, str) else value)


def upsert_supplier(
    db: Session,
    organization_id: str,
    name: str,
    vat_number: str | None,
    iban: str | None,
) -> Supplier:
    normalized = normalize_supplier_name(name) or name
    supplier_query = db.query(Supplier).filter(Supplier.organization_id == organization_id)
    normalized_vat = normalize_vat_number(vat_number)
    if normalized_vat:
        supplier_query = supplier_query.filter(
            or_(Supplier.normalized_name == normalized.lower(), Supplier.vat_number == normalized_vat)
        )
    else:
        supplier_query = supplier_query.filter(Supplier.normalized_name == normalized.lower())
    supplier = supplier_query.first()
    if supplier is None:
        supplier = Supplier(
            organization_id=organization_id,
            name=normalized,
            normalized_name=normalized.lower(),
            vat_number=normalized_vat,
            iban=iban,
        )
        db.add(supplier)
        db.flush()
    else:
        supplier.name = normalized
        supplier.normalized_name = normalized.lower()
        supplier.vat_number = normalized_vat or supplier.vat_number
        supplier.iban = iban or supplier.iban
    return supplier


def replace_warnings(db: Session, invoice_id: str, warnings: list[ValidationWarning]) -> None:
    db.query(ExtractionWarning).filter(ExtractionWarning.invoice_id == invoice_id).delete()
    seen: set[str] = set()
    for warning in warnings:
        key = f"{warning.code}:{warning.severity}"
        if key in seen:
            continue
        seen.add(key)
        db.add(
            ExtractionWarning(
                invoice_id=invoice_id,
                code=warning.code,
                severity=warning.severity,
                message=warning.message,
            )
        )


def invoice_values(invoice: Invoice) -> dict[str, object]:
    supplier = supplier_party(invoice)
    return {
        "supplier_name": supplier.name if supplier else None,
        "supplier_vat_number": supplier.vat_number if supplier else None,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "currency": invoice.currency,
        "subtotal_amount": invoice.subtotal_amount,
        "tax_amount": invoice.tax_amount,
        "total_amount": invoice.total_amount,
        "extraction_confidence": invoice.extraction_confidence,
    }


def supplier_party(invoice: Invoice) -> InvoiceParty | None:
    return next((party for party in invoice.parties if party.party_type == "supplier"), None)


def customer_party(invoice: Invoice) -> InvoiceParty | None:
    return next((party for party in invoice.parties if party.party_type == "customer"), None)


def invoice_to_dict(invoice: Invoice, settings: Settings, include_preview: bool = True) -> dict[str, object]:
    supplier = supplier_party(invoice)
    customer = customer_party(invoice)
    confidence = {
        field.field_name: Decimal(field.confidence or 0).quantize(Decimal("0.0001"))
        for field in invoice.extraction_fields
    }
    if invoice.extraction_confidence is not None:
        confidence["overall"] = Decimal(invoice.extraction_confidence).quantize(Decimal("0.0001"))
    file_preview_url = None
    if include_preview:
        file_preview_url = (
            f"{settings.BACKEND_BASE_URL}/api/invoices/{invoice.id}/file?preview_token={preview_token(invoice, settings)}"
        )
    return {
        "id": invoice.id,
        "organization_id": invoice.organization_id,
        "status": invoice.status,
        "original_filename": invoice.original_filename,
        "file_mime_type": invoice.file_mime_type,
        "file_size_bytes": invoice.file_size_bytes,
        "page_count": invoice.page_count,
        "duplicate_of_invoice_id": invoice.duplicate_of_invoice_id,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "currency": invoice.currency,
        "subtotal_amount": invoice.subtotal_amount,
        "tax_amount": invoice.tax_amount,
        "total_amount": invoice.total_amount,
        "iban": invoice.iban,
        "payment_terms": invoice.payment_terms,
        "raw_text": invoice.raw_text,
        "extraction_confidence": invoice.extraction_confidence,
        "reviewed_at": invoice.reviewed_at,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "supplier": party_to_dict(supplier),
        "customer": party_to_dict(customer) if customer else None,
        "confidence": confidence,
        "warnings": [{"code": warning.code, "severity": warning.severity, "message": warning.message} for warning in invoice.warnings],
        "line_items": [
            {
                "line_number": item.line_number,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_rate": item.tax_rate,
                "tax_amount": item.tax_amount,
                "total_amount": item.total_amount,
                "confidence": item.confidence,
            }
            for item in invoice.line_items
        ],
        "file_preview_url": file_preview_url,
    }


def party_to_dict(party: InvoiceParty | None) -> dict[str, object]:
    if party is None:
        return {
            "name": None,
            "vat_number": None,
            "tax_id": None,
            "address_line1": None,
            "address_line2": None,
            "postal_code": None,
            "city": None,
            "country_code": None,
        }
    return {
        "name": party.name,
        "vat_number": party.vat_number,
        "tax_id": party.tax_id,
        "address_line1": party.address_line1,
        "address_line2": party.address_line2,
        "postal_code": party.postal_code,
        "city": party.city,
        "country_code": party.country_code,
    }


def query_invoices(
    db: Session,
    organization_id: str,
    status_filter: str | None,
    search: str | None,
    from_date: object | None,
    to_date: object | None,
) -> object:
    query = db.query(Invoice).filter(Invoice.organization_id == organization_id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if search:
        search_like = f"%{search.lower()}%"
        query = query.outerjoin(InvoiceParty).filter(
            or_(
                func.lower(Invoice.original_filename).like(search_like),
                func.lower(Invoice.invoice_number).like(search_like),
                func.lower(InvoiceParty.name).like(search_like),
            )
        )
    if from_date:
        query = query.filter(Invoice.invoice_date >= from_date)
    if to_date:
        query = query.filter(Invoice.invoice_date <= to_date)
    return query.order_by(Invoice.created_at.desc())


def store_export_file(db: Session, export_job: ExportJob, filename: str, content: bytes) -> None:
    key = f"{export_job.organization_id}/exports/{export_job.id}/{filename}"
    get_storage_backend().save_bytes(key, content)
    export_job.storage_key = key
    export_job.status = "succeeded"
    db.commit()
    db.refresh(export_job)


def _decimal_value(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _date_value(value: object) -> object | None:
    if value in (None, ""):
        return None
    from app.invoices.normalization import normalize_date

    return normalize_date(value)


def _choose(current: object, extracted: object, overwrite_existing: bool) -> object:
    if extracted in (None, ""):
        return current
    if overwrite_existing or current in (None, ""):
        return extracted
    return current


def dumps_filter(value: dict[str, object]) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))
