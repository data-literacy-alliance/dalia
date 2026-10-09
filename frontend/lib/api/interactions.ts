'use client';

import { apiFetch } from '@/lib/auth/apiFetch';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import { useUserInfo } from '@/lib/auth/authApi';
import { useCallback } from 'react';

export function useLikeItem() {
  const { access } = useAuthLogin();
  const { userInfo } = useUserInfo();

  return useCallback(
    async (itemId: number) => {
      if (!access || !userInfo) return null;
      try {
        const result = await apiFetch('/api/curation/likes/toggle/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${access}`,
          },
          body: JSON.stringify({
            object_id: itemId,
            user: userInfo.id,
          }),
        });

        return await result.json() as Promise<{
          id: number;
          uuid: string;
          content_object_str: string;
          created: string;
          modified: string;
          object_id: number;
          user: number;
          content_type: number;
        }>;
      } catch (e) {
        return null;
      }
    },
    [access, userInfo]
  );
}
