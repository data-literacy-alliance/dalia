import appFetch from '@/lib/api/fetch';
import { BasicSearchFilter } from '@/lib/types/Filters';

export async function getBasicSearchFilters() {
  const data = await appFetch(`/basic-search-filters/`);

  if (!data?.ok) {
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return data.json() as Promise<BasicSearchFilter[]>;
}
