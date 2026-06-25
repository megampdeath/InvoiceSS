"use client";

import { createExport, getMe } from "@/lib/api";
import { Download, FileSpreadsheet } from "lucide-react";
import { useEffect, useState } from "react";

type ExportResult = { id: string; status: string; format: string; row_count: number; download_url?: string };

export default function ExportsPage() {
  const [organizationId, setOrganizationId] = useState("");
  const [result, setResult] = useState<ExportResult | null>(null);
  const [busy, setBusy] = useState<"csv" | "xlsx" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const me = await getMe();
      setOrganizationId(me.active_organization_id || "");
    }
    void load();
  }, []);

  async function run(format: "csv" | "xlsx") {
    if (!organizationId) {
      return;
    }
    setBusy(format);
    setError(null);
    try {
      setResult(await createExport(organizationId, format));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Export failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <p className="text-sm font-semibold text-signal">Files</p>
        <h1 className="text-2xl font-bold text-ink">Exports</h1>
      </header>
      <section className="rounded-lg border border-line bg-white p-4">
        <div className="flex flex-wrap gap-2">
          <button className="primary-button" disabled={Boolean(busy)} onClick={() => void run("xlsx")}>
            <FileSpreadsheet size={16} />
            XLSX
          </button>
          <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void run("csv")}>
            <FileSpreadsheet size={16} />
            CSV
          </button>
        </div>
        {error && <div className="mt-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm font-semibold text-berry">{error}</div>}
        {result && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-slate-50 p-3 text-sm">
            <div>
              <div className="font-semibold text-ink">{result.format.toUpperCase()} export ready</div>
              <div className="text-slate-500">{result.row_count} row(s)</div>
            </div>
            {result.download_url && (
              <a className="primary-button" href={result.download_url}>
                <Download size={16} />
                Download
              </a>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
