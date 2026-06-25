"use client";

import { getMe, getSuppliers, type Supplier } from "@/lib/api";
import { money } from "@/lib/formatting";
import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const me = await getMe();
        if (me.active_organization_id) {
          setSuppliers(await getSuppliers(me.active_organization_id));
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load suppliers.");
      }
    }
    void load();
  }, []);

  return (
    <div className="space-y-5">
      <header>
        <p className="text-sm font-semibold text-signal">Memory</p>
        <h1 className="text-2xl font-bold text-ink">Suppliers</h1>
      </header>
      <section className="rounded-lg border border-line bg-white">
        {error && <div className="border-b border-line bg-rose-50 px-4 py-3 text-sm font-semibold text-berry">{error}</div>}
        {suppliers.length === 0 ? (
          <div className="flex items-center gap-3 p-6 text-sm text-slate-500">
            <Building2 size={20} />
            No suppliers have been captured yet.
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Supplier</th>
                <th className="px-4 py-3">VAT</th>
                <th className="px-4 py-3">Invoices</th>
                <th className="px-4 py-3">Total</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-semibold">{supplier.name}</td>
                  <td className="px-4 py-3">{supplier.vat_number || "-"}</td>
                  <td className="px-4 py-3">{supplier.invoice_count}</td>
                  <td className="px-4 py-3">{money(supplier.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
