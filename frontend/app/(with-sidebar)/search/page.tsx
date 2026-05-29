import React, { FC, Suspense } from 'react';
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
  const { results, selectedFacets } = await getResultsAndFacets(
    filters,
    query,
    strOffset,
    strLimit ?? (view === 'grid' ? '18' : '15')
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
