"use client";

import { supabase } from "@/lib/supabase";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Organization = {
  id: string;
  name: string;
  slug: string;
  role: string;
  plan: string;
  subscription_status: string;
};

export type Me = {
  user: { id: string; email: string; name?: string | null };
  organizations: Organization[];
  active_organization_id: string | null;
};

export type Warning = { code: string; severity: "info" | "warning" | "error"; message: string };
export type Party = {
  name?: string | null;
  vat_number?: string | null;
  tax_id?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  postal_code?: string | null;
  city?: string | null;
  country_code?: string | null;
};

export type Invoice = {
  id: string;
  organization_id: string;
  status: string;
  original_filename: string;
  file_mime_type: string;
  file_size_bytes: number;
  page_count?: number | null;
  duplicate_of_invoice_id?: string | null;
  invoice_number?: string | null;
  invoice_date?: string | null;
  due_date?: string | null;
  currency?: string | null;
  subtotal_amount?: string | null;
  tax_amount?: string | null;
  total_amount?: string | null;
  iban?: string | null;
  payment_terms?: string | null;
  raw_text?: string | null;
  extraction_confidence?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
  supplier: Party;
  customer?: Party | null;
  confidence: Record<string, string>;
  warnings: Warning[];
  file_preview_url?: string | null;
};

export type InvoiceList = {
  items: Invoice[];
  page: number;
  page_size: number;
  total: number;
};

export type Supplier = {
  id: string;
  name: string;
  vat_number?: string | null;
  iban?: string | null;
  invoice_count: number;
  total_amount?: string | null;
};

type FetchOptions = RequestInit & { form?: boolean };

export function authToken(): string {
  if (typeof window === "undefined") {
    return "demo-token";
  }
  return localStorage.getItem("invoice_saas_token") || "demo-token";
}

/**
 * Try to refresh the Supabase session and return a fresh access token.
 * Falls back to the stored localStorage token if refresh fails.
 */
async function freshToken(): Promise<string> {
  if (typeof window === "undefined") return "demo-token";
  try {
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      localStorage.setItem("invoice_saas_token", data.session.access_token);
      return data.session.access_token;
    }
  } catch {
    // Supabase client unavailable — fall through
  }
  return authToken();
}

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const token = await freshToken();
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (!options.form && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });
  if (!response.ok) {
    // Automatic redirect to login on 401 (expired / invalid token)
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("invoice_saas_token");
      window.location.href = "/login";
      // Return a never-resolving promise so callers don't see an error flash
      return new Promise<T>(() => {});
    }
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function getMe() {
  return apiFetch<Me>("/api/me");
}

export async function getInvoices(organizationId: string, params: Record<string, string> = {}) {
  const search = new URLSearchParams({ organization_id: organizationId, ...params });
  return apiFetch<InvoiceList>(`/api/invoices?${search.toString()}`);
}

export async function getStatusCounts(organizationId: string) {
  return apiFetch<Record<string, number>>(`/api/invoices/status-counts?organization_id=${organizationId}`);
}

export async function uploadInvoice(organizationId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<{ id: string; status: string; original_filename: string }>(
    `/api/invoices?organization_id=${organizationId}`,
    { method: "POST", body: form, form: true }
  );
}

export async function getInvoice(id: string) {
  return apiFetch<Invoice>(`/api/invoices/${id}`);
}

export async function patchInvoice(id: string, payload: unknown) {
  return apiFetch<Invoice>(`/api/invoices/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function approveInvoice(id: string) {
  return apiFetch<Invoice>(`/api/invoices/${id}/approve`, { method: "POST" });
}

export async function reprocessInvoice(id: string) {
  return apiFetch<Invoice>(`/api/invoices/${id}/reprocess`, { method: "POST" });
}

export async function archiveInvoice(id: string) {
  return apiFetch<Invoice>(`/api/invoices/${id}/archive`, { method: "POST" });
}

export async function createExport(organizationId: string, format: "csv" | "xlsx") {
  return apiFetch<{ id: string; status: string; format: string; row_count: number; download_url?: string }>(
    "/api/exports",
    {
      method: "POST",
      body: JSON.stringify({ organization_id: organizationId, format, status: "approved" })
    }
  );
}

export async function getSuppliers(organizationId: string) {
  return apiFetch<Supplier[]>(`/api/suppliers?organization_id=${organizationId}`);
}

export async function getBillingSummary(organizationId: string) {
  return apiFetch<{
    plan: string;
    subscription_status: string;
    invoices_used: number;
    invoices_limit: number;
    usage_period_start?: string | null;
    usage_period_end?: string | null;
    stripe_configured: boolean;
    available_plans: Array<{ id: string; name: string; limit: number }>;
  }>(`/api/billing/summary?organization_id=${organizationId}`);
}

export async function createCheckoutSession(organizationId: string, priceId: string) {
  return apiFetch<{ checkout_url: string }>("/api/billing/create-checkout-session", {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId, price_id: priceId }),
  });
}

export async function createPortalSession(organizationId: string) {
  return apiFetch<{ portal_url: string }>("/api/billing/create-portal-session", {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId }),
  });
}
