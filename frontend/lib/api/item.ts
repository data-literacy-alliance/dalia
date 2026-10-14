import { ItemObject, ResourceItem } from '@/lib/types/ItemTypes';
import appFetch from '@/lib/api/fetch';
import { Pageable } from '@/lib/types/Common';
import { Facet, SelectedFacet } from '@/lib/types/Filters';
import { NEXT_PUBLIC_BACKEND_ROOT, NEXT_PUBLIC_API_URL } from '@/lib/settings.mjs';
import { getCsrfTokenClient } from '@/lib/auth/csrfToken';

export async function getItem(id: string): Promise<ItemObject | null> {
  const data = await appFetch(`/items/${id}/`);

  if (data?.status === 404) {
    return null;
  }

  if (!data?.ok) {
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return data.json() as Promise<ItemObject>;
}

export async function getRecommendations(_id: string) {
  const backendBase = process.env.BACKEND_URL
    ? new URL(process.env.BACKEND_URL).origin
    : NEXT_PUBLIC_API_URL
      ? new URL(NEXT_PUBLIC_API_URL).origin
      : '';

  if (!backendBase) {
    return { results: [] as ItemObject[] };
  }

  const data = await appFetch(
    `${backendBase}/api/dalia/recommendation/v1/item/${_id}/recommendations`
  );

  if (!data?.ok) {
    return { results: [] as ItemObject[] };
  }

  return (await data.json()) as { results: ItemObject[] };
}

export async function searchItems(
  query: string,
  offset: number,
  limit: number,
  selectedFacets: SelectedFacet[] = [],
  crossFacetOperators: ('AND' | 'OR')[] = [],
  sortBy: 'relevance' | 'created' = 'relevance',
  sortOrder: 'asc' | 'dsc' = 'dsc',
  datePublished_after?: string,
  datePublished_before?: string,
  extraHeaders?: Record<string, string>
) {
  // Empty query should be replaced with "*" to get all results
  const normalizedQuery = query.trim() || '*';

  const requestBody = {
    query: normalizedQuery,
    offset,
    limit,
    selectedFacets,
    crossFacetOperators,
    sortBy,
    sortOrder,
    ...(datePublished_after && { datePublished_after }),
    ...(datePublished_before && { datePublished_before }),
  };

  // Log request for debugging
  console.log('[searchItems] Request:', JSON.stringify(requestBody, null, 2));

  const data = await appFetch('/items/', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...extraHeaders,
    },
    body: JSON.stringify(requestBody),
  });

  if (!data?.ok) {
    // Try to get error details from response body
    let errorDetails = '';
    try {
      const errorBody = await data.text();
      errorDetails = errorBody.substring(0, 500); // Limit to 500 chars
      console.error('[searchItems] Error response:', errorDetails);
    } catch {
      // Ignore parse errors
    }
    console.error('[searchItems] Request failed:', {
      status: data.status,
      statusText: data.statusText,
      url: data.url,
      requestBody,
    });
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return data.json() as Promise<
    Pageable<ItemObject> & {
      facets: Facet[];
    }
  >;
}

// Type for the backend ResourceContent response (based on actual API)
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
  keywords?: string[];
  resource_uuid?: string;
  resource?: {
    id: number;
    uuid: string;
    title: string;
  };
  submitted_for_review?: boolean;
  version?: number;
  version_label?: string;
  is_active?: boolean;
  size_mb: string | null;
  created: string;
  modified: string;
  community_relations?: Array<{
    community: { id: number; uuid: string; title: string };
    relation_type_code: string;
  }>;
  related_items?: Array<{
    target_url: string;
    relation_type: { label: string; value: string };
  }>;
  links?: string[];
};

