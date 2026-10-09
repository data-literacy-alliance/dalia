import { cookies } from 'next/headers';
import { AUTH_ACCESS_KEY } from '@/lib/auth/authSettings';

export function getAuthToken() {
  const cookieStore = cookies();
  const allCookies = cookieStore.getAll();
  console.log('[getAuthToken] Looking for cookie:', AUTH_ACCESS_KEY);
  console.log('[getAuthToken] All cookies:', allCookies.map(c => c.name));

  const authCookie = cookieStore.get(AUTH_ACCESS_KEY);
  console.log('[getAuthToken] Auth cookie found:', !!authCookie);

  return authCookie?.value;
}

export function getCsrfToken() {
  const cookieStore = cookies();
  const csrfCookie = cookieStore.get('csrftoken');
  console.log('[getCsrfToken] CSRF token found:', !!csrfCookie);
  return csrfCookie?.value;
}

export async function getJWTTokenFromSession(): Promise<string | null> {
  console.log('[getJWTTokenFromSession] Starting...');

  const cookieStore = cookies();
  const sessionid = cookieStore.get('sessionid')?.value;
  const csrftoken = cookieStore.get('csrftoken')?.value;

  console.log('[getJWTTokenFromSession] Session cookie present:', !!sessionid);
  console.log('[getJWTTokenFromSession] CSRF token present:', !!csrftoken);

  if (!sessionid) {
    console.log('[getJWTTokenFromSession] No session cookie, returning null');
    return null;
  }

  try {
    // Build cookie header manually to include session
    const cookieHeader = cookieStore.getAll()
      .map((cookie: { name: string; value: string }) => `${cookie.name}=${cookie.value}`)
      .join('; ');

    console.log('[getJWTTokenFromSession] Calling JWT endpoint with session auth...');

    // Internal backend URL — must use container-internal hostname (web:8000) for server-side fetch.
    // NEXT_PUBLIC_BACKEND_ROOT is the public host (e.g. https://search.dalia.education) and is
    // not reachable from inside the container network. Use http://web:8000 directly.
    const response = await fetch(
      'http://web:8000/api/v1/auth/jwt/social/',
      {
        method: 'GET',
        headers: {
          'Cookie': cookieHeader,
        },
        credentials: 'include',
      }
    );

    console.log('[getJWTTokenFromSession] Response status:', response.status);

    if (!response.ok) {
      console.error('[getJWTTokenFromSession] Failed to get JWT:', response.status, response.statusText);
      return null;
    }

    const data = await response.json() as { access?: string; refresh?: string };
    console.log('[getJWTTokenFromSession] JWT received:', !!data.access);

    return data.access || null;
  } catch (error) {
    console.error('[getJWTTokenFromSession] Error:', error);
    return null;
  }
}
