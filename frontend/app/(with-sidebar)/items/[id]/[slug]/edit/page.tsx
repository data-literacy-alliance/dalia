import React, { Suspense } from 'react';
import { notFound, redirect } from 'next/navigation';
import { LoginURL } from '@/lib/settings.mjs';
import { VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import AddContentData from '@/app/(with-sidebar)/items/new/_parts/AddContentData';
import { getJWTTokenFromSession } from '@/lib/auth/serverAuth';
import {
  ResourceContentResponse,
  transformResourceContentToItem,
} from '@/lib/api/curationContent';
import { ResourceItem } from '@/lib/types/ItemTypes';

type ItemDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function ItemEditPage({
  params: { id },
}: ItemDetails) {
  const authToken = await getJWTTokenFromSession();

  if (!authToken) {
    redirect(LoginURL);
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    notFound();
  }
  const backendOrigin = new URL(backendUrl).origin;

  const headers = {
    Authorization: `Bearer ${authToken}`,
  };

  // Resolve resource uuid → editable content via the new ?resource= filter
  const listUrl = new URL(`${backendOrigin}/api/curation/resource-contents/`);
  listUrl.searchParams.set('resource', id);
  listUrl.searchParams.set('filter', 'all-resources');
  const listResponse = await fetch(listUrl.toString(), { headers, cache: 'no-store' });

  if (!listResponse.ok) {
    notFound();
  }

  const listData = (await listResponse.json()) as
    | { results: ResourceContentResponse[] }
    | ResourceContentResponse[];

  const results: ResourceContentResponse[] =
    'results' in listData ? listData.results : listData;

  if (results.length === 0) {
    return (
      <VFlex className={'flex-1 border-l border-primary'}>
        <div className={'border-b border-primary px-10 py-14 lg:px-14'}>
          <Text variant={'h2'}>Editing not available yet</Text>
        </div>
        <div className={'px-10 py-10 lg:px-14'}>
          <Text>
            This resource isn&apos;t editable yet — we&apos;re currently merging our
            databases. Editing will be available here soon.
          </Text>
        </div>
      </VFlex>
    );
  }

  // Prefer the active content; fall back to the first (latest by -id ordering)
  const content: ResourceContentResponse = results.find((c) => c.is_active) ?? results[0];

  const item: ResourceItem = transformResourceContentToItem(content);

  const contentUuid = content.uuid;

  // Fetch related works
  try {
    const relatedResponse = await fetch(
      `${backendOrigin}/api/curation/related-items/?content=${contentUuid}`,
      { headers, cache: 'no-store' }
    );
    if (relatedResponse.ok) {
      const relatedData = (await relatedResponse.json()) as
        | { results: Array<{ target_url: string; relation_type: number; relation_type_label: string }> }
        | Array<{ target_url: string; relation_type: number; relation_type_label: string }>;
      const relatedItems = 'results' in relatedData ? relatedData.results : relatedData;
      item.related_works = relatedItems.map((rel) => ({
        type: { label: rel.relation_type_label || '', value: String(rel.relation_type) },
        link: rel.target_url,
      }));
    }
  } catch {
    // non-fatal: related works left empty
  }

  // Fetch community relations
  try {
    const communitiesResponse = await fetch(
      `${backendOrigin}/api/curation/community-relations/?content=${contentUuid}`,
      { headers, cache: 'no-store' }
    );
    if (communitiesResponse.ok) {
      const communitiesData = (await communitiesResponse.json()) as
        | { results: Array<{ community: number; community_title: string }> }
        | Array<{ community: number; community_title: string }>;
      const communityRels =
        'results' in communitiesData ? communitiesData.results : communitiesData;
      item.communities = communityRels.map((rel) => ({
        id: String(rel.community),
        title: rel.community_title ?? '',
        slug: '',
        image: '',
        url: '',
        about: '',
        likes: 0,
        views: 0,
        followers: 0,
        is_supporting: false,
        is_recommending: false,
      }));
    }
  } catch {
    // non-fatal: communities left null
  }

  return (
    <VFlex className={'flex-1 border-l border-primary'}>
      <div className={'border-b border-primary px-10 py-14 lg:px-14'}>
        <Text variant={'h2'}>Edit content</Text>
      </div>
      <Suspense fallback={'Loading...'}>
        <AddContentData item={item} />
      </Suspense>
    </VFlex>
  );
}
