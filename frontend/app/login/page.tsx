"use client";

import { ArrowRight, Lock, Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  async function submit() {
    setError(null);
    setIsSubmitting(true);
    const result =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });
    setIsSubmitting(false);

    if (result.error) {
      setError(result.error.message);
      return;
    }

    const session = result.data.session ?? (await supabase.auth.getSession()).data.session;
    if (!session?.access_token) {
      setError("Check your email to confirm the account, then sign in.");
      return;
    }

    localStorage.setItem("invoice_saas_token", session.access_token);
    router.push("/app/invoices");
  }

  if (!isMounted) {
    return <main className="flex min-h-screen items-center justify-center bg-panel px-4" />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-panel px-4">
      <section className="w-full max-w-sm rounded-lg border border-line bg-white p-6 shadow-soft">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-ink">Invoice SaaS</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in to the review workspace.</p>
        </div>
        <div className="mb-4 grid grid-cols-2 gap-2 rounded-md bg-slate-100 p-1 text-sm">
          <button className={`rounded px-3 py-2 ${mode === "signin" ? "bg-white shadow-sm" : ""}`} onClick={() => setMode("signin")}>
            Sign in
          </button>
          <button className={`rounded px-3 py-2 ${mode === "signup" ? "bg-white shadow-sm" : ""}`} onClick={() => setMode("signup")}>
            Sign up
          </button>
        </div>
        <label className="field-label" htmlFor="email">
          Email
        </label>
        <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3 focus-within:border-signal focus-within:ring-2 focus-within:ring-signal/15">
          <Mail size={17} className="text-slate-400" />
          <input
            id="email"
            className="h-11 flex-1 border-0 bg-transparent text-sm outline-none"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <label className="field-label mt-4" htmlFor="password">
          Password
        </label>
        <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3 focus-within:border-signal focus-within:ring-2 focus-within:ring-signal/15">
          <Lock size={17} className="text-slate-400" />
          <input
            id="password"
            className="h-11 flex-1 border-0 bg-transparent text-sm outline-none"
            value={password}
            type="password"
            minLength={8}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        {mode === "signin" && (
          <a
            href="/reset-password"
            className="mt-2 block text-xs font-medium text-signal hover:underline"
          >
            Forgot password?
          </a>
        )}
        <button
          className="primary-button mt-4 w-full"
          onClick={submit}
          disabled={isSubmitting || !email || password.length < 8}
        >
          {isSubmitting ? "Working..." : "Continue"}
          <ArrowRight size={16} />
        </button>
      </section>
    </main>
  );
}
