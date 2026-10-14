'use client';
import useSWR from 'swr';
import { NEXT_PUBLIC_BACKEND_ROOT } from '@/lib/settings.mjs';
import { UserInfo } from '@/lib/auth/authSettings';

export class AuthError extends Error {}

type authFetcherAllInput = [addr: string, init: RequestInit];

export const authFetcher = async (input: string | authFetcherAllInput) => {
  let addr: string;
  let init: authFetcherAllInput[1] = {};
  if (Array.isArray(input)) {
    addr = input[0];
    init = input[1];
  } else {
    addr = input;
  }

  const result = await fetch(NEXT_PUBLIC_BACKEND_ROOT + addr, {
    ...init,
    credentials: 'include',
  });

  if (!result.ok) {
    throw new AuthError();
  }

  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  return result.json();
};

export function useAuthGetTokensRequest(skip?: boolean) {
  const { data, isLoading, error, mutate } = useSWR<
    {
      access: string;
      refresh: string;
    },
    AuthError
  >(skip ? null : '/api/auth/jwt/social/', authFetcher, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 10_000,
    shouldRetryOnError: false,
  });

  return {
    tokens: data,
    isLoading,
    error,
    mutate,
  };
}

export function useAuthRefreshTokenRequest(refreshToken: string | undefined) {
  const { data, isLoading, error, mutate } = useSWR<
    {
      access: string;
      refresh: string;
    },
    AuthError
  >(
    !refreshToken
      ? null
      : [
          '/api/auth/jwt/refresh/',
          {
            method: 'POST',
            body: JSON.stringify(refreshToken),
          },
        ],
    authFetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  return {
    tokens: data,
    isLoading,
    error,
    refetch: mutate,
  };
}

export function useUserInfo() {
  const { data, isLoading, isValidating, error } = useSWR<UserInfo, AuthError>(
    '/api/auth/me/',
    authFetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      shouldRetryOnError: false,
    }
  );

  return {
    userInfo: data,
    // Treat background revalidation as loading to prevent premature redirects when
    // SWR has a stale/cached error but a fresh request is already in-flight.
    isLoading: isLoading || isValidating,
    error,
  };
}

export function useUserProfile() {
  const { data, isLoading, error } = useSWR<UserInfo, AuthError>(
    '/api/auth/profile/',
    authFetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  return {
    userProfile: data,
    userProfileLoading: isLoading,
    error,
  };
}
