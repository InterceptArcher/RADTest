/**
 * Supabase client for frontend.
 *
 * IMPORTANT: Supabase URL and anon key must be provided via environment variables.
 * These are public client-side keys (anon key), NOT service role keys.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

/**
 * Creates a no-op Supabase client proxy for when credentials are not configured.
 * All operations resolve with empty results so the app doesn't crash.
 */
function createNoopClient(): SupabaseClient {
  const noopPromise = () => Promise.resolve({ data: null, error: { message: 'Supabase not configured' } });

  const noopChain: any = new Proxy(
    {},
    {
      get: () =>
        (..._args: any[]) => {
          // If the result is awaited, return a promise
          const proxy: any = new Proxy(noopPromise, {
            get: (_t, p) => {
              if (p === 'then' || p === 'catch' || p === 'finally') {
                return noopPromise()[p as 'then'].bind(noopPromise());
              }
              return (..._a: any[]) => proxy;
            },
            apply: () => noopPromise(),
          });
          return proxy;
        },
    }
  );

  return new Proxy({} as SupabaseClient, {
    get: (_target, prop) => {
      if (prop === 'from') return () => noopChain;
      if (prop === 'channel')
        return () => ({
          on: function (this: any) {
            return this;
          },
          subscribe: () => {},
          unsubscribe: () => {},
        });
      if (prop === 'removeChannel') return () => {};
      return () => noopChain;
    },
  });
}

let _supabase: SupabaseClient;

// Only create a real client when both URL and key are valid
if (supabaseUrl.startsWith('http') && supabaseAnonKey.length > 0) {
  _supabase = createClient(supabaseUrl, supabaseAnonKey);
} else {
  if (typeof window !== 'undefined') {
    console.warn(
      'NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be provided via environment variables. ' +
        'Seller sync features will not work without them.'
    );
  }
  _supabase = createNoopClient();
}

export const supabase = _supabase;
