'use client';
import React, { FC, Suspense, useState } from 'react';
import { ChevronDownIcon, ChevronRightIcon } from 'lucide-react';
import SortBar from './_parts/SortBar';
import DateRangeFilter from './_parts/DateRangeFilter';
import Checkbox from '@/components/Checkbox';
import { Facet, FacetItem, SelectedFacet } from '@/lib/types/Filters';
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
import { NEXT_PUBLIC_API_URL } from '@/lib/settings.mjs';

const ResultsSide: FC<ResultsSideProps> = ({ facets, selectedFacets }) => {
  const { setSidebarOpen } = useMainContext();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  // childrenCache: children loaded without counts (on ▶ expand click)
  const [childrenCache, setChildrenCache] = useState<Record<string, FacetItem[]>>({});
  // childrenWithCounts: children loaded with full search params (on select)
  const [childrenWithCounts, setChildrenWithCounts] = useState<Record<string, FacetItem[]>>({});

  const categoriesHasSelected = facets.filter((facet) =>
    facet.facetItems.some(
      (facetItem) =>
        facetItem.active ||
        isFacetSelected(facetItem, facet.facetCategory.name, selectedFacets) ||
        (facetItem.children ?? []).some(
          (c) => c.active || isFacetSelected(c, facet.facetCategory.name, selectedFacets)
        )
    )
  );

  const toggleItem = (value: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  // Load children without counts — called on ▶ expand click
  const loadChildrenNoCount = async (parentValue: string) => {
    if (childrenCache[parentValue] !== undefined) return;
    try {
      const res = await fetch(
        `${NEXT_PUBLIC_API_URL}/disciplines/children/?parent=${encodeURIComponent(parentValue)}`,
        { credentials: 'include' }
      );
      if (res.ok) {
        const data = (await res.json()) as FacetItem[];
        setChildrenCache((prev) => ({ ...prev, [parentValue]: data }));
      }
    } catch {}
  };

  // Load children with full search context (counts) — called when parent is selected
  const loadChildrenWithCounts = async (
    parentValue: string,
    currentParams: URLSearchParams
  ) => {
    try {
      const p = new URLSearchParams(currentParams);
      const res = await fetch(
        `${NEXT_PUBLIC_API_URL}/disciplines/children/?parent=${encodeURIComponent(parentValue)}&${p.toString()}`,
        { credentials: 'include' }
      );
      if (res.ok) {
        const data = (await res.json()) as FacetItem[];
        setChildrenWithCounts((prev) => ({ ...prev, [parentValue]: data }));
      }
    } catch {}
  };

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
                  {(() => {
                    const hasFacetChildren = facet.facetItems.some(
                      (fi) => (fi.children ?? []).length > 0
                    );

                    return facet.facetItems.map((facetItem) => {
                      const checked =
                        facetItem.active ||
                        isFacetSelected(facetItem, facet.facetCategory.name, selectedFacets);

                      const hasActiveChild = (facetItem.children ?? []).some(
                        (c) =>
                          c.active ||
                          isFacetSelected(c, facet.facetCategory.name, selectedFacets)
                      );

                      const hasChildren = (facetItem.children ?? []).length > 0;
                      const isExpanded =
                        hasActiveChild || expandedItems.has(facetItem.value);

                      const hasResults = (facetItem.count ?? 0) > 0;
                      const label =
                        facetItem.count !== undefined && !isExpanded
                          ? `${facetItem.label} (${facetItem.count})`
                          : facetItem.label;

                      // Tree layout: activate when ANY item has children or hasChildren flag
                      const showAsTree = hasFacetChildren || facetItem.hasChildren;

                      if (showAsTree) {
                        const showToggle = hasChildren || facetItem.hasChildren;

                        // Parent is active (selected as filter)
                        const parentIsActive = checked;
                        // Show counts in children only when parent is selected
                        const showCount = parentIsActive;

                        // Determine what children to display:
                        // - If parent is active: prefer childrenWithCounts (have counts), fall back to childrenCache or pre-loaded
                        // - If parent is expanded but not active: use childrenCache (no counts) or pre-loaded
                        const displayChildren = parentIsActive
                          ? (childrenWithCounts[facetItem.value] ??
                              childrenCache[facetItem.value] ??
                              facetItem.children ??
                              [])
                          : (childrenCache[facetItem.value] ??
                              facetItem.children ??
                              []);

                        return (
                          <div key={`${facet.facetCategory.name}_${facetItem.value}`}>
                            <div className="flex items-center gap-1">
                              {showToggle ? (
                                <button
                                  onClick={() => {
                                    toggleItem(facetItem.value);
                                    void loadChildrenNoCount(facetItem.value);
                                  }}
                                  className="flex-shrink-0 text-gray-500 hover:text-gray-700"
                                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                                >
                                  {isExpanded ? (
                                    <ChevronDownIcon className="h-4 w-4" />
                                  ) : (
                                    <ChevronRightIcon className="h-4 w-4" />
                                  )}
                                </button>
                              ) : (
                                <span className="w-4 flex-shrink-0" />
                              )}
                              <Checkbox
                                label={label}
                                value={facetItem.value}
                                onCheckedChange={() => {
                                  changeFacet(facet.facetCategory.name, facetItem.value, !checked);
                                  // When selecting (becoming active), load children with counts
                                  if (!checked) {
                                    const updatedParams = new URLSearchParams(params);
                                    updatedParams.append(facet.facetCategory.name, facetItem.value);
                                    void loadChildrenWithCounts(facetItem.value, updatedParams);
                                  }
                                }}
                                checked={checked}
                                disabled={!hasResults && !checked && !hasActiveChild}
                                className={
                                  !hasResults && !checked && !hasActiveChild ? 'opacity-50' : ''
                                }
                              />
                            </div>
                            {showToggle && isExpanded && (
                              <div className="ml-5 mt-1 flex flex-col gap-1 border-l border-primary pl-3">
                                {displayChildren.map((child) => {
                                  const childChecked =
                                    child.active ||
                                    isFacetSelected(
                                      child,
                                      facet.facetCategory.name,
                                      selectedFacets
                                    );
                                  // Show count only when parent is an active filter
                                  const childLabel =
                                    showCount && child.count !== undefined
                                      ? `${child.label} (${child.count})`
                                      : child.label;
                                  return (
                                    <Checkbox
                                      key={`${facet.facetCategory.name}_${child.value}`}
                                      label={childLabel}
                                      value={child.value}
                                      onCheckedChange={() =>
                                        changeFacet(
                                          facet.facetCategory.name,
                                          child.value,
                                          !childChecked
                                        )
                                      }
                                      checked={childChecked}
                                    />
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      }

                      // Flat layout — all other facets
                      return (
                        <Checkbox
                          key={`${facet.facetCategory.name}_${facetItem.value}`}
                          label={label}
                          value={facetItem.value}
                          onCheckedChange={() =>
                            changeFacet(facet.facetCategory.name, facetItem.value, !checked)
                          }
                          checked={checked}
                          disabled={!hasResults && !checked}
                          className={!hasResults && !checked ? 'opacity-50' : ''}
                        />
                      );
                    });
                  })()}
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
