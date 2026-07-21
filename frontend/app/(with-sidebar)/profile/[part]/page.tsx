import React, { Suspense } from 'react';
import ProfileHeader from '@/app/(with-sidebar)/profile/_parts/ProfileHeader';
import ProfileItems from '@/app/(with-sidebar)/profile/_parts/ProfileItems';
import { VFlex } from '@/components/Flex';
import { notFound, redirect } from 'next/navigation';
import { getUserContributions, getUserBookmarks, getUserLikes } from '@/lib/api/item';
import { getJWTTokenFromSession, getCsrfToken } from '@/lib/auth/serverAuth';
import { ResourceItem } from '@/lib/types/ItemTypes';

const allowedParts: Record<string, string> = {
  activities: 'My Activities',
  contributions: 'My Contributions',
  communities: 'My Communities',
  reviews: 'My Reviews',
  bookmarks: 'My Bookmarks',
  likes: 'My Likes',
};

export default async function ProfilePage({
  params,
  searchParams,
}: {
  params: { part: string };
  searchParams: { filter?: string; page?: string };
}) {
  const part = params.part;
  console.log('[ProfilePage] Loading profile page:', { part, allowedParts: Object.keys(allowedParts) });

  if (!Object.keys(allowedParts).includes(part)) {
    console.log('[ProfilePage] Part not allowed, returning 404');
    notFound();
  }

  let results: ResourceItem[] = [];

  // Fetch contributions if on contributions page
  if (part === 'contributions') {
    console.log('[ProfilePage] Part is contributions, getting JWT token from session...');

    // Get JWT token from session
    const authToken = await getJWTTokenFromSession();
    const csrfToken = getCsrfToken();

    console.log('[ProfilePage] JWT token obtained:', !!authToken);
    console.log('[ProfilePage] CSRF token present:', !!csrfToken);

    if (authToken) {
      const filter = searchParams.filter as 'my-resources' | 'pending' | 'published' | 'archived' | 'unpublished' | 'all-resources' | undefined;
      const page = parseInt(searchParams.page || '1', 10);

      // all-resources is a regular filter value — no showAll needed
      const showAll = false;
      const versionFilter = filter || 'my-resources';

      console.log('[ProfilePage] Calling getUserContributions with filter:', versionFilter, 'showAll:', showAll, 'page:', page);
      const data = await getUserContributions(authToken, csrfToken, versionFilter, showAll, page);
      console.log('[ProfilePage] getUserContributions returned:', data.results.length, 'items');
      results = data.results;
      const pagination = { count: data.count ?? 0, next: data.next ?? null, previous: data.previous ?? null, page };

      return (
        <VFlex className={'h-full w-full border-primary pb-4 lg:border-l'}>
          <Suspense fallback={'Loading...'}>
            <ProfileHeader />
            <ProfileItems items={results} title={allowedParts[part]} pagination={pagination} />
          </Suspense>
        </VFlex>
      );
    } else {
      console.log('[ProfilePage] No JWT token available, skipping fetch');
    }
  }

  // Fetch bookmarks/likes when on the activities page (filter=bookmark or filter=likes)
  if (part === 'activities' && (searchParams.filter === 'bookmark' || searchParams.filter === 'likes')) {
    const authToken = await getJWTTokenFromSession();
    const csrfToken = getCsrfToken();

    if (authToken) {
      const page = parseInt(searchParams.page || '1', 10);
      let data: { results: unknown[]; count: number; next: string | null; previous: string | null };
      try {
        data = searchParams.filter === 'bookmark'
          ? await getUserBookmarks(authToken, csrfToken, page)
          : await getUserLikes(authToken, csrfToken, page);
      } catch (e) {
        if (e instanceof Error && e.message === 'AUTH_EXPIRED') {
          redirect('/login');
        }
        data = { results: [], count: 0, next: null, previous: null };
      }
      results = data.results as unknown as ResourceItem[];
      const pagination = { count: data.count ?? 0, next: data.next ?? null, previous: data.previous ?? null, page };

      return (
        <VFlex className={'h-full w-full border-primary pb-4 lg:border-l'}>
          <Suspense fallback={'Loading...'}>
            <ProfileHeader />
            <ProfileItems items={results} title={allowedParts[part]} pagination={pagination} editable={false} deletable={false} />
          </Suspense>
        </VFlex>
      );
    }
  }

  console.log('[ProfilePage] Rendering with', results.length, 'results');

  return (
    <VFlex className={'h-full w-full border-primary pb-4 lg:border-l'}>
      <Suspense fallback={'Loading...'}>
        <ProfileHeader />
        <ProfileItems items={results} title={allowedParts[part]} />
      </Suspense>
    </VFlex>
  );
}
