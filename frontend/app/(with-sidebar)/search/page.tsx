import React, { FC, Suspense } from 'react';
import { cookies } from 'next/headers';
import { getResultsAndFacets } from '@/app/(with-sidebar)/search/utils';
import ResultsBody from '@/app/(with-sidebar)/search/_parts/ResultsBody';
import Text from '@/components/Text';

const SearchResultPage: FC<PageProps> = async ({
  searchParams: {
    query,
    source,
    offset: strOffset,
    limit: strLimit,
    view,
    ...filters
  },
}) => {
  const cookieStore = cookies();
  const cookieHeader = cookieStore.toString();
  const csrfToken = cookieStore.get('csrftoken')?.value;
  const ssrHeaders: Record<string, string> = {};
  if (cookieHeader) ssrHeaders['Cookie'] = cookieHeader;
  if (csrfToken) ssrHeaders['X-CSRFToken'] = csrfToken;

  const { results, selectedFacets } = await getResultsAndFacets(
    filters,
    query,
    strOffset,
    strLimit ?? (view === 'grid' ? '18' : '15'),
    Object.keys(ssrHeaders).length > 0 ? ssrHeaders : undefined
  );

  return (
    <Suspense fallback={<Text className={'my-4'}>Getting the results...</Text>}>
      <ResultsBody
        source={source}
        query={query}
        results={results}
        selectedFacets={selectedFacets}
      />
    </Suspense>
  );
};

export type PageProps = {
  searchParams: {
    offset?: string;
    limit?: string;
    query?: string;
    source?: 'basic' | 'advanced';
  } & Record<string, string>;
};

export default SearchResultPage;
