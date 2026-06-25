"""Redis-backed job queue for invoice processing.

Uses ``rq`` when ``REDIS_URL`` is configured. Falls back to synchronous
in-process execution otherwise (useful for local dev without Redis).
"""

from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

QUEUE_NAME = "invoices"


def _get_redis():
    """Return a Redis connection or *None* when Redis is not configured."""
    settings = get_settings()
    if not settings.REDIS_URL:
        return None
    try:
        from redis import Redis

        conn = Redis.from_url(settings.REDIS_URL)
        conn.ping()
        return conn
    except Exception as exc:
        logger.warning("Redis unavailable (%s), falling back to sync processing.", exc)
        return None


def enqueue_invoice_processing(invoice_id: str, preserve_existing: bool = False) -> bool:
    """Enqueue an invoice processing job.

    Returns ``True`` if the job was queued in Redis, ``False`` if it fell
    back to synchronous (in-process) execution.
    """
    redis = _get_redis()
    if redis is not None:
        try:
            from rq import Queue

            queue = Queue(QUEUE_NAME, connection=redis)
            queue.enqueue(
                "app.workers.process_invoice.process_invoice_job",
                invoice_id,
                preserve_existing,
                job_timeout="10m",
            )
            logger.info("Queued invoice %s for processing via Redis/RQ.", invoice_id)
            return True
        except Exception as exc:
            logger.warning("Failed to enqueue via RQ (%s), falling back to sync.", exc)

    # Fallback: process synchronously (keeps dev without Redis working)
    from app.workers.process_invoice import process_invoice_job

    logger.info("Processing invoice %s synchronously (no Redis).", invoice_id)
    process_invoice_job(invoice_id, preserve_existing)
    return False
