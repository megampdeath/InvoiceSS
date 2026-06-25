import type { Invoice } from "@/lib/api";
import { FileText } from "lucide-react";

export function InvoicePreview({ invoice }: { invoice: Invoice }) {
  if (!invoice.file_preview_url) {
    return (
      <div className="flex h-[640px] items-center justify-center rounded-lg border border-line bg-white text-slate-500">
        <FileText size={24} />
      </div>
    );
  }

  if (invoice.file_mime_type.startsWith("image/")) {
    return (
      <div className="h-[640px] overflow-auto rounded-lg border border-line bg-white">
        <img src={invoice.file_preview_url} alt={invoice.original_filename} className="mx-auto max-w-full" />
      </div>
    );
  }

  return (
    <iframe
      title={invoice.original_filename}
      src={invoice.file_preview_url}
      className="h-[640px] w-full rounded-lg border border-line bg-white"
    />
  );
}
