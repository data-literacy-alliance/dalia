import useSWR from 'swr';
import { authFetcher } from '@/lib/auth/authApi';

type CommunityItem = {
  id: number;
  uuid: string;
  created: string;
  modified: string;
  is_active: boolean;
  title: string;
  slug: string;
  uri: string;
  description: string;
  moderation_policy: string;
  auto_publish_threshold: number;
  requires_approval: boolean;
};

export function useCommunities(skip: boolean = false) {
  const { data, isLoading } = useSWR<CommunityItem[]>(
    !skip ? '/api/curation/communities/' : null,
    authFetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    communities: data ?? [],
    isLoading,
  }
}
