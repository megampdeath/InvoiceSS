"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

/**
 * AuthGuard wraps protected /app/* pages.
 * On mount it checks for a valid Supabase session.
 * If none exists it redirects to /login.
 * While checking it renders a centered loading spinner.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "authenticated">("loading");

  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      const { data } = await supabase.auth.getSession();

      if (cancelled) return;

      if (data.session?.access_token) {
        // Keep localStorage in sync so apiFetch can read it
        localStorage.setItem("invoice_saas_token", data.session.access_token);
        setStatus("authenticated");
      } else {
        localStorage.removeItem("invoice_saas_token");
        router.replace("/login");
      }
    }

    void checkSession();

    // Listen for auth state changes (e.g. token refresh, sign-out from another tab)
    const { data: listener } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (cancelled) return;

        if (event === "SIGNED_OUT" || !session) {
          localStorage.removeItem("invoice_saas_token");
          router.replace("/login");
        } else if (session?.access_token) {
          localStorage.setItem("invoice_saas_token", session.access_token);
          setStatus("authenticated");
        }
      }
    );

    return () => {
      cancelled = true;
      listener.subscription.unsubscribe();
    };
  }, [router]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-panel">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-signal border-t-transparent" />
          <p className="text-sm text-slate-500">Checking session…</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
