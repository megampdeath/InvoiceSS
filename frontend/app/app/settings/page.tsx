"use client";

import { getBillingSummary, getMe } from "@/lib/api";
import { CreditCard, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

type Billing = Awaited<ReturnType<typeof getBillingSummary>>;

export default function SettingsPage() {
  const [billing, setBilling] = useState<Billing | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const me = await getMe();
        if (me.active_organization_id) {
          setBilling(await getBillingSummary(me.active_organization_id));
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load settings.");
      }
    }
    void load();
  }, []);

  return (
    <div className="space-y-5">
      <header>
        <p className="text-sm font-semibold text-signal">Workspace</p>
        <h1 className="text-2xl font-bold text-ink">Settings</h1>
      </header>
      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-berry">{error}</div>}
      {billing && (
        <div className="grid gap-4 md:grid-cols-2">
          <section className="rounded-lg border border-line bg-white p-4">
            <div className="flex items-center gap-2">
              <CreditCard size={18} className="text-signal" />
              <h2 className="text-base font-bold">Billing</h2>
            </div>
            <dl className="mt-4 space-y-3 text-sm">
              <Row label="Plan" value={billing.plan} />
              <Row label="Status" value={billing.subscription_status} />
              <Row label="Usage" value={`${billing.invoices_used} / ${billing.invoices_limit} invoices`} />
              <Row label="Stripe" value={billing.stripe_configured ? "Configured" : "Not configured"} />
            </dl>
          </section>
          <section className="rounded-lg border border-line bg-white p-4">
            <div className="flex items-center gap-2">
              <ShieldCheck size={18} className="text-signal" />
              <h2 className="text-base font-bold">Tenant Security</h2>
            </div>
            <dl className="mt-4 space-y-3 text-sm">
              <Row label="Auth" value="Supabase token seam" />
              <Row label="Storage" value="Private local adapter" />
              <Row label="Preview URLs" value="Signed short links" />
              <Row label="Exports" value="Approved invoices by default" />
            </dl>
          </section>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line pb-2 last:border-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-semibold text-ink">{value}</dd>
    </div>
  );
}
