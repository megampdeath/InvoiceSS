"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const TOKEN_KEY = "invoice_saas_token";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "authenticated">("loading");

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;

    if (token) {
      setStatus("authenticated");
      return;
    }

    // No token → redirect to login immediately.
    // Don't call supabase.auth.getSession() here — it can hang if the
    // Supabase client initialization stalls in the browser, freezing
    // the page on "Checking session…". The login page sets the token
    // in localStorage after a successful Supabase sign-in, so checking
    // localStorage is sufficient and instant.
    router.replace("/login");
  }, [router]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-panel">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-signal border-t-transparent" />
          <p className="text-sm text-slate-500">Loading…</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
