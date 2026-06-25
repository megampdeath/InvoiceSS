"use client";

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY.");
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Keep localStorage token in sync with the Supabase session.
// TOKEN_REFRESH events auto-update the stored access token so API calls
// always use a fresh JWT without manual refresh logic elsewhere.
if (typeof window !== "undefined") {
  supabase.auth.onAuthStateChange((event, session) => {
    if (session?.access_token) {
      localStorage.setItem("invoice_saas_token", session.access_token);
    }
    if (event === "SIGNED_OUT") {
      localStorage.removeItem("invoice_saas_token");
    }
  });
}

