import React, { Suspense } from 'react';
import ProfileHeader from '@/app/(with-sidebar)/profile/_parts/ProfileHeader';
import ProfileItems from '@/app/(with-sidebar)/profile/_parts/ProfileItems';
import { VFlex } from '@/components/Flex';
import { notFound } from 'next/navigation';
import { getUserContributions } from '@/lib/api/item';
import { getJWTTokenFromSession, getCsrfToken } from '@/lib/auth/serverAuth';
import { ResourceItem } from '@/lib/types/ItemTypes';

const allowedParts: Record<string, string> = {
  activities: 'My Activities',
  contributions: 'My Contributions',
  communities: 'My Communities',
  reviews: 'My Reviews',
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