// Transform ResourceContent to ResourceItem format
function transformResourceContentToItem(content: ResourceContentResponse): ResourceItem {
  try {
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
      communities: Array.isArray(content.community_relations) && content.community_relations.length > 0
        ? content.community_relations.map((rel) => ({
            id: rel.community.uuid,
            slug: '',
            title: rel.community.title,
            image: '',
            url: '',
            about: '',
            likes: 0,
            views: 0,
            followers: 0,
            is_supporting: rel.relation_type_code === 'supporting',
            is_recommending: rel.relation_type_code === 'recommending',
          }))
        : null,
      likes: 0,
      views: 0,
      comments: 0,
      tags: Array.isArray(content.keywords) ? content.keywords : [],
      related_works: Array.isArray(content.related_items)
        ? content.related_items.map((item) => ({
            type: item.relation_type,
            link: item.target_url,
          }))
        : [],
      learning_resource_types: Array.isArray(content.learning_resource_types)
        ? content.learning_resource_types.map((t) => ({
            label: t.label || '',
            value: t.slug || String(t.id),
          }))
        : [],
      media_types: Array.isArray(content.media_types)
        ? content.media_types.map((t) => ({
            label: t.label || '',
            value: t.slug || String(t.id),
          }))
        : [],
      disciplines: Array.isArray(content.disciplines)
        ? content.disciplines.map((d) => ({
            label: d.label || '',
            value: d.slug || String(d.id),
          }))
        : [],
      target_groups: Array.isArray(content.target_groups)
        ? content.target_groups.map((t) => ({
            label: t.label || '',
            value: t.slug || String(t.id),
          }))
        : [],
      proficiency_levels: Array.isArray(content.proficiency_levels)
        ? content.proficiency_levels.map((p) => ({
            label: p.label || '',
            value: p.slug || String(p.id),
          }))
        : [],
      format: Array.isArray(content.file_formats)
        ? content.file_formats.map((f) => (f.label || '').replace(/^\.+/, '').toUpperCase()).filter(Boolean).join(', ') || 'Unknown'
        : 'Unknown',
      license: Array.isArray(content.licenses) && content.licenses[0]
        ? {
            id: content.licenses[0].spdx_id || content.licenses[0].label || '',
            name: content.licenses[0].label || '',
            link: '', // API doesn't provide link field
          }
        : { id: '', name: '', link: '' },
      publication_date: content.publication_date || '',
      links: Array.isArray(content.links) ? content.links : [],
      languages: Array.isArray(content.languages)
        ? content.languages.map((l) => l.label || l.code || '').filter(Boolean)
        : [],
      resource_uuid: content.resource_uuid || content.resource?.uuid,
      file_size: content.size_mb ? `${content.size_mb} MB` : undefined,
      submitted_for_review: content.submitted_for_review,
      version: content.version_label || (content.version != null ? String(content.version) : undefined),
      is_active: content.is_active,
    };
  } catch (error) {
    console.error('[transformResourceContentToItem] Error transforming item:', error, content);
    // Return minimal valid item on error
    const fallbackLicense = Array.isArray(content.licenses) && content.licenses[0]
      ? {
          id: content.licenses[0].spdx_id || content.licenses[0].label || '',
          name: content.licenses[0].label || '',
          link: '',
        }
      : { id: '', name: '', link: '' };

    const fallbackLanguages = Array.isArray(content.languages)
      ? content.languages.map((l) => l.label || l.code || '').filter(Boolean)
      : [];

    return {
      id: content.uuid || String(content.id),
      slug: content.uuid || String(content.id),
      resource_uuid: undefined,
      title: content.title || 'Error loading item',
      url: content.main_url || '',
      description: content.description || '',
      authors: [],
      communities: null,
      likes: 0,
      views: 0,
      comments: 0,
      tags: [],
      related_works: [],
      learning_resource_types: [],
      media_types: [],
      disciplines: [],
      target_groups: [],
      proficiency_levels: [],
      format: 'Unknown',
      license: fallbackLicense,
      publication_date: '',
      links: [],
      languages: fallbackLanguages,
    };
  }
}

