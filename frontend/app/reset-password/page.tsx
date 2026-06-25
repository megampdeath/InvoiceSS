"use client";

import { ArrowLeft, ArrowRight, Lock, Mail } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

/**
 * Password reset flow:
 * 1. User enters email → calls supabase.auth.resetPasswordForEmail()
 *    Supabase sends a magic-link email with a recovery token.
 * 2. User clicks the link → arrives at /reset-password with a Supabase
 *    recovery hash. Supabase JS auto-detects the recovery event.
 * 3. User enters a new password → calls supabase.auth.updateUser().
 */
function ResetPasswordInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Detect whether Supabase has set a recovery session from the magic link
  const [mode, setMode] = useState<"request" | "set-password">("request");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Supabase appends recovery params as a URL hash fragment.
    // The JS client automatically picks them up and fires PASSWORD_RECOVERY.
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") {
        setMode("set-password");
        setMessage(null);
        setError(null);
      }
    });

    // Also check if there's already a session (user might have landed here
    // after clicking the recovery link in another tab)
    supabase.auth.getSession().then(({ data }) => {
      if (data.session && searchParams.get("type") === "recovery") {
        setMode("set-password");
      }
    });

    return () => {
      listener.subscription.unsubscribe();
    };
  }, [searchParams]);

  async function handleRequestReset() {
    setError(null);
    setMessage(null);
    setIsSubmitting(true);
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password?type=recovery`,
    });
    setIsSubmitting(false);
    if (resetError) {
      setError(resetError.message);
    } else {
      setMessage("Check your email for a password reset link.");
    }
  }

  async function handleSetPassword() {
    setError(null);
    setMessage(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    const { error: updateError } = await supabase.auth.updateUser({
      password,
    });
    setIsSubmitting(false);

    if (updateError) {
      setError(updateError.message);
    } else {
      setMessage("Password updated! Redirecting to login…");
      // Sign out so the user can log in with the new password
      await supabase.auth.signOut();
      localStorage.removeItem("invoice_saas_token");
      setTimeout(() => router.push("/login"), 1500);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-panel px-4">
      <section className="w-full max-w-sm rounded-lg border border-line bg-white p-6 shadow-soft">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-ink">Reset Password</h1>
          <p className="mt-1 text-sm text-slate-500">
            {mode === "request"
              ? "Enter your email to receive a reset link."
              : "Choose a new password for your account."}
          </p>
        </div>

        {mode === "request" && (
          <>
            <label className="field-label" htmlFor="reset-email">
              Email
            </label>
            <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3 focus-within:border-signal focus-within:ring-2 focus-within:ring-signal/15">
              <Mail size={17} className="text-slate-400" />
              <input
                id="reset-email"
                type="email"
                className="h-11 flex-1 border-0 bg-transparent text-sm outline-none"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
          </>
        )}

        {mode === "set-password" && (
          <>
            <label className="field-label" htmlFor="new-password">
              New Password
            </label>
            <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3 focus-within:border-signal focus-within:ring-2 focus-within:ring-signal/15">
              <Lock size={17} className="text-slate-400" />
              <input
                id="new-password"
                type="password"
                className="h-11 flex-1 border-0 bg-transparent text-sm outline-none"
                value={password}
                minLength={8}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 characters"
              />
            </div>

            <label className="field-label mt-4" htmlFor="confirm-password">
              Confirm Password
            </label>
            <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3 focus-within:border-signal focus-within:ring-2 focus-within:ring-signal/15">
              <Lock size={17} className="text-slate-400" />
              <input
                id="confirm-password"
                type="password"
                className="h-11 flex-1 border-0 bg-transparent text-sm outline-none"
                value={confirmPassword}
                minLength={8}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat password"
              />
            </div>
          </>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {message && <p className="mt-3 text-sm text-emerald-600">{message}</p>}

        <button
          className="primary-button mt-4 w-full"
          onClick={mode === "request" ? handleRequestReset : handleSetPassword}
          disabled={
            isSubmitting ||
            (mode === "request" && !email) ||
            (mode === "set-password" && password.length < 8)
          }
        >
          {isSubmitting
            ? "Working…"
            : mode === "request"
              ? "Send Reset Link"
              : "Update Password"}
          <ArrowRight size={16} />
        </button>

        <a
          href="/login"
          className="mt-4 flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-ink"
        >
          <ArrowLeft size={14} />
          Back to login
        </a>
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-panel px-4" />
      }
    >
      <ResetPasswordInner />
    </Suspense>
  );
}
