"use client";

import { UploadDropzone } from "@/components/upload-dropzone";
import { getInvoices, getMe, getStatusCounts, uploadInvoice, type Invoice, type Me, type UploadProgress } from "@/lib/api";
import { money, percent, shortDate } from "@/lib/formatting";
import { Download, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { StatusBadge } from "@/components/status-badge";

const statuses = ["all", "uploaded", "processing", "needs_review", "approved", "failed", "archived"];

type PendingUpload = {
  id: string;
  filename: string;
  progress: number;
};

export default function InvoiceInboxPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);

  const organizationId = me?.active_organization_id || "";

  useEffect(() => {
    const queryStatus = new URLSearchParams(window.location.search).get("status");
    if (queryStatus && statuses.includes(queryStatus)) {
      setStatus(queryStatus);
    }
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      const user = me || (await getMe());
      setMe(user);
      const orgId = user.active_organization_id;
      if (!orgId) {
        setInvoices([]);
        return;
      }
      const params: Record<string, string> = {};
      if (status !== "all") {
        params.status = status;
      }
      if (search.trim()) {
        params.search = search.trim();
      }
      const [invoiceList, statusCounts] = await Promise.all([getInvoices(orgId, params), getStatusCounts(orgId)]);
      setInvoices(invoiceList.items);
      setCounts(statusCounts);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load invoices.");
    } finally {
      setLoading(false);
    }
  }, [me, search, status]);

  useEffect(() => {
    void load();
  }, [load]);

  const totals = useMemo(
    () => ({
      all: Object.values(counts).reduce((sum, value) => sum + value, 0),
      needs_review: counts.needs_review || 0,
      approved: counts.approved || 0,
      failed: counts.failed || 0
    }),
    [counts]
  );

  async function handleUpload(file: File, onProgress: (progress: UploadProgress) => void) {
    if (!organizationId) {
      return;
    }
    const pendingId = crypto.randomUUID();
    const pending = { id: pendingId, filename: file.name, progress: 1 };
    setError(null);
    setPendingUploads((current) => [pending, ...current]);
    try {
      await uploadInvoice(organizationId, file, (progress) => {
        onProgress(progress);
        setPendingUploads((current) =>
          current.map((item) => (item.id === pendingId ? { ...item, progress: progress.percent } : item))
        );
      });
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to upload invoice.");
    } finally {
      setPendingUploads((current) => current.filter((item) => item.id !== pendingId));
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-signal">Inbox</p>
          <h1 className="text-2xl font-bold text-ink">Invoices</h1>
        </div>
        <Link href="/app/exports" className="secondary-button">
          <Download size={16} />
          Exports
        </Link>
      </header>

      <div className="grid gap-3 sm:grid-cols-4">
        <Metric label="All" value={totals.all} />
        <Metric label="Review" value={totals.needs_review} tone="amber" />
        <Metric label="Approved" value={totals.approved} tone="teal" />
        <Metric label="Failed" value={totals.failed} tone="rose" />
      </div>

      <UploadDropzone onUpload={handleUpload} disabled={!organizationId} />

      <section className="rounded-lg border border-line bg-white">
        <div className="flex flex-col gap-3 border-b border-line p-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            {statuses.map((item) => (
              <button
                key={item}
                className={item === status ? "primary-button" : "secondary-button"}
                onClick={() => setStatus(item)}
              >
                {item.replace("_", " ")}
              </button>
            ))}
          </div>
          <label className="flex min-w-64 items-center gap-2 rounded-md border border-line bg-white px-3 focus-within:border-signal focus-within:ring-2 focus-within:ring-signal/15">
            <Search size={16} className="text-slate-400" />
            <input
              className="h-9 flex-1 border-0 bg-transparent text-sm outline-none"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search"
            />
            <SlidersHorizontal size={16} className="text-slate-400" />
          </label>
        </div>

        {error && <div className="border-b border-line bg-rose-50 px-4 py-3 text-sm font-semibold text-berry">{error}</div>}
        {loading ? (
          <div className="p-6 text-sm text-slate-500">Loading invoices...</div>
        ) : invoices.length === 0 && pendingUploads.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">No invoices match the current view.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="border-b border-line bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Invoice</th>
                  <th className="px-4 py-3">Supplier</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {pendingUploads.map((upload) => (
                  <tr key={upload.id} className="border-b border-line bg-teal-50/60">
                    <td className="px-4 py-3">
                      <span className="font-semibold text-ink">{upload.filename}</span>
                      <div className="mt-2 h-1.5 max-w-52 overflow-hidden rounded-full bg-slate-200">
                        <div className="h-full bg-signal transition-all" style={{ width: `${upload.progress}%` }} />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-500">-</td>
                    <td className="px-4 py-3 text-slate-500">-</td>
                    <td className="px-4 py-3 text-slate-500">-</td>
                    <td className="px-4 py-3 text-slate-500">{upload.progress}%</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={upload.progress >= 100 ? "processing" : "uploaded"} />
                    </td>
                  </tr>
                ))}
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-line last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link href={`/app/invoices/${invoice.id}`} className="font-semibold text-ink hover:text-signal">
                        {invoice.invoice_number || invoice.original_filename}
                      </Link>
                      <div className="text-xs text-slate-500">{invoice.original_filename}</div>
                    </td>
                    <td className="px-4 py-3">{invoice.supplier?.name || "-"}</td>
                    <td className="px-4 py-3">{shortDate(invoice.invoice_date)}</td>
                    <td className="px-4 py-3">{money(invoice.total_amount, invoice.currency || "EUR")}</td>
                    <td className="px-4 py-3">{percent(invoice.extraction_confidence)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={invoice.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value, tone = "slate" }: { label: string; value: number; tone?: "slate" | "amber" | "teal" | "rose" }) {
  const colors = {
    slate: "border-slate-200 bg-white text-slate-700",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    teal: "border-teal-200 bg-teal-50 text-teal-900",
    rose: "border-rose-200 bg-rose-50 text-rose-900"
  };
  return (
    <div className={`rounded-lg border p-4 ${colors[tone]}`}>
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}
