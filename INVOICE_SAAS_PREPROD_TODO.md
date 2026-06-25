# Invoice SaaS Preprod Handoff

This file is a handoff for another coding AI. Be careful: do not undo the current Supabase setup unless explicitly asked. The app currently has a real Supabase connection working locally, but the project is not fully preprod-ready.

## Current State

Workspace:

```text
C:\Users\ashami\OneDrive - Expleo France\Desktop\Work\mail\invoice-saas
```

Real Supabase project currently used:

```text
qddypcxbqlgjsvxeytqy
```

Supabase project name:

```text
supabase-indigo-car
```

Important: a new Supabase project could not be created because the account hit the free active-project limit. The existing project above is being used as preprod for now.

## Already Done

- Repo linked to Supabase project `qddypcxbqlgjsvxeytqy`.
- Backend `.env` created at:

```text
backend\.env
```

- Frontend `.env.local` created at:

```text
frontend\.env.local
```

- Supabase app tables created.
- RLS policies applied.
- Private Storage buckets created:

```text
invoice-originals
invoice-exports
ocr-raw-results
```

- Frontend login now uses real Supabase email/password auth.
- Backend validates real Supabase access tokens through Supabase Auth `/auth/v1/user`.
- Backend Supabase Storage implementation exists.
- Dedicated Postgres backend role `invoice_app` was created.
- Verification passed:
  - Supabase Auth admin user creation.
  - Supabase password login.
  - Backend `/api/me` with real Supabase token.
  - Supabase Storage write/read/delete.
  - Backend tests.
  - Frontend build.

## Do Not Break These Files

Inspect before editing:

```text
backend\.env
frontend\.env.local
backend\app\core\security.py
backend\app\core\config.py
backend\app\storage\supabase_storage.py
backend\app\storage\__init__.py
frontend\app\login\page.tsx
frontend\lib\supabase.ts
supabase\rls.sql
supabase\storage-policies.sql
supabase\config.toml
```

Do not commit real secrets from `.env` or `.env.local`.

## What Is Missing

### 1. Real OCR Provider

Current extraction is still mock-based:

```env
EXTRACTION_PROVIDER=mock
```

Needed:

- Pick and wire a production OCR provider.
- Recommended from planning: AWS Textract first, unless another provider wins a real invoice bake-off.
- Add provider env vars.
- Test with real PDF/image invoices.
- Keep the provider behind the existing extraction abstraction.

Relevant files:

```text
backend\app\extraction\
backend\app\workers\process_invoice.py
```

### 2. Real Worker And Queue

Current local flow can process via FastAPI background task behavior. Preprod needs a real worker setup.

Needed:

- Redis service.
- Worker process running:

```powershell
python -m app.workers.process_invoice --once
```

or a loop/worker process appropriate for Render.

- Ensure uploads enqueue jobs reliably.
- Ensure worker reads from Supabase Storage and writes extraction results to Supabase Postgres.

### 3. Deployment To Render

Local works. Render/preprod is not done.

Needed Render services:

- Backend web service.
- Frontend web/static service.
- Redis.
- Worker/background service.

Copy required env vars from:

```text
backend\.env
frontend\.env.local
```

Do not expose service role keys to frontend.

### 4. Auth UX Hardening

Basic Supabase email/password login and signup works.

Still missing:

- Logout button.
- Protected-route redirect when no valid token exists.
- Session refresh using Supabase client.
- Password reset page.
- Decide whether email confirmation should be enabled for preprod.
- Better expired-token handling.

Relevant files:

```text
frontend\app\login\page.tsx
frontend\lib\api.ts
frontend\lib\supabase.ts
frontend\components\app-shell.tsx
```

### 5. Billing / Stripe

Stripe is not wired.

Needed:

- Stripe secret key.
- Stripe webhook secret.
- Price IDs.
- Checkout flow.
- Webhook handler.
- Subscription state updates in organizations table.
- Plan limit enforcement.

Relevant files:

```text
backend\app\billing\
backend\app\main.py
frontend\app\app\settings\page.tsx
```

### 6. Proper Migrations

Tables were created in Supabase from generated SQL/schema, not clean committed migrations.

Needed:

- Convert current schema into a reproducible migration.
- Keep Alembic and/or Supabase migrations consistent.
- Make setup reproducible for a fresh preprod/prod project.

Suggested path:

```powershell
cd invoice-saas
npx supabase db pull
```

Then inspect generated migration carefully. Do not blindly overwrite app schema.

### 7. Storage And Signed URL Review

Storage works through backend service-role access.

Still needed:

- Review file preview/download behavior.
- Add expiring signed URLs if desired.
- Confirm large PDF/image behavior.
- Confirm delete cleanup for invoice originals and exports.

Relevant files:

```text
backend\app\storage\supabase_storage.py
backend\app\invoices\routes.py
backend\app\invoices\service.py
```

### 8. End-To-End Browser Test

Programmatic verification passed. Full UI workflow still needs manual browser testing.

Test:

1. Open:

```text
http://127.0.0.1:3000/login
```

2. Sign up with email/password.
3. Confirm app redirects to invoices.
4. Upload sample invoice.
5. Confirm invoice gets processed.
6. Review invoice.
7. Approve invoice.
8. Export CSV/XLSX.
9. Download export.

### 9. Clean Dedicated Supabase Project

Current preprod uses existing project:

```text
supabase-indigo-car
```

Better final setup:

- Delete/pause/upgrade Supabase projects to free capacity.
- Create dedicated project:

```text
invoice-saas-preprod
```

- Re-run schema, RLS, storage setup.
- Regenerate env files.

## Useful Commands

Start backend:

```powershell
cd "C:\Users\ashami\OneDrive - Expleo France\Desktop\Work\mail\invoice-saas\backend"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start frontend:

```powershell
cd "C:\Users\ashami\OneDrive - Expleo France\Desktop\Work\mail\invoice-saas\frontend"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Run backend tests:

```powershell
cd "C:\Users\ashami\OneDrive - Expleo France\Desktop\Work\mail\invoice-saas\backend"
python -m pytest
```

Build frontend:

```powershell
cd "C:\Users\ashami\OneDrive - Expleo France\Desktop\Work\mail\invoice-saas\frontend"
npm run build
```

Check Supabase link:

```powershell
cd "C:\Users\ashami\OneDrive - Expleo France\Desktop\Work\mail\invoice-saas"
npx supabase projects list
```

Query linked Supabase DB:

```powershell
npx supabase db query --linked "select now();"
```

Apply RLS:

```powershell
npx supabase db query --linked --file .\supabase\rls.sql
```

Apply storage policies:

```powershell
npx supabase db query --linked --file .\supabase\storage-policies.sql
```

## Warnings For The Next AI

- Do not assume the DB password in `..\Supabase pass.txt` belongs to the current project. It did not work for the existing project.
- The backend uses a dedicated `invoice_app` role now.
- Do not put `SUPABASE_SERVICE_ROLE_KEY` in frontend env.
- Do not replace Supabase auth with demo-token again.
- Do not delete the unrelated existing `day_logs` table unless the user explicitly says so.
- If changing schema, check RLS policies because model IDs are strings, while `auth.uid()` is UUID and must be cast to text.
