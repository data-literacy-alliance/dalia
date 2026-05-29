'use client';
import React, { FC, Suspense } from 'react';
import SortBar from './_parts/SortBar';
import DateRangeFilter from './_parts/DateRangeFilter';
import Checkbox from '@/components/Checkbox';
import { Facet, SelectedFacet } from '@/lib/types/Filters';
import { usePathname, useSearchParams } from 'next/navigation';
import { useRouter } from 'nextjs-toploader/app';
import { useMainContext } from '@/app/Providers';
import { isFacetSelected } from '@/app/(with-sidebar)/search/utils';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { VFlex } from '@/components/Flex';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const ResultsSide: FC<ResultsSideProps> = ({ facets, selectedFacets }) => {
  const { setSidebarOpen } = useMainContext();
  const categoriesHasSelected = facets.filter((facet) =>
    facet.facetItems.some(
      (facetItem) =>
        facetItem.active ||
        isFacetSelected(facetItem, facet.facetCategory.name, selectedFacets)
    )
  );

  // Check if any filters are active
  // const hasActiveFilters = selectedFacets.some((sf) => sf.selected.length > 0);

  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const changeFacet = (name: string, value: string, newChecked: boolean) => {
    const writeableRouter = new URLSearchParams(params);
    if (value || !newChecked) {
      writeableRouter.delete(name, value);
    }

    if (newChecked) {
      writeableRouter.append(name, value);
    }

    // reset page
    writeableRouter.set('offset', '0');

    setSidebarOpen(false);
    router.push(`${pathname}?${writeableRouter}`);
  };

  // Clear All Filters function - commented out for future use
  // const clearAllFilters = () => {
  //   const writeableRouter = new URLSearchParams(params);
  //
  //   // Remove all filter params (keep query and other non-filter params)
  //   facets.forEach((facet) => {
  //     writeableRouter.delete(facet.facetCategory.name);
  //   });
  //
  //   // Reset pagination
  //   writeableRouter.set('offset', '0');
  //
  //   setSidebarOpen(false);
  //   router.push(`${pathname}?${writeableRouter}`);
  // };

  return (
    <div
      className={cn(
        `sticky top-[4.5rem] mx-5 mb-1 h-[calc(100dvh-4.5rem)] overflow-auto border border-b-0 border-primary lg:mx-auto lg:border-0`
      )}
    >
      <ScrollArea className={'h-full'}>
        <div className={'hidden xl:block'}>
          <Suspense>
            <SortBar />
          </Suspense>
        </div>

        {/* Clear All Filters Button - commented out for future use */}
        {/* {hasActiveFilters && (
          <div className="border-b border-primary bg-gray-50 px-5 py-3">
            <button
              onClick={clearAllFilters}
              className="w-full rounded border border-blue-600 bg-white px-4 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50"
            >
              Clear All Filters
            </button>
          </div>
        )} */}

        <Accordion
          type={'multiple'}
          defaultValue={categoriesHasSelected.map(
            (facet) => facet.facetCategory.name
          )}
          className={'border-primary lg:border-x'}
        >
          {facets.map((facet) => (
            <AccordionItem
              value={facet.facetCategory.name}
              key={facet.facetCategory.name}
              className={'mt-px overflow-hidden first:mt-0'}
            >
              <AccordionTrigger
                className={
                  'flex h-12 flex-1 cursor-default items-center justify-between border-b border-primary px-5 leading-none outline-none'
                }
              >
                {facet.facetCategory.label}
              </AccordionTrigger>
              <AccordionContent className={'border-b border-primary'}>
                <VFlex className="gap-2 px-2 pb-2 pt-4">
                  {facet.facetItems.map((facetItem) => {
                    const checked =
                      facetItem.active ||
                      isFacetSelected(
                        facetItem,
                        facet.facetCategory.name,
                        selectedFacets
                      );

                    // Display count if available
                    const hasResults = (facetItem.count ?? 0) > 0;
                    const label = facetItem.count !== undefined
                      ? `${facetItem.label} (${facetItem.count})`
                      : facetItem.label;

                    return (
                      <Checkbox
                        key={`${facet.facetCategory.name}_${facetItem.value}`}
                        label={label}
                        value={facetItem.value}
                        onCheckedChange={() =>
                          changeFacet(
                            facet.facetCategory.name,
                            facetItem.value,
                            !checked
                          )
                        }
                        checked={checked}
                        disabled={!hasResults && !checked}
                        className={!hasResults && !checked ? 'opacity-50' : ''}
                      />
                    );
                  })}
                </VFlex>
              </AccordionContent>
            </AccordionItem>
          ))}

          {/* Publication Date Filter - Custom accordion item with date range picker */}
          <AccordionItem
            value="publication_date"
            className={'mt-px overflow-hidden first:mt-0'}
          >
            <AccordionTrigger
              className={
                'flex h-12 flex-1 cursor-default items-center justify-between border-b border-primary px-5 leading-none outline-none'
              }
            >
              Publication Date
            </AccordionTrigger>
            <AccordionContent className={'border-b border-primary'}>
              <DateRangeFilter />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </ScrollArea>
    </div>
  );
};

export type ResultsSideProps = {
  facets: Facet[];
  selectedFacets: SelectedFacet[];
};

export default ResultsSide;
