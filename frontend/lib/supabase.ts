"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let _supabase: SupabaseClient | null = null;

function getSupabase(): SupabaseClient {
  if (_supabase) return _supabase;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY.");
  }
  _supabase = createClient(supabaseUrl, supabaseAnonKey);
  return _supabase;
}

export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    const client = getSupabase();
    const value = Reflect.get(client, prop);
    return typeof value === "function" ? value.bind(client) : value;
  },
});

if (typeof window !== "undefined") {
  getSupabase().auth.onAuthStateChange((event, session) => {
    if (session?.access_token) {
      localStorage.setItem("invoice_saas_token", session.access_token);
    }
    if (event === "SIGNED_OUT") {
      localStorage.removeItem("invoice_saas_token");
    }
  });
}

