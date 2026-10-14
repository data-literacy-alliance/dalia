import React from 'react';
import ResultsSide from '@/app/(with-sidebar)/@sideBar/search/ResultsSide';
import { getResultsAndFacets } from '@/app/(with-sidebar)/search/utils';

export const dynamic = 'force-dynamic';

export default async function NewOnDaliaSideBar({
  searchParams: { offset: strOffset, limit: strLimit, ...filters },
}: PageProps) {
  const { results, selectedFacets } = await getResultsAndFacets(
    filters,
    '',
    strOffset,
    strLimit,
    undefined,
    'created'
  );

  return (
    <ResultsSide
      facets={results?.facets ?? []}
      selectedFacets={selectedFacets}
    />
  );
}

export type PageProps = {
  searchParams: {
    offset?: string;
    limit?: string;
  } & Record<string, string>;
};
