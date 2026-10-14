import appFetch from '@/lib/api/fetch';
import { LabelValuePair, Pageable } from '@/lib/types/Common';
import { SuggestionLicense } from '@/lib/types/Suggestion';

/**
 * This is supposed to be used for LabelValue pairs with pagination
 */
export async function getSuggestionsWithPagination(
  key: 'communities' | 'languages' | 'file-formats' | 'keywords',
  query: string,
  limit: number = 10,
  offset: number = 0
) {
  const data = await appFetch(
    `/curation/suggest/${key}/?q=${query}&limit=${limit}&offset=${offset}`
  );

  if (!data?.ok) {
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return (await data.json()) as Pageable<LabelValuePair>;
}

export async function getLicenseSuggestions(
  query: string,
  limit: number = 10,
  offset: number = 0
) {
  const data = await appFetch(
    `/curation/suggest/licenses/?q=${query}&limit=${limit}&offset=${offset}`
  );

  if (!data?.ok) {
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return (await data.json()) as Pageable<SuggestionLicense>;
}
