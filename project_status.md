# Invoice SaaS — Current Status & Next Steps

## ✅ What's Already Done

| Area | Status |
|---|---|
| **Supabase Auth** | Working — real email/password login/signup |
| **Backend `.env`** | Configured with real Supabase credentials |
| **Frontend `.env.local`** | Configured with public Supabase keys |
| **DB Tables** | Created in Supabase Postgres |
| **RLS Policies** | Applied |
| **Storage Buckets** | `invoice-originals`, `invoice-exports`, `ocr-raw-results` (private) |
| **Backend token validation** | Real Supabase JWT via `/auth/v1/user` |
| **Supabase Storage backend** | Implemented in [supabase_storage.py](file:///C:/Users/ashami/OneDrive%20-%20Expleo%20France/Desktop/Work/mail/invoice-saas/backend/app/storage/supabase_storage.py) |
| **Frontend pages** | Login, invoices, suppliers, exports, settings shells exist |
| **Backend API** | FastAPI with invoices, billing, extraction, workers modules |
| **Dedicated DB role** | `invoice_app` created |
| **Backend tests** | Passing |
| **Frontend build** | Passing |

---

## 🔴 What's Missing (from PREPROD_TODO)

### Priority Order (recommended)

| # | Task | Complexity | Details |
|---|---|---|---|
| **1** | **Auth UX Hardening** | Medium | Logout button, protected-route redirect, session refresh, password reset page, expired-token handling |
| **2** | **Real Worker & Queue** | Medium | Redis service, worker process, reliable job enqueue, worker reads from Supabase Storage → writes extraction results to Postgres |
| **3** | **Real OCR Provider** | Medium-High | Wire a production OCR provider (AWS Textract recommended), add provider env vars, test with real PDFs, keep behind extraction abstraction |
| **4** | **Storage & Signed URL Review** | Low-Medium | File preview/download behavior, expiring signed URLs, large PDF handling, delete cleanup |
| **5** | **Proper Migrations** | Low-Medium | Convert current schema into reproducible Alembic/Supabase migrations |
| **6** | **Billing / Stripe** | High | Stripe keys, checkout flow, webhook handler, subscription state, plan limit enforcement |
| **7** | **Deployment to Render** | Medium | Backend, frontend, Redis, worker services on Render with proper env vars |
| **8** | **End-to-End Browser Test** | Low | Full UI workflow testing: signup → upload → process → review → approve → export |
| **9** | **Clean Supabase Project** | Low | Dedicated `invoice-saas-preprod` project when capacity allows |

---

## ⚠️ Critical Warnings

> [!CAUTION]
> - Do **NOT** undo the current Supabase setup
> - Do **NOT** put `SUPABASE_SERVICE_ROLE_KEY` in frontend env
> - Do **NOT** replace Supabase auth with demo-token
> - Do **NOT** delete the `day_logs` table unless explicitly asked
> - If changing schema, check RLS policies — `auth.uid()` is UUID and must be cast to text

## 🎯 Recommended Next Action

**Auth UX Hardening (#4 in PREPROD_TODO)** is the most impactful starting point because:
1. It's user-facing and blocks real testing
2. It doesn't require external services (no Redis, no Stripe, no OCR API keys)
3. It unblocks the end-to-end browser test

Key deliverables:
- Add **logout button** to the app shell
- Add **protected-route redirect** (redirect to `/login` when no valid token)
- Implement **session refresh** using Supabase client
- Wire up the **password reset page** (already has a route at `/reset-password`)
- Handle **expired tokens** gracefully
