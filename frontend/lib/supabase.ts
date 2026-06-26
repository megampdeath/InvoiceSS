"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabaseConfigError =
  !supabaseUrl || !supabaseAnonKey
    ? `Missing Supabase env vars in the browser bundle. URL=${supabaseUrl || "(empty)"} KEY=${supabaseAnonKey ? "(set)" : "(empty)"}`
    : null;

let _client: SupabaseClient | null = null;

function getClient(): SupabaseClient {
  if (_client) return _client;
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(supabaseConfigError || "Supabase not configured");
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

if (typeof window !== "undefined" && !supabaseConfigError) {
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
    // best-effort
  }
}