export async function getUserContributions(
  accessKey: string | undefined,
  csrfToken: string | undefined,
  filter: 'my-resources' | 'pending' | 'published' | 'archived' | 'unpublished' | 'all-resources' | 'all' = 'my-resources',
  showAll: boolean = false,
  page: number = 1
) {
  try {
    // If no access key, try session-based auth
    const headers: Record<string, string> = {};
    if (accessKey) {
      headers['Authorization'] = `Bearer ${accessKey}`;
    }
    // Add CSRF token for session authentication
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    // Build URL with filter parameter.
    // Server-side: derive base from BACKEND_URL (http://web:8000/...) so we use the internal
    // container hostname, not NEXT_PUBLIC_BACKEND_ROOT which is baked as http://localhost:7087.
    // Client-side: NEXT_PUBLIC_BACKEND_ROOT is correct (the public host).
    const backendBase =
      typeof window === 'undefined' && process.env.BACKEND_URL
        ? new URL(process.env.BACKEND_URL).origin
        : NEXT_PUBLIC_BACKEND_ROOT;
    const url = new URL(`${backendBase}/api/curation/resource-contents/`);
    if (filter && filter !== 'all') {
      url.searchParams.append('filter', filter);
    }
    // Add show_all parameter for admin/curation view (curators/superusers only)
    // Note: all-resources is handled as a regular filter value, not via show_all
    if (showAll && filter !== 'all-resources') {
      url.searchParams.append('show_all', 'true');
    }
    url.searchParams.append('page', String(page));

    console.log('[getUserContributions] Calling API with:', {
      hasAccessKey: !!accessKey,
      hasCsrfToken: !!csrfToken,
      willUseSessionAuth: !accessKey,
      url: url.toString(),
      filter,
      showAll,
    });

    const data = await fetch(url.toString(), {
      credentials: 'include', // Include cookies for session auth
      headers,
    });

    if (!data?.ok) {
      console.error('[getUserContributions] HTTP Error:', {
        status: data.status,
        statusText: data.statusText,
        url: data.url,
      });
      return { results: [] };
    }

    const responseText = await data.text();
    console.log('[getUserContributions] Raw response text (first 500 chars):', responseText.substring(0, 500));

    let response: ResourceContentResponse[] | { results: ResourceContentResponse[]; count?: number; next?: string | null; previous?: string | null } | Record<string, unknown>;

    try {
      response = JSON.parse(responseText) as
        | ResourceContentResponse[]
        | { results: ResourceContentResponse[]; count?: number; next?: string | null; previous?: string | null }
        | Record<string, unknown>;
    } catch (e) {
      console.error('[getUserContributions] Failed to parse JSON:', e);
      return { results: [] };
    }

    console.log('[getUserContributions] Parsed response:', {
      type: typeof response,
      isArray: Array.isArray(response),
      hasResults: 'results' in response,
      length: Array.isArray(response) ? response.length : ('results' in response && Array.isArray(response.results) ? response.results.length : 0),
      keys: response && typeof response === 'object' ? Object.keys(response) : [],
      sampleData: Array.isArray(response)
        ? response[0]
        : (response && typeof response === 'object' && 'results' in response && Array.isArray(response.results)
          ? (response.results as ResourceContentResponse[])[0]
          : response),
    });

    // Handle both paginated and non-paginated responses
    let rawResults: ResourceContentResponse[] = [];
    let count: number;
    let next: string | null = null;
    let previous: string | null = null;

    if (Array.isArray(response)) {
      rawResults = response;
      count = response.length;
    } else if (
      response &&
      typeof response === 'object' &&
      'results' in response &&
      Array.isArray(response.results)
    ) {
      const paginatedResponse = response as { results: ResourceContentResponse[]; count?: number; next?: string | null; previous?: string | null };
      rawResults = paginatedResponse.results;
      count = paginatedResponse.count ?? rawResults.length;
      next = paginatedResponse.next ?? null;
      previous = paginatedResponse.previous ?? null;
    } else {
      console.error('[getUserContributions] Unexpected response format:', response);
      return { results: [], count: 0, next: null, previous: null };
    }

    console.log('[getUserContributions] Found items:', rawResults.length);

    // Transform ResourceContent objects to ResourceItem format
    const results = rawResults.map(transformResourceContentToItem);

    return { results, count, next, previous };
  } catch (error) {
    console.error('[getUserContributions] Error:', error);
    return { results: [], count: 0, next: null, previous: null };
  }
}

