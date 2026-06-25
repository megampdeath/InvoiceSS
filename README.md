# Invoice Extraction SaaS MVP

This project implements the first vertical slice from `../INVOICE_SAAS_PLANNING.md`:

```text
Upload invoice -> extract key fields -> review quickly -> approve -> export
```

The local build uses FastAPI, SQLAlchemy/SQLite, local private storage, mock extraction, and a Next.js app. The architecture seams for Supabase Auth, Supabase Storage, Redis/RQ workers, Stripe, and external OCR providers are present so the production services can be swapped in without rewriting the workflow.

## Run Locally

Backend:

```powershell
cd .\backend
python -m pip install -e ".[test]"
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd .\frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The development login uses `demo-token`; no Supabase project is required for the first local run.

## API Smoke Flow

```powershell
curl http://localhost:8000/api/health
```

1. Open `/login` and continue as the demo user.
2. Upload a PDF/image invoice.
3. Review the extracted fields.
4. Approve the invoice.
5. Export approved invoices to CSV or XLSX.

## Production Wiring

Before customer data is stored, configure:

- Supabase Auth and the JWT settings in `.env`.
- Supabase Postgres and private storage buckets.
- Render services for `backend`, `worker`, `frontend`, and Redis.
- Stripe price IDs and webhook secret.
- An external OCR provider selected by a sample-invoice bake-off.

## Useful Commands

Backend tests:

```powershell
cd .\backend
pytest
```

Frontend build:

```powershell
cd .\frontend
npm run build
```

Process queued jobs once:

```powershell
cd .\backend
python -m app.workers.process_invoice --once
```
