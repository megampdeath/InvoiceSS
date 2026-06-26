"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let _client: SupabaseClient | null = null;

function getClient(): SupabaseClient {
  if (_client) return _client;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY.");
  }
  _client = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
  return _client;
}

export const supabase = {
  get auth() {
    return getClient().auth;
  },
} as unknown as SupabaseClient;

if (typeof window !== "undefined") {
  try {
    getClient().auth.onAuthStateChange((event, session) => {
      if (session?.access_token) {
        localStorage.setItem("invoice_saas_token", session.access_token);
      }
      if (event === "SIGNED_OUT") {
        localStorage.removeItem("invoice_saas_token");
      }
    });
  } catch {
    // best-effort: client init failure is handled at call sites
  }
}
