import { BACKEND_URL, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_BACKEND_ROOT } from '@/lib/settings.mjs';

export default async function appFetch(
  input: string,
  init?: RequestInit
): Promise<Response> {
  const isServer = typeof window === 'undefined';

  if (!input.startsWith('http')) {
    // Relative path: prepend appropriate base URL
    const baseUrl = isServer && BACKEND_URL ? BACKEND_URL : NEXT_PUBLIC_API_URL;
    input = `${baseUrl}${input}`;
  } else if (isServer && BACKEND_URL && NEXT_PUBLIC_BACKEND_ROOT && input.startsWith(NEXT_PUBLIC_BACKEND_ROOT)) {
    // Full URL using baked-in localhost root — rewrite to container DNS for SSR
    const backendRoot = new URL(BACKEND_URL).origin; // "http://web:8000"
    input = input.replace(NEXT_PUBLIC_BACKEND_ROOT, backendRoot);
  }

  const noCacheInit: RequestInit = {
    ...init,
    cache: 'no-store',
  };

  return fetch(input, noCacheInit);
}
