"use client";

import type { Invoice } from "@/lib/api";
import { approveInvoice, archiveInvoice, patchInvoice, reprocessInvoice } from "@/lib/api";
import { percent } from "@/lib/formatting";
import { Archive, CheckCircle2, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { StatusBadge } from "./status-badge";

type FormState = {
  supplier_name: string;
  supplier_vat_number: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  currency: string;
  subtotal_amount: string;
  tax_amount: string;
  total_amount: string;
  iban: string;
  payment_terms: string;
};

export function InvoiceReviewForm({ invoice, onChange }: { invoice: Invoice; onChange: (invoice: Invoice) => void }) {
  const [form, setForm] = useState<FormState>(toForm(invoice));
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setForm(toForm(invoice)), [invoice]);

  function setField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function run(label: string, task: () => Promise<Invoice>) {
    setBusy(label);
    setError(null);
    try {
      onChange(await task());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status={invoice.status} />
            <span className="text-xs font-semibold text-slate-500">Confidence {percent(invoice.extraction_confidence)}</span>
          </div>
          <h1 className="mt-2 text-lg font-bold text-ink">{invoice.original_filename}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            title="Reprocess"
            className="secondary-button"
            disabled={Boolean(busy)}
            onClick={() => void run("reprocess", () => reprocessInvoice(invoice.id))}
          >
            <RefreshCw size={16} />
            Reprocess
          </button>
          <button
            title="Archive"
            className="secondary-button"
            disabled={Boolean(busy)}
            onClick={() => void run("archive", () => archiveInvoice(invoice.id))}
          >
            <Archive size={16} />
            Archive
          </button>
        </div>
      </div>

      {invoice.warnings.length > 0 && (
        <div className="space-y-2 border-b border-line bg-amber-50 px-4 py-3">
          {invoice.warnings.map((warning) => (
            <div key={`${warning.code}-${warning.severity}`} className="text-sm text-amber-900">
              <span className="font-semibold">{warning.code}</span>: {warning.message}
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-4 p-4 sm:grid-cols-2">
        <Field label="Supplier" value={form.supplier_name} onChange={(value) => setField("supplier_name", value)} />
        <Field label="Supplier VAT" value={form.supplier_vat_number} onChange={(value) => setField("supplier_vat_number", value)} />
        <Field label="Invoice number" value={form.invoice_number} onChange={(value) => setField("invoice_number", value)} />
        <Field label="Currency" value={form.currency} onChange={(value) => setField("currency", value.toUpperCase())} />
        <Field label="Invoice date" type="date" value={form.invoice_date} onChange={(value) => setField("invoice_date", value)} />
        <Field label="Due date" type="date" value={form.due_date} onChange={(value) => setField("due_date", value)} />
        <Field label="Subtotal" value={form.subtotal_amount} onChange={(value) => setField("subtotal_amount", value)} />
        <Field label="VAT" value={form.tax_amount} onChange={(value) => setField("tax_amount", value)} />
        <Field label="Total" value={form.total_amount} onChange={(value) => setField("total_amount", value)} />
        <Field label="IBAN" value={form.iban} onChange={(value) => setField("iban", value)} />
        <div className="sm:col-span-2">
          <Field label="Payment terms" value={form.payment_terms} onChange={(value) => setField("payment_terms", value)} />
        </div>
      </div>

      {error && <div className="border-t border-line px-4 py-3 text-sm font-semibold text-berry">{error}</div>}

      <div className="flex flex-wrap justify-end gap-2 border-t border-line px-4 py-3">
        <button
          title="Save corrections"
          className="secondary-button"
          disabled={Boolean(busy)}
          onClick={() =>
            void run("save", () =>
              patchInvoice(invoice.id, {
                invoice_number: emptyToNull(form.invoice_number),
                invoice_date: emptyToNull(form.invoice_date),
                due_date: emptyToNull(form.due_date),
                currency: emptyToNull(form.currency),
                subtotal_amount: emptyToNull(form.subtotal_amount),
                tax_amount: emptyToNull(form.tax_amount),
                total_amount: emptyToNull(form.total_amount),
                iban: emptyToNull(form.iban),
                payment_terms: emptyToNull(form.payment_terms),
                supplier: {
                  name: emptyToNull(form.supplier_name),
                  vat_number: emptyToNull(form.supplier_vat_number)
                }
              })
            )
          }
        >
          <Save size={16} />
          Save
        </button>
        <button
          title="Approve invoice"
          className="primary-button"
          disabled={Boolean(busy) || invoice.status === "approved"}
          onClick={() => void run("approve", () => approveInvoice(invoice.id))}
        >
          <CheckCircle2 size={16} />
          Approve
        </button>
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text"
}: {
  label: string;
  value: string;
  type?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="field-label">{label}</span>
      <input className="input mt-1" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function toForm(invoice: Invoice): FormState {
  return {
    supplier_name: invoice.supplier?.name || "",
    supplier_vat_number: invoice.supplier?.vat_number || "",
    invoice_number: invoice.invoice_number || "",
    invoice_date: invoice.invoice_date || "",
    due_date: invoice.due_date || "",
    currency: invoice.currency || "EUR",
    subtotal_amount: invoice.subtotal_amount || "",
    tax_amount: invoice.tax_amount || "",
    total_amount: invoice.total_amount || "",
    iban: invoice.iban || "",
    payment_terms: invoice.payment_terms || ""
  };
}

function emptyToNull(value: string) {
  return value.trim() === "" ? null : value.trim();
}
