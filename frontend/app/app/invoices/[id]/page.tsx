"use client";

import { InvoicePreview } from "@/components/invoice-preview";
import { InvoiceReviewForm } from "@/components/invoice-review-form";
import { getInvoice, type Invoice } from "@/lib/api";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setInvoice(await getInvoice(params.id));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load invoice.");
      }
    }
    void load();
  }, [params.id]);

  if (error) {
    return <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-berry">{error}</div>;
  }
  if (!invoice) {
    return <div className="rounded-lg border border-line bg-white p-6 text-sm text-slate-500">Loading invoice...</div>;
  }

  return (
    <div className="space-y-4">
      <Link href="/app/invoices" className="secondary-button w-fit">
        <ArrowLeft size={16} />
        Invoices
      </Link>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(420px,0.9fr)]">
        <InvoicePreview invoice={invoice} />
        <InvoiceReviewForm invoice={invoice} onChange={setInvoice} />
      </div>
    </div>
  );
}
