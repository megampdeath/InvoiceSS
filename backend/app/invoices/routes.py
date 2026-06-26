from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import Principal, get_current_principal, principal_from_authorization
from app.db.models import ExportJob, Invoice, OrganizationMember, Supplier, UsageEvent
from app.db.session import get_db
from app.invoices.exports import build_export
from app.invoices.schemas import ExportCreate, InvoiceListOut, InvoiceOut, InvoicePatch, InvoiceUploadOut, SupplierOut
from app.invoices.service import (
    EXPORT_ROLES,
    OWNER_ROLES,
    REVIEW_ROLES,
    UPLOAD_ROLES,
    archive_invoice,
    approve_invoice,
    create_invoice_upload,
    dumps_filter,
    export_token,
    hard_delete_invoice,
    invoice_to_dict,
    preview_token,
    query_invoices,
    require_invoice_access,
    require_member,
    store_export_file,
)
from app.storage import get_storage_backend
from app.workers.queue import enqueue_invoice_processing

router = APIRouter(prefix="/api", tags=["invoices"])


@router.post("/invoices", response_model=InvoiceUploadOut)
async def upload_invoice(
    organization_id: Annotated[str, Query()],
    file: Annotated[UploadFile, File()],
    background_tasks: BackgroundTasks,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    content = await file.read()
    invoice = create_invoice_upload(db, principal, organization_id, file, content, settings)
    background_tasks.add_task(enqueue_invoice_processing, invoice.id)
    return {"id": invoice.id, "status": invoice.status, "original_filename": invoice.original_filename}


@router.get("/invoices", response_model=InvoiceListOut)
def list_invoices(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    organization_id: Annotated[str, Query()],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    search: str | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, object]:
    require_member(db, principal, organization_id, None, settings)
    query = query_invoices(db, organization_id, status_filter, search, from_date, to_date)
    total = query.count()
    invoices = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [invoice_to_dict(invoice, settings, include_preview=False) for invoice in invoices],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/invoices/status-counts")
def invoice_status_counts(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    organization_id: Annotated[str, Query()],
) -> dict[str, int]:
    require_member(db, principal, organization_id, None, settings)
    rows = (
        db.query(Invoice.status, func.count(Invoice.id))
        .filter(Invoice.organization_id == organization_id)
        .group_by(Invoice.status)
        .all()
    )
    return {status_name: count for status_name, count in rows}


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def invoice_detail(
    invoice_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    invoice = require_invoice_access(db, principal, invoice_id, None, settings)
    return invoice_to_dict(invoice, settings)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: str,
    payload: InvoicePatch,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    invoice = require_invoice_access(db, principal, invoice_id, REVIEW_ROLES, settings)
    from app.invoices.service import apply_invoice_patch

    invoice = apply_invoice_patch(db, invoice, payload)
    return invoice_to_dict(invoice, settings)


@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceOut)
def approve_invoice_route(
    invoice_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    invoice = require_invoice_access(db, principal, invoice_id, REVIEW_ROLES, settings)
    invoice = approve_invoice(db, invoice, principal)
    return invoice_to_dict(invoice, settings)


@router.post("/invoices/{invoice_id}/reprocess", response_model=InvoiceOut)
def reprocess_invoice(
    invoice_id: str,
    background_tasks: BackgroundTasks,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    invoice = require_invoice_access(db, principal, invoice_id, REVIEW_ROLES, settings)
    from app.db.models import ExtractionJob, now_utc

    db.add(ExtractionJob(invoice_id=invoice.id, status="queued", provider=settings.EXTRACTION_PROVIDER, queued_at=now_utc()))
    invoice.status = "uploaded"
    db.commit()
    background_tasks.add_task(enqueue_invoice_processing, invoice.id, preserve_existing=True)
    db.refresh(invoice)
    return invoice_to_dict(invoice, settings)


@router.post("/invoices/{invoice_id}/archive", response_model=InvoiceOut)
def archive_invoice_route(
    invoice_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    invoice = require_invoice_access(db, principal, invoice_id, REVIEW_ROLES, settings)
    invoice = archive_invoice(db, invoice, principal)
    return invoice_to_dict(invoice, settings, include_preview=False)


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    invoice = require_invoice_access(db, principal, invoice_id, OWNER_ROLES, settings)
    hard_delete_invoice(db, invoice, principal)


@router.get("/invoices/{invoice_id}/file")
def invoice_file(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    preview_token_value: Annotated[str | None, Query(alias="preview_token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    if preview_token_value != preview_token(invoice, settings):
        principal = principal_from_authorization(authorization, settings)
        require_member(db, principal, invoice.organization_id, None, settings)
    storage = get_storage_backend()
    try:
        path = storage.local_path(invoice.storage_key)
        return FileResponse(path, media_type=invoice.file_mime_type, filename=invoice.original_filename)
    except FileNotFoundError:
        return Response(
            content=storage.read_bytes(invoice.storage_key),
            media_type=invoice.file_mime_type,
            headers={"Content-Disposition": f'inline; filename="{invoice.original_filename}"'},
        )


@router.post("/exports")
def create_export(
    payload: ExportCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    require_member(db, principal, payload.organization_id, EXPORT_ROLES, settings)
    query = query_invoices(db, payload.organization_id, payload.status, None, payload.from_date, payload.to_date)
    invoices = query.all()
    export_job = ExportJob(
        organization_id=payload.organization_id,
        created_by_user_id=principal.user_id,
        status="running",
        format=payload.format,
        filter_json=dumps_filter(payload.model_dump(by_alias=True)),
    )
    db.add(export_job)
    db.flush()
    filename, content, row_count = build_export(db, invoices, payload.format)
    export_job.row_count = row_count
    store_export_file(db, export_job, filename, content)
    return {
        "id": export_job.id,
        "export_job_id": export_job.id,
        "status": export_job.status,
        "format": export_job.format,
        "row_count": export_job.row_count,
        "download_url": f"{settings.BACKEND_BASE_URL}/api/exports/{export_job.id}/download?download_token={export_token(export_job, settings)}",
    }


@router.get("/exports/{export_job_id}")
def export_detail(
    export_job_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    export_job = db.get(ExportJob, export_job_id)
    if export_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found.")
    require_member(db, principal, export_job.organization_id, EXPORT_ROLES, settings)
    return {
        "id": export_job.id,
        "export_job_id": export_job.id,
        "status": export_job.status,
        "format": export_job.format,
        "row_count": export_job.row_count,
        "download_url": f"{settings.BACKEND_BASE_URL}/api/exports/{export_job.id}/download?download_token={export_token(export_job, settings)}"
        if export_job.storage_key
        else None,
    }


@router.get("/exports/{export_job_id}/download")
def download_export(
    export_job_id: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    download_token: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    export_job = db.get(ExportJob, export_job_id)
    if export_job is None or not export_job.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found.")
    if download_token != export_token(export_job, settings):
        principal = principal_from_authorization(authorization, settings)
        require_member(db, principal, export_job.organization_id, EXPORT_ROLES, settings)
    media_type = "text/csv" if export_job.format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = export_job.storage_key.rsplit("/", 1)[-1]
    storage = get_storage_backend()
    try:
        path = storage.local_path(export_job.storage_key)
        return FileResponse(path, media_type=media_type, filename=path.name)
    except FileNotFoundError:
        return Response(
            content=storage.read_bytes(export_job.storage_key),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    organization_id: Annotated[str, Query()],
) -> list[dict[str, object]]:
    require_member(db, principal, organization_id, None, settings)
    suppliers = db.query(Supplier).filter(Supplier.organization_id == organization_id).order_by(Supplier.name.asc()).all()
    results = []
    for supplier in suppliers:
        invoice_query = db.query(Invoice).filter(Invoice.supplier_id == supplier.id)
        results.append(
            {
                "id": supplier.id,
                "name": supplier.name,
                "normalized_name": supplier.normalized_name,
                "vat_number": supplier.vat_number,
                "tax_id": supplier.tax_id,
                "iban": supplier.iban,
                "default_expense_category": supplier.default_expense_category,
                "invoice_count": invoice_query.count(),
                "total_amount": invoice_query.with_entities(func.coalesce(func.sum(Invoice.total_amount), 0)).scalar(),
            }
        )
    return results


@router.get("/billing/summary")
def billing_summary(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    organization_id: Annotated[str, Query()],
) -> dict[str, object]:
    member = require_member(db, principal, organization_id, None, settings)
    organization = member.organization
    used = (
        db.query(func.coalesce(func.sum(UsageEvent.quantity), 0))
        .filter(UsageEvent.organization_id == organization_id, UsageEvent.event_type == "invoice_uploaded")
        .scalar()
    )
    limits = {"free": 20, "starter": 200, "pro": 1000, "business": 1000000}
    return {
        "plan": organization.plan,
        "subscription_status": organization.subscription_status,
        "invoices_used": int(used or 0),
        "invoices_limit": limits.get(organization.plan, 20),
        "usage_period_start": organization.usage_period_start,
        "usage_period_end": organization.usage_period_end,
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
        "available_plans": [
            {"id": "free", "name": "Free", "limit": 20},
            {"id": "starter", "name": "Starter", "limit": 200},
            {"id": "pro", "name": "Pro", "limit": 1000},
        ],
    }

