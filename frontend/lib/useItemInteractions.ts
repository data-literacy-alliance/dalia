'use client';

import { useState, useEffect } from 'react';
import { toggleBookmark, toggleLike } from '@/lib/api/item';
import { useUserInfo } from '@/lib/auth/authApi';
import { NEXT_PUBLIC_API_URL } from '@/lib/settings.mjs';

export function useItemInteractions(
  resourceId: string,
  initial?: {
    is_bookmarked?: boolean;
    is_liked?: boolean;
    likes?: number;
  }
) {
  const { userInfo } = useUserInfo();
  const [isBookmarked, setIsBookmarked] = useState<boolean | null>(
    initial?.is_bookmarked ?? null
  );
  const [isLiked, setIsLiked] = useState<boolean | null>(initial?.is_liked ?? null);
  const [likesCount, setLikesCount] = useState<number>(initial?.likes ?? 0);
  const [isLoading, setIsLoading] = useState(false);

  const initialIsBookmarked = initial?.is_bookmarked;
  const initialIsLiked = initial?.is_liked;

  // Fetch interaction state client-side when initial values are unknown (detail page SSR)
  useEffect(() => {
    if (!userInfo || !resourceId) return;
    if (initialIsBookmarked != null && initialIsLiked != null) return;
    fetch(`${NEXT_PUBLIC_API_URL}/items/${resourceId}/interactions/`, {
      credentials: 'include',
    })
      .then((r) => (r.ok ? (r.json() as Promise<{ is_bookmarked: boolean; is_liked: boolean; likes: number }>) : null))
      .then((data) => {
        if (!data) return;
        setIsBookmarked(data.is_bookmarked);
        setIsLiked(data.is_liked);
        setLikesCount(data.likes ?? 0);
      })
      .catch(() => {});
  }, [resourceId, userInfo, initialIsBookmarked, initialIsLiked]);

  const handleBookmarkToggle = async (): Promise<boolean | null> => {
    if (!userInfo || isLoading) return null;
    setIsLoading(true);
    try {
      const result = await toggleBookmark(resourceId);
      setIsBookmarked(result.bookmarked);
      return result.bookmarked;
    } catch {
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const handleLikeToggle = async (): Promise<boolean | null> => {
    if (!userInfo || isLoading) return null;
    setIsLoading(true);
    try {
      const result = await toggleLike(resourceId);
      setIsLiked(result.liked);
      setLikesCount((prev) => (result.liked ? prev + 1 : Math.max(0, prev - 1)));
      return result.liked;
    } catch {
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isBookmarked,
    isLiked,
    likesCount,
    isLoading,
    isLoggedIn: !!userInfo,
    handleBookmarkToggle,
    handleLikeToggle,
  };
}
