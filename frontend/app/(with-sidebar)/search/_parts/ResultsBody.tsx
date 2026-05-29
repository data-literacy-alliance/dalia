'use client';
import React, { FC } from 'react';

import styles from '@/app/(with-sidebar)/search/_parts/search.module.css';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import Item, { GridItem } from '@/components/Item';
import Pages from '@/app/_parts/Pages';
import { Pageable } from '@/lib/types/Common';
import { ItemObject } from '@/lib/types/ItemTypes';
import { Facet, SelectedFacet } from '@/lib/types/Filters';
import { useSearchParams } from 'next/navigation';
import useWindowDimensions, { ScreenSizes } from '@/lib/useWindowDimensions';
import AppliedFilters from '@/app/(with-sidebar)/search/_parts/AppliedFilters';

const ResultsBody: FC<ResultsBodyProps> = ({ query, results, selectedFacets }) => {
  const { width } = useWindowDimensions();
  const params = useSearchParams();
  const view =
    width < ScreenSizes.xl
      ? 'grid'
      : ((params.get('view') || 'list') as 'list' | 'grid');

  const totalPages = results ? Math.ceil(results.count / results.limit) : 0;
  const currentPage = results
    ? Math.floor(results.offset / results.limit) + 1
    : 0;

  return width === 0 ? (
    <Text className={'my-4 p-6'}>Getting the results...</Text>
  ) : results ? (
    <HFlex className={'w-full'}>
      <div className={'flex w-full'}>
        <VFlex className={'min-w-0 flex-1 lg:pe-5'}>
          <VFlex className={'gap-5 px-5 pb-7 pt-4'}>
            {results.results.length > 0 ? (
              <>
                <Text className={'hidden lg:inline'} variant={'h3'}>
                  {query && query !== '*' ? 'Search results for:' : 'Showing all items'}
                </Text>
                <div className={styles.searchInfo}>
                  {query && query !== '*' && <Text>{query}</Text>}
                  <Text>
                    Showing {results.results.length} out of {results.count}{' '}
                    results.
                  </Text>
                  <Text>
                    Page {currentPage} out of {totalPages}.
                  </Text>
                </div>

                {/* Display applied filters */}
                {results.facets && selectedFacets && (
                  <AppliedFilters
                    facets={results.facets}
                    selectedFacets={selectedFacets}
                  />
                )}
              </>
            ) : (
              <div className={styles.searchInfo}>No results found.</div>
            )}
          </VFlex>
          {view === 'list' ? (
            <VFlex className={'border-r border-t border-primary'}>
              {results.results.map((item) => (
                <Item
                  item={item}
                  key={item.id}
                  className={'border-b border-l'}
                />
              ))}
            </VFlex>
          ) : (
            <div
              className={
                'grid w-full grid-cols-1 flex-wrap border-l border-t border-primary xl:grid-cols-2 2xl:grid-cols-3'
              }
            >
              {results.results.map((item) => (
                <GridItem
                  item={item}
                  key={item.id}
                  noBorder
                  className={'w-full border-b border-primary lg:border-r'}
                />
              ))}
            </div>
          )}
          <Pages
            offset={results.offset}
            count={results.count}
            limit={results.limit}
          />
        </VFlex>
      </div>
    </HFlex>
  ) : null;
};

type ResultsBodyProps = {
  source?: 'basic' | 'advanced' | undefined;
  query?: string | undefined;
  results?: (Pageable<ItemObject> & { facets: Facet[] }) | null;
  selectedFacets?: SelectedFacet[];
};

export default ResultsBody;
