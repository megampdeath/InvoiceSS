from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.db.models import ExtractionJob, Invoice, now_utc
from app.db.session import SessionLocal, init_db
from app.extraction.providers import get_extraction_provider
from app.invoices.service import apply_extraction_result
from app.storage import get_storage_backend


def process_invoice_job(invoice_id: str, preserve_existing: bool = False) -> None:
    db = SessionLocal()
    try:
        _process_invoice_job(db, invoice_id, preserve_existing)
    finally:
        db.close()


def _process_invoice_job(db: Session, invoice_id: str, preserve_existing: bool) -> None:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        return

    job = (
        db.query(ExtractionJob)
        .filter(ExtractionJob.invoice_id == invoice_id, ExtractionJob.status.in_(["queued", "retrying"]))
        .order_by(ExtractionJob.queued_at.desc())
        .first()
    )
    if job is None:
        job = ExtractionJob(invoice_id=invoice.id, status="queued", provider="mock")
        db.add(job)
        db.flush()

    job.status = "running"
    job.started_at = now_utc()
    invoice.status = "processing"
    db.commit()

    try:
        content = get_storage_backend().read_bytes(invoice.storage_key)
        provider = get_extraction_provider()
        job.provider = provider.name
        result = provider.extract(content, invoice.original_filename, invoice.file_mime_type)
        apply_extraction_result(db, invoice, result, overwrite_existing=not preserve_existing)
        invoice.status = "needs_review"
        job.status = "succeeded"
        job.finished_at = now_utc()
        db.commit()
    except Exception as exc:
        invoice.status = "failed"
        job.status = "failed"
        job.error_code = exc.__class__.__name__
        job.error_message = str(exc)[:500]
        job.finished_at = now_utc()
        db.commit()


def run_pending_once() -> int:
    init_db()
    db = SessionLocal()
    try:
        jobs = db.query(ExtractionJob).filter(ExtractionJob.status == "queued").all()
        invoice_ids = [job.invoice_id for job in jobs]
    finally:
        db.close()
    for invoice_id in invoice_ids:
        process_invoice_job(invoice_id)
    return len(invoice_ids)


def run_loop(interval: int = 5) -> None:
    """Poll for queued jobs every *interval* seconds.

    Suitable for Render Background Worker when a dedicated Redis/RQ
    worker is not available.
    """
    import time

    init_db()
    print(f"starting poll loop (interval={interval}s)")
    while True:
        try:
            count = run_pending_once()
            if count:
                print(f"processed {count} queued job(s)")
        except Exception as exc:
            print(f"error during poll: {exc}")
        time.sleep(interval)


def run_rq_worker() -> None:
    """Start an ``rq.Worker`` that listens on the *invoices* queue."""
    from redis import Redis
    from rq import Worker

    from app.core.config import get_settings

    settings = get_settings()
    if not settings.REDIS_URL:
        raise SystemExit("REDIS_URL must be set to start the RQ worker.")

    init_db()
    conn = Redis.from_url(settings.REDIS_URL)
    worker = Worker(["invoices"], connection=conn)
    print("starting RQ worker on queue 'invoices'")
    worker.work()


def main() -> int:
    parser = argparse.ArgumentParser(description="Process queued invoice extraction jobs.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="Process all currently queued jobs and exit.")
    group.add_argument("--loop", nargs="?", type=int, const=5, metavar="SECONDS",
                       help="Poll for queued jobs every N seconds (default 5).")
    group.add_argument("--worker", action="store_true", help="Start an RQ worker on the 'invoices' queue.")
    args = parser.parse_args()

    if args.worker:
        run_rq_worker()
        return 0

    if args.loop is not None:
        run_loop(args.loop)
        return 0

    # Default to --once
    count = run_pending_once()
    print(f"processed {count} queued job(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

