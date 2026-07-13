'use client';

import { useItemInteractions } from '@/lib/useItemInteractions';
import IconButton from '@/components/IconButton';

interface InteractionButtonsProps {
  resourceId: string;
  initialIsBookmarked?: boolean;
  initialIsLiked?: boolean;
  initialLikes?: number;
  small?: boolean;
  onRemove?: () => void;
}

export default function InteractionButtons({
  resourceId,
  initialIsBookmarked,
  initialIsLiked,
  initialLikes,
  small,
  onRemove,
}: InteractionButtonsProps) {
  const {
    isBookmarked,
    isLiked,
    likesCount,
    isLoading,
    isLoggedIn,
    handleBookmarkToggle,
    handleLikeToggle,
  } = useItemInteractions(resourceId, {
    is_bookmarked: initialIsBookmarked,
    is_liked: initialIsLiked,
    likes: initialLikes,
  });

  return (
    <>
      <IconButton
        source={isBookmarked ? 'bookmark' : 'bookmark-outline'}
        dark={!(isBookmarked ?? false)}
        small={small}
        disabled={!isLoggedIn || isLoading}
        onClick={() => { void handleBookmarkToggle().then(v => { if (v === false) onRemove?.(); }); }}
        title={isBookmarked ? 'Remove bookmark' : 'Bookmark this resource'}
        aria-pressed={isBookmarked ?? false}
      />
      <IconButton
        source={isLiked ? 'heart' : 'heart-outline'}
        dark={!(isLiked ?? false)}
        small={small}
        disabled={!isLoggedIn || isLoading}
        onClick={() => { void handleLikeToggle().then(v => { if (v === false) onRemove?.(); }); }}
        title={isLiked ? 'Unlike this resource' : `Like this resource (${likesCount})`}
        aria-pressed={isLiked ?? false}
      />
    </>
  );
}
