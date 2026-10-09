import { getCsrfTokenClient } from '@/lib/auth/csrfToken';
import { NEXT_PUBLIC_BACKEND_ROOT } from '@/lib/settings.mjs';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);

/**
 * Fetch wrapper for backend API calls.
 * Automatically adds X-CSRFToken for write requests (POST/PATCH/PUT/DELETE).
 * Path must be relative to backend root (e.g. '/api/curation/persons/').
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase();
  const extraHeaders: Record<string, string> = {};

  if (!SAFE_METHODS.has(method)) {
    const csrf = getCsrfTokenClient();
    if (csrf) {
      extraHeaders['X-CSRFToken'] = csrf;
    }
  }

  return fetch(NEXT_PUBLIC_BACKEND_ROOT + path, {
    credentials: 'include',
    ...init,
    headers: {
      ...(init.headers as Record<string, string>),
      ...extraHeaders,
    },
  });
}