export async function toggleBookmark(resourceId: string): Promise<{ bookmarked: boolean }> {
  const csrfToken = getCsrfTokenClient();
  const res = await fetch(`${NEXT_PUBLIC_API_URL}/items/${resourceId}/bookmark/`, {
    method: 'POST',
    credentials: 'include',
    headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json() as Promise<{ bookmarked: boolean }>;
}

export async function toggleLike(resourceId: string): Promise<{ liked: boolean }> {
  const csrfToken = getCsrfTokenClient();
  const res = await fetch(`${NEXT_PUBLIC_API_URL}/items/${resourceId}/like/`, {
    method: 'POST',
    credentials: 'include',
    headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json() as Promise<{ liked: boolean }>;
}

export async function getUserBookmarks(
  accessKey: string | undefined,
  csrfToken: string | undefined,
  page = 1
): Promise<{ results: ItemObject[]; count: number; next: string | null; previous: string | null }> {
  try {
    const headers: Record<string, string> = {};
    if (accessKey) headers['Authorization'] = `Bearer ${accessKey}`;
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    const isServer = typeof window === 'undefined';
    const backendBase =
      isServer && process.env.BACKEND_URL
        ? new URL(process.env.BACKEND_URL).origin
        : NEXT_PUBLIC_BACKEND_ROOT;
    const url = new URL(`${backendBase}/api/dalia/v1/activities/bookmarks/`);
    url.searchParams.append('page', String(page));
    const data = await fetch(url.toString(), { credentials: 'include', headers });
    if (data.status === 401) throw new Error('AUTH_EXPIRED');
    if (!data?.ok) return { results: [], count: 0, next: null, previous: null };
    const response = (await data.json()) as {
      results: ItemObject[];
      count: number;
      next: string | null;
      previous: string | null;
    };
    return {
      results: response.results,
      count: response.count,
      next: response.next,
      previous: response.previous,
    };
  } catch (e) {
    if (e instanceof Error && e.message === 'AUTH_EXPIRED') throw e;
    return { results: [], count: 0, next: null, previous: null };
  }
}

export async function getUserLikes(
  accessKey: string | undefined,
  csrfToken: string | undefined,
  page = 1
): Promise<{ results: ItemObject[]; count: number; next: string | null; previous: string | null }> {
  try {
    const headers: Record<string, string> = {};
    if (accessKey) headers['Authorization'] = `Bearer ${accessKey}`;
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    const isServer = typeof window === 'undefined';
    const backendBase =
      isServer && process.env.BACKEND_URL
        ? new URL(process.env.BACKEND_URL).origin
        : NEXT_PUBLIC_BACKEND_ROOT;
    const url = new URL(`${backendBase}/api/dalia/v1/activities/likes/`);
    url.searchParams.append('page', String(page));
    const data = await fetch(url.toString(), { credentials: 'include', headers });
    if (data.status === 401) throw new Error('AUTH_EXPIRED');
    if (!data?.ok) return { results: [], count: 0, next: null, previous: null };
    const response = (await data.json()) as {
      results: ItemObject[];
      count: number;
      next: string | null;
      previous: string | null;
    };
    return {
      results: response.results,
      count: response.count,
      next: response.next,
      previous: response.previous,
    };
  } catch (e) {
    if (e instanceof Error && e.message === 'AUTH_EXPIRED') throw e;
    return { results: [], count: 0, next: null, previous: null };
  }
}

export async function getItemInteractions(
  resourceId: string,
  accessKey?: string
): Promise<{ is_bookmarked: boolean; is_liked: boolean; likes: number } | null> {
  try {
    const isServer = typeof window === 'undefined';
    const backendBase =
      isServer && process.env.BACKEND_URL
        ? new URL(process.env.BACKEND_URL).origin
        : NEXT_PUBLIC_BACKEND_ROOT;
    const url = `${backendBase}/api/dalia/v1/items/${resourceId}/interactions/`;
    const headers: Record<string, string> = {};
    if (accessKey) headers['Authorization'] = `Bearer ${accessKey}`;
    const res = await fetch(url, { credentials: 'include', headers, cache: 'no-store' });
    if (!res.ok) return null;
    return res.json() as Promise<{ is_bookmarked: boolean; is_liked: boolean; likes: number }>;
  } catch {
    return null;
  }
}

export async function softDeleteResource(
  uuid: string,
  accessKey: string,
  csrfToken: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(
      `${NEXT_PUBLIC_BACKEND_ROOT}/api/curation/resource-contents/${uuid}/soft-delete/`,
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessKey}`,
          'X-CSRFToken': csrfToken,
        },
      }
    );

    if (!response.ok) {
      const errorData = (await response.json().catch(() => ({}))) as {
        detail?: string;
      };
      return {
        success: false,
        error: errorData.detail || 'Failed to delete resource',
      };
    }

    return { success: true };
  } catch (error) {
    console.error('[softDeleteResource] Error:', error);
    return {
      success: false,
      error: 'An error occurred while deleting the resource',
    };
  }
}
