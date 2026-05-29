'use client';
import React, { FC } from 'react';
import { Facet, SelectedFacet } from '@/lib/types/Filters';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import { XIcon } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

/**
 * Display currently applied filters in a human-readable format
 * Example:
 *   Learning Resource Type: Course OR Tutorial
 *   AND
 *   Target Group: Bachelor Student OR Master's Student
 */
const AppliedFilters: FC<AppliedFiltersProps> = ({
  facets,
  selectedFacets,
}) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  // Filter out empty selections
  const activeFilters = selectedFacets.filter((sf) => sf.selected.length > 0);

  // Check for date filters
  const dateAfter = params.get('datePublished_after');
  const dateBefore = params.get('datePublished_before');
  const hasDateFilter = dateAfter || dateBefore;

  if (activeFilters.length === 0 && !hasDateFilter) {
    return null; // Don't show anything if no filters applied
  }

  // Build readable filter display
  const filterDisplay = activeFilters.map((selectedFacet, index) => {
    // Find the facet definition to get labels
    const facet = facets.find(
      (f) => f.facetCategory.name === selectedFacet.key
    );

    if (!facet) return null;

    // Get labels for selected values
    const selectedLabels = selectedFacet.selected
      .map((value) => {
        const item = facet.facetItems.find((fi) => fi.value === value);
        return item?.label;
      })
      .filter(Boolean);

    if (selectedLabels.length === 0) return null;

    return {
      category: facet.facetCategory.label,
      values: selectedLabels,
      key: selectedFacet.key,
    };
  }).filter(Boolean);

  // Remove a specific filter value
  const removeFilter = (categoryKey: string, valueToRemove: string) => {
    const newParams = new URLSearchParams(params);
    newParams.delete(categoryKey, valueToRemove);
    newParams.set('offset', '0'); // Reset pagination
    router.push(`${pathname}?${newParams.toString()}`);
  };

  // Clear all filters
  const clearAllFilters = () => {
    const newParams = new URLSearchParams(params);

    // Remove all filter params (keep query and other params)
    activeFilters.forEach((filter) => {
      newParams.delete(filter.key);
    });

    // Remove date filters
    newParams.delete('datePublished_after');
    newParams.delete('datePublished_before');

    newParams.set('offset', '0');
    router.push(`${pathname}?${newParams.toString()}`);
  };

  // Remove date filter
  const removeDateFilter = () => {
    const newParams = new URLSearchParams(params);
    newParams.delete('datePublished_after');
    newParams.delete('datePublished_before');
    newParams.set('offset', '0');
    router.push(`${pathname}?${newParams.toString()}`);
  };

  // Format date range text
  const getDateRangeText = () => {
    if (dateAfter && dateBefore) {
      return `${dateAfter} to ${dateBefore}`;
    } else if (dateAfter) {
      return `After ${dateAfter}`;
    } else if (dateBefore) {
      return `Before ${dateBefore}`;
    }
    return '';
  };

  return (
    <VFlex className="gap-3 rounded-lg border border-primary bg-gray-50 p-4">
      {/* Header with Clear All button */}
      <HFlex className="items-center justify-between">
        <Text variant="h4" className="font-semibold">
          Active Filters
        </Text>
        <button
          onClick={clearAllFilters}
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          Clear all
        </button>
      </HFlex>

      {/* Display filters with OR/AND logic */}
      <VFlex className="gap-2">
        {/* Date filter display */}
        {hasDateFilter && (
          <div key="publication_date">
            <HFlex className="flex-wrap items-center gap-2">
              <Text className="font-medium text-gray-700">
                Publication Date:
              </Text>
              <button
                onClick={removeDateFilter}
                className="inline-flex items-center gap-1 rounded-full border border-blue-300 bg-blue-100 px-3 py-1 text-sm text-blue-800 transition-colors hover:bg-blue-200"
              >
                <span>{getDateRangeText()}</span>
                <XIcon className="h-3 w-3" />
              </button>
            </HFlex>
          </div>
        )}

        {/* AND separator if both date and facet filters exist */}
        {hasDateFilter && filterDisplay.length > 0 && (
          <Text className="my-1 text-xs font-bold uppercase text-gray-500">
            AND
          </Text>
        )}

        {filterDisplay.map((filter, index) => (
          <div key={filter!.key}>
            {/* AND separator between categories */}
            {index > 0 && (
              <Text className="my-1 text-xs font-bold uppercase text-gray-500">
                AND
              </Text>
            )}

            {/* Category with values */}
            <HFlex className="flex-wrap items-center gap-2">
              <Text className="font-medium text-gray-700">
                {filter!.category}:
              </Text>

              {/* Display each value as a removable chip */}
              {filter!.values.map((value, valueIndex) => (
                <React.Fragment key={`${filter!.key}-${value}`}>
                  {/* OR separator between values in same category */}
                  {valueIndex > 0 && (
                    <Text className="text-xs font-semibold text-gray-400">
                      OR
                    </Text>
                  )}

                  {/* Filter chip */}
                  <button
                    onClick={() => {
                      // Find the original value to remove
                      const selectedFacet = selectedFacets.find(
                        (sf) => sf.key === filter!.key
                      );
                      const facet = facets.find(
                        (f) => f.facetCategory.name === filter!.key
                      );
                      const facetItem = facet?.facetItems.find(
                        (fi) => fi.label === value
                      );
                      if (facetItem) {
                        removeFilter(filter!.key, facetItem.value);
                      }
                    }}
                    className="inline-flex items-center gap-1 rounded-full border border-blue-300 bg-blue-100 px-3 py-1 text-sm text-blue-800 transition-colors hover:bg-blue-200"
                  >
                    <span>{value}</span>
                    <XIcon className="h-3 w-3" />
                  </button>
                </React.Fragment>
              ))}
            </HFlex>
          </div>
        ))}
      </VFlex>

      {/* Count of active filters */}
      <Text className="text-xs text-gray-500">
        {activeFilters.reduce((sum, f) => sum + f.selected.length, 0) + (hasDateFilter ? 1 : 0)}{' '}
        filter{activeFilters.reduce((sum, f) => sum + f.selected.length, 0) + (hasDateFilter ? 1 : 0) !== 1 ? 's' : ''} active
      </Text>
    </VFlex>
  );
};

export type AppliedFiltersProps = {
  facets: Facet[];
  selectedFacets: SelectedFacet[];
};

export default AppliedFilters;
