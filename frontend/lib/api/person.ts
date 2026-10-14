import useSWR from 'swr';
import { AuthError, authFetcher, useUserInfo } from '@/lib/auth/authApi';

type OrcidPersonResponse = {
  name?: {
    'given-names'?: { value: string };
    'family-name'?: { value: string };
  } | null;
};

export async function lookupOrcid(
  orcidUrl: string
): Promise<{ firstname: string; lastname: string } | null> {
  try {
    const orcidId = orcidUrl.startsWith('https://orcid.org/')
      ? orcidUrl.replace('https://orcid.org/', '')
      : orcidUrl;
    const res = await fetch(`https://pub.orcid.org/v3.0/${orcidId}/person`, {
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as OrcidPersonResponse;
    const firstname = data?.name?.['given-names']?.value ?? '';
    const lastname = data?.name?.['family-name']?.value ?? '';
    if (!firstname && !lastname) return null;
    return { firstname, lastname };
  } catch {
    return null;
  }
}

export type Person = {
  id: number;
  uuid: string;
  created: string;
  modified: string;
  is_active: boolean;
  first_name: string;
  last_name: string;
  orcid: string;
  homepage: string;
  uri: string;
  privacy_level: 'public' | 'internal' | 'private';
  email_notifications: boolean;
  sync_name_from_provider: boolean;
  user: number;
};

export function usePerson(uuid: string | null) {
  const { data, isLoading } = useSWR<Person>(
    uuid ? `/api/curation/persons/${uuid}` : null,
    authFetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    person: data,
    isLoading,
  };
}

export function useUserPerson() {
  const {
    userInfo,
    isLoading: userInfoLoading,
    error: userInfoError,
  } = useUserInfo();
  const { data, isLoading, error } = useSWR<Person[], AuthError>(
    userInfo ? `/api/auth/profile/search?user_id=${userInfo.id}` : null,
    authFetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  return {
    userInfo,
    person: data && data.length === 1 ? data[0] : null,
    isLoading: userInfoLoading || isLoading,
    error: error || userInfoError,
  };
}
