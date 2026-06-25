"use client";

import clsx from "clsx";
import { Archive, Building2, FileCheck2, FileSpreadsheet, Inbox, LogOut, Settings, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const items = [
  { href: "/app/invoices", label: "Inbox", icon: Inbox },
  { href: "/app/invoices?status=needs_review", label: "Review", icon: FileCheck2 },
  { href: "/app/invoices?status=approved", label: "Approved", icon: Archive },
  { href: "/app/suppliers", label: "Suppliers", icon: Users },
  { href: "/app/exports", label: "Exports", icon: FileSpreadsheet },
  { href: "/app/settings", label: "Settings", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white lg:block">
        <div className="flex h-16 items-center gap-2 border-b border-line px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-ink text-white">
            <Building2 size={19} />
          </div>
          <div>
            <p className="text-sm font-bold">Invoice SaaS</p>
            <p className="text-xs text-slate-500">Demo Workspace</p>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {items.map((item) => {
            const active = pathname === item.href.split("?")[0];
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition",
                  active ? "bg-teal-50 text-signal" : "text-slate-600 hover:bg-slate-50 hover:text-ink"
                )}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          title="Log out"
          className="absolute bottom-4 left-3 right-3 flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          onClick={async () => {
            try {
              await (await import("@/lib/supabase")).supabase.auth.signOut();
            } catch {
              // best-effort: signOut may fail if already expired
            }
            localStorage.removeItem("invoice_saas_token");
            router.push("/login");
          }}
        >
          <LogOut size={18} />
          Log out
        </button>
      </aside>
      <main className="lg:pl-64">
        <div className="mx-auto min-h-screen max-w-7xl px-4 py-5 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
