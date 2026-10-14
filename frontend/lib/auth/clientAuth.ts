'use client';
import Cookies from 'js-cookie';
import {
  useAuthGetTokensRequest,
  useAuthRefreshTokenRequest,
} from '@/lib/auth/authApi';
import { AUTH_ACCESS_KEY, AUTH_REFRESH_KEY } from '@/lib/auth/authSettings';
import { NEXT_PUBLIC_BACKEND_ROOT } from '@/lib/settings.mjs';

/**
 * Use this hook when you think the user has already logged in.
 */
export function useAuthLogin() {
  // get fresh access token if we don't have one
  const { tokens, isLoading, mutate } = useAuthGetTokensRequest();

  return {
    isLoading,
    loggedIn: !!tokens,
    access: tokens?.access,
    refresh: tokens?.refresh,
    refetch: mutate,
  };
}

export function useAuthRefresh() {
  const refresh = Cookies.get(AUTH_REFRESH_KEY);
  const access = Cookies.get(AUTH_ACCESS_KEY);

  const { tokens, isLoading } = useAuthRefreshTokenRequest(refresh);

  if (tokens && tokens.refresh !== refresh) {
    Cookies.set(AUTH_ACCESS_KEY, tokens.access, {
      path: '/',
      sameSite: 'Lax',
    });
    Cookies.set(AUTH_REFRESH_KEY, tokens.refresh, {
      path: '/',
      sameSite: 'Lax',
    });
  }

  return {
    isLoading,
    loggedIn: !!tokens,
    access,
    refresh,
  };
}

export async function clientLogout(access: string) {
  Cookies.remove(AUTH_ACCESS_KEY);
  Cookies.remove(AUTH_REFRESH_KEY);

  const result = await fetch(NEXT_PUBLIC_BACKEND_ROOT + '/api/auth/logout/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${access}`,
    },
  });

  return result.ok;
}
