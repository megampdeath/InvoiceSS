"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase, supabaseConfigError } from "@/lib/supabase";

type Status = "loading" | "authenticated" | "error";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (supabaseConfigError) {
      console.error("[AuthGuard]", supabaseConfigError);
      setError(supabaseConfigError);
      setStatus("error");
      return;
    }

    let cancelled = false;
    let listener: { subscription: { unsubscribe: () => void } } | null = null;

    async function checkSession() {
      try {
        const { data, error: err } = await supabase.auth.getSession();
        if (cancelled) return;
        if (err) {
          console.error("[AuthGuard] getSession error:", err);
          setError(err.message);
          setStatus("error");
          return;
        }
        if (data.session?.access_token) {
          localStorage.setItem("invoice_saas_token", data.session.access_token);
          setStatus("authenticated");
        } else {
          localStorage.removeItem("invoice_saas_token");
          router.replace("/login");
        }
      } catch (err) {
        console.error("[AuthGuard] getSession threw:", err);
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setStatus("error");
      }
    }

    void checkSession();

    const timeout = setTimeout(() => {
      if (cancelled || status !== "loading") return;
      console.warn("[AuthGuard] getSession timed out after 10s");
      setError("Supabase getSession() timed out. Check your network tab and console.");
      setStatus("error");
    }, 10000);

    try {
      const { data } = supabase.auth.onAuthStateChange((event, session) => {
        if (cancelled) return;
        if (event === "SIGNED_OUT" || !session) {
          localStorage.removeItem("invoice_saas_token");
          router.replace("/login");
        } else if (session?.access_token) {
          localStorage.setItem("invoice_saas_token", session.access_token);
          setStatus("authenticated");
        }
      });
      listener = data;
    } catch (err) {
      console.error("[AuthGuard] onAuthStateChange failed:", err);
    }

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      listener?.subscription.unsubscribe();
    };
  }, [router, status]);

  if (status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-panel p-4">
        <div className="max-w-lg rounded-lg border border-rose-200 bg-white p-6 shadow-sm">
          <h1 className="text-lg font-bold text-rose-700">Auth setup error</h1>
          <p className="mt-2 text-sm text-slate-700">
            The app could not connect to Supabase. This is usually a missing environment variable in the build.
          </p>
          <pre className="mt-3 overflow-auto rounded bg-slate-900 p-3 text-xs text-rose-200">
            {error || "Unknown error"}
          </pre>
          <p className="mt-3 text-xs text-slate-500">
            Open the browser console (F12) for more details. Check that NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set in Render.
          </p>
        </div>
      </div>
    );
  }

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
