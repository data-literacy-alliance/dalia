import React, { FC, Suspense } from 'react';
import { cookies } from 'next/headers';
import { getResultsAndFacets } from '@/app/(with-sidebar)/search/utils';
import ResultsBody from '@/app/(with-sidebar)/search/_parts/ResultsBody';
import Text from '@/components/Text';

const NewOnDaliaPage: FC<PageProps> = async ({
  searchParams: {
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

  const { results, selectedFacets, crossFacetOperators } = await getResultsAndFacets(
    filters,
    '',
    strOffset,
    strLimit ?? (view === 'grid' ? '18' : '15'),
    Object.keys(ssrHeaders).length > 0 ? ssrHeaders : undefined,
    'created'
  );

  return (
    <Suspense fallback={<Text className={'my-4'}>Getting the results...</Text>}>
      <ResultsBody
        results={results}
        selectedFacets={selectedFacets}
        crossFacetOperators={crossFacetOperators}
        headingText="Showing the latest items on DALIA"
        hideCountInfo
      />
    </Suspense>
  );
};

export type PageProps = {
  searchParams: {
    offset?: string;
    limit?: string;
  } & Record<string, string>;
};

export default NewOnDaliaPage;
