import Text from '@/components/Text';
import React, { Suspense } from 'react';
import { VFlex } from '@/components/Flex';
import AddContentData from '@/app/(with-sidebar)/items/new/_parts/AddContentData';
import { getJWTTokenFromSession } from '@/lib/auth/serverAuth';
import { ResourceItem } from '@/lib/types/ItemTypes';

type ResourceContentResponse = {
  id: number;
  uuid: string;
  title: string;
  main_url: string;
  description: string;
  publication_date: string | null;
  people: Array<{
    id: number;
    uuid: string;
    first_name: string;
    last_name: string;
    orcid: string;
  }>;
  organizations: Array<{
    id: number;
    uuid: string;
    name?: string;
    ror?: string;
  }>;
  languages: Array<{
    id: number;
    code: string;
    label: string;
    native_name: string;
  }>;
  learning_resource_types: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  disciplines: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  licenses: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
    spdx_id: string;
  }>;
  proficiency_levels: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  target_groups: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  file_formats: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  media_types: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  size_mb: string | null;
};

function transformResourceContentToItem(content: ResourceContentResponse): ResourceItem {
  const authors = [
    ...(Array.isArray(content.people) ? content.people : []).map((p) => ({
      firstname: p.first_name || '',
      lastname: p.last_name || '',
      orcid: p.orcid || '',
      authorType: 'PersonAuthor' as const,
      id: p.id,
      uuid: p.uuid,
    })),
    ...(Array.isArray(content.organizations) ? content.organizations : []).map((o) => ({
      name: o.name || '',
      ror: o.ror || '',
      authorType: 'OrganizationAuthor' as const,
      id: o.id,
      uuid: o.uuid,
    })),
  ];

  return {
    id: content.uuid || String(content.id),
    slug: content.uuid || String(content.id),
    title: content.title || 'Untitled',
    url: content.main_url || '',
    description: content.description || '',
    authors,
    communities: null,
    likes: 0,
    views: 0,
    comments: 0,
    tags: [],
    related_works: [],
    learning_resource_types: Array.isArray(content.learning_resource_types)
      ? content.learning_resource_types.map((t) => ({
          label: t.label || '',
          value: String(t.id),
        }))
      : [],
    media_types: Array.isArray(content.media_types)
      ? content.media_types.map((t) => ({
          label: t.label || '',
          value: String(t.id),
        }))
      : [],
    disciplines: Array.isArray(content.disciplines)
      ? content.disciplines.map((d) => ({
          label: d.label || '',
          value: String(d.id),
        }))
      : [],
    target_groups: Array.isArray(content.target_groups)
      ? content.target_groups.map((t) => ({
          label: t.label || '',
          value: String(t.id),
        }))
      : [],
    proficiency_levels: Array.isArray(content.proficiency_levels)
      ? content.proficiency_levels.map((p) => ({
          label: p.label || '',
          value: String(p.id),
        }))
      : [],
    format: Array.isArray(content.file_formats) ? content.file_formats : [],
    license: Array.isArray(content.licenses) && content.licenses[0]
      ? {
          id: String(content.licenses[0].id),
          name: content.licenses[0].label || '',
          link: '',
        }
      : { id: '', name: '', link: '' },
    publication_date: content.publication_date || '',
    links: [],
    languages: Array.isArray(content.languages)
      ? content.languages.map((l) => ({
          id: l.id,
          label: l.label || l.code || '',
          code: l.code,
        }))
      : [],
    file_size: content.size_mb ? `${content.size_mb} MB` : undefined,
  };
}

export default async function AddContentPage({
  searchParams,
}: {
  searchParams: { id?: string };
}) {
  let item: ResourceItem | undefined = undefined;
  const editId = searchParams.id;

  console.log('[AddContentPage] Starting with searchParams:', searchParams);
  console.log('[AddContentPage] editId:', editId);

  // If editing, fetch the draft content
  if (editId) {
    console.log('[AddContentPage] Attempting to fetch draft for id:', editId);
    try {
      const authToken = await getJWTTokenFromSession();
      console.log('[AddContentPage] JWT token obtained:', !!authToken);
      if (authToken) {
        const headers = {
          Authorization: `Bearer ${authToken}`,
        };

        // Use the internal container URL (http://web:8000) for server-side fetches.
        // BACKEND_URL env var is "http://web:8000/api/..." so we extract the origin only.
        const backendOrigin = process.env.BACKEND_URL
          ? new URL(process.env.BACKEND_URL).origin
          : '';

        // Fetch the resource content
        const response = await fetch(
          `${backendOrigin}/api/curation/resource-contents/${editId}/?show_all=true`,
          {
            headers,
            cache: 'no-store',
          }
        );

        if (response.ok) {
          console.log('[AddContentPage] Successfully fetched draft content');
          const data = (await response.json()) as ResourceContentResponse;
          item = transformResourceContentToItem(data);
          console.log('[AddContentPage] Transformed item:', { id: item.id, title: item.title });

          // Fetch related items
          try {
            const relatedResponse = await fetch(
              `${backendOrigin}/api/curation/related-items/?content=${editId}`,
              { headers, cache: 'no-store' }
            );

            if (relatedResponse.ok) {
              const relatedData = (await relatedResponse.json()) as
                | { results: Array<{ target_url: string; relation_type: number; relation_type_label: string }> }
                | Array<{ target_url: string; relation_type: number; relation_type_label: string }>;

              const relatedItems = 'results' in relatedData ? relatedData.results : relatedData;

              console.log('[AddContentPage] Fetched related items:', JSON.stringify(relatedItems, null, 2));

              item.related_works = relatedItems.map((rel) => ({
                type: { label: rel.relation_type_label || '', value: String(rel.relation_type) },
                link: rel.target_url,
              }));

              console.log('[AddContentPage] Mapped related_works:', JSON.stringify(item.related_works, null, 2));
            }
          } catch (e) {
            console.error('[AddContentPage] Error fetching related items:', e);
          }

          // Fetch community relations and populate item.communities
          try {
            const communitiesResponse = await fetch(
              `${backendOrigin}/api/curation/community-relations/?content=${editId}`,
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
          } catch (e) {
            console.error('[AddContentPage] Error fetching communities:', e);
          }
        } else {
          console.error('[AddContentPage] Failed to fetch draft:', response.status, response.statusText);
        }
      } else {
        console.log('[AddContentPage] No JWT token available');
      }
    } catch (e) {
      console.error('[AddContentPage] Error fetching draft:', e);
    }
  } else {
    console.log('[AddContentPage] No editId, showing add new content form');
  }

  const isEdit = !!item;
  console.log('[AddContentPage] isEdit:', isEdit, 'item:', !!item);

  try {
    return (
      <VFlex className={'flex-1 border-l border-primary'}>
        <div className={'border-b border-primary px-10 py-14 lg:px-14'}>
          <Text variant={'h2'}>{isEdit ? 'Edit Content' : 'Add New Content'}</Text>
        </div>
        <Suspense fallback={'Loading...'}>
          <AddContentData item={item} />
        </Suspense>
      </VFlex>
    );
  } catch (e) {
    console.log(e);
  }
  return null;
}
