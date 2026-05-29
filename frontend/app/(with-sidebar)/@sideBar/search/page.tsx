import React from 'react';
import ResultsSide from './ResultsSide';
import { getResultsAndFacets } from '@/app/(with-sidebar)/search/utils';

export const dynamic = 'force-dynamic';

export default async function SearchTopBar({
  searchParams: {
    query,
    source,
    offset: strOffset,
    limit: strLimit,
    ...filters
  },
}: PageProps) {
  const { results, selectedFacets } = await getResultsAndFacets(
    filters,
    query,
    strOffset,
    strLimit
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
    query?: string;
    source?: 'basic' | 'advanced';
  } & Record<string, string>;
};
