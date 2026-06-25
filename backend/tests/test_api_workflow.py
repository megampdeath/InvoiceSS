import os
import tempfile
from pathlib import Path

test_db = Path(tempfile.gettempdir()) / f"invoice_saas_test_{os.getpid()}.db"
if test_db.exists():
    test_db.unlink()

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db.as_posix()}"
os.environ["LOCAL_STORAGE_DIR"] = str(test_db.parent / f"invoice_saas_storage_{os.getpid()}")
os.environ["BACKEND_BASE_URL"] = "http://testserver"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE_INVOICE = """Supplier: Example SARL
TVA: FR12345678901
Facture: FA-2026-001
Date facture: 23/06/2026
Echeance: 23/07/2026
Total HT: 1000,00 EUR
TVA: 200,00 EUR
Total TTC: 1200,00 EUR
IBAN: FR7630006000011234567890189
"""


def test_upload_review_approve_and_export() -> None:
    with TestClient(app) as client:
        me = client.get("/api/me", headers={"Authorization": "Bearer demo-token"}).json()
        organization_id = me["active_organization_id"]

        upload = client.post(
            f"/api/invoices?organization_id={organization_id}",
            files={"file": ("invoice.pdf", SAMPLE_INVOICE.encode("utf-8"), "application/pdf")},
            headers={"Authorization": "Bearer demo-token"},
        )
        assert upload.status_code == 200
        invoice_id = upload.json()["id"]

        detail = client.get(f"/api/invoices/{invoice_id}", headers={"Authorization": "Bearer demo-token"})
        assert detail.status_code == 200
        invoice = detail.json()
        assert invoice["status"] == "needs_review"
        assert invoice["supplier"]["name"] == "Example SARL"
        assert invoice["invoice_number"] == "FA-2026-001"

        approve = client.post(f"/api/invoices/{invoice_id}/approve", headers={"Authorization": "Bearer demo-token"})
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        export = client.post(
            "/api/exports",
            json={"organization_id": organization_id, "format": "csv", "status": "approved"},
            headers={"Authorization": "Bearer demo-token"},
        )
        assert export.status_code == 200
        assert export.json()["row_count"] == 1
