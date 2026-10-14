'use client';
import React, { FC } from 'react';
import { Facet, SelectedFacet } from '@/lib/types/Filters';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import { XIcon } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

const OP_PREFIX = '_op_';
const CROSS_OP_PREFIX = '_crossOp_';

const OperatorToggle = ({
  value,
  onChange,
}: {
  value: 'AND' | 'OR';
  onChange: (next: 'AND' | 'OR') => void;
}) => (
  <span className="inline-flex overflow-hidden rounded border border-gray-300 text-xs font-semibold">
    <button
      onClick={() => onChange('AND')}
      className={`px-2 py-0.5 transition-colors ${
        value === 'AND'
          ? 'bg-gray-800 text-white'
          : 'bg-white text-gray-400 hover:text-gray-600'
      }`}
    >
      AND
    </button>
    <button
      onClick={() => onChange('OR')}
      className={`border-l border-gray-300 px-2 py-0.5 transition-colors ${
        value === 'OR'
          ? 'bg-gray-800 text-white'
          : 'bg-white text-gray-400 hover:text-gray-600'
      }`}
    >
      OR
    </button>
  </span>
);

/**
 * Display currently applied filters in a human-readable format with AND/OR operator toggles.
 * Example:
 *   Learning Resource Type: [AND][OR] Course OR Tutorial
 *   [AND]
 *   Target Group: [AND][OR] Bachelor Student OR Master's Student
 */
const AppliedFilters: FC<AppliedFiltersProps> = ({
  facets,
  selectedFacets,
  crossFacetOperators,
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
    return null;
  }

  // Build readable filter display
  const filterDisplay = activeFilters
    .map((selectedFacet) => {
      const facet = facets.find(
        (f) => f.facetCategory.name === selectedFacet.key
      );

      if (!facet) return null;

      const selectedLabels = selectedFacet.selected
        .map((value) => {
          const item =
            facet.facetItems.find((fi) => fi.value === value) ??
            facet.facetItems
              .flatMap((fi) => fi.children ?? [])
              .find((c) => c.value === value);
          return item?.label;
        })
        .filter((l): l is string => Boolean(l));

      if (selectedLabels.length === 0) return null;

      return {
        category: facet.facetCategory.label,
        values: selectedLabels,
        key: selectedFacet.key,
        operator: selectedFacet.operator ?? 'OR',
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  // Toggle within-group operator for a facet key
  const toggleWithinOp = (facetKey: string, desired: 'AND' | 'OR') => {
    const newParams = new URLSearchParams(params);
    if (desired === 'OR') {
      newParams.delete(`${OP_PREFIX}${facetKey}`);  // OR is default, clean up
    } else {
      newParams.set(`${OP_PREFIX}${facetKey}`, desired);
    }
    newParams.set('offset', '0');
    router.push(`${pathname}?${newParams.toString()}`);
  };

  // Toggle cross-facet operator at index i (between row i and row i+1)
  const toggleCrossOp = (index: number, desired: 'AND' | 'OR') => {
    const newParams = new URLSearchParams(params);
    if (desired === 'AND') {
      newParams.delete(`${CROSS_OP_PREFIX}${index}`);  // AND is default
    } else {
      newParams.set(`${CROSS_OP_PREFIX}${index}`, desired);
    }
    newParams.set('offset', '0');
    router.push(`${pathname}?${newParams.toString()}`);
  };

  // Remove a specific filter value
  const removeFilter = (categoryKey: string, valueToRemove: string) => {
    const newParams = new URLSearchParams(params);
    newParams.delete(categoryKey, valueToRemove);
    newParams.set('offset', '0');
    router.push(`${pathname}?${newParams.toString()}`);
  };

  // Clear all filters (including operator params)
  const clearAllFilters = () => {
    const newParams = new URLSearchParams(params);

    activeFilters.forEach((filter) => {
      newParams.delete(filter.key);
      newParams.delete(`${OP_PREFIX}${filter.key}`);
    });

    for (let i = 0; i < crossFacetOperators.length; i++) {
      newParams.delete(`${CROSS_OP_PREFIX}${i}`);
    }

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

  // Build boolean formula string for display
  const buildFormula = (): string => {
    const parts = filterDisplay.map((filter) => {
      const op = filter.operator;
      const joined = filter.values.join(` ${op} `);
      return filter.values.length > 1 ? `(${joined})` : joined;
    });

    const allParts: string[] = [];
    if (hasDateFilter) allParts.push(getDateRangeText());
    allParts.push(...parts.filter(Boolean));

    return allParts.reduce((acc, part, i) => {
      if (i === 0) return part;
      // Between date filter and first facet row: always AND
      if (hasDateFilter && i === 1) return `${acc} AND ${part}`;
      // Between subsequent facet rows: use crossFacetOperators indexed by facet position
      const facetIdx = hasDateFilter ? i - 2 : i - 1;
      const crossOp = crossFacetOperators[facetIdx] ?? 'AND';
      return `${acc} ${crossOp} ${part}`;
    }, '');
  };

  const formula = buildFormula();
  const totalCount =
    activeFilters.reduce((sum, f) => sum + f.selected.length, 0) +
    (hasDateFilter ? 1 : 0);

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

      {/* Display filters with operator toggles */}
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

        {/* Static AND between date filter and first facet row */}
        {hasDateFilter && filterDisplay.length > 0 && (
          <Text className="my-1 text-xs font-bold uppercase text-gray-500">
            AND
          </Text>
        )}

        {filterDisplay.map((filter, index) => (
          <div key={filter.key}>
            {/* Cross-facet operator toggle between adjacent facet rows */}
            {index > 0 && (
              <HFlex className="my-1 items-center gap-2">
                <OperatorToggle
                  value={crossFacetOperators[index - 1] ?? 'AND'}
                  onChange={(next) => toggleCrossOp(index - 1, next)}
                />
              </HFlex>
            )}

            {/* Category label + within-group toggle + value chips */}
            <HFlex className="flex-wrap items-center gap-2">
              <Text className="font-medium text-gray-700">
                {filter.category}:
              </Text>

              {/* Within-group operator toggle — shown only when ≥2 values selected */}
              {filter.values.length >= 2 && (
                <OperatorToggle
                  value={filter.operator}
                  onChange={(next) => toggleWithinOp(filter.key, next)}
                />
              )}

              {/* Value chips with operator text between them */}
              {filter.values.map((value, valueIndex) => (
                <React.Fragment key={`${filter.key}-${value}`}>
                  {valueIndex > 0 && (
                    <Text className="text-xs font-semibold text-gray-400">
                      {filter.operator}
                    </Text>
                  )}

                  <button
                    onClick={() => {
                      const facet = facets.find(
                        (f) => f.facetCategory.name === filter.key
                      );
                      const facetItem =
                        facet?.facetItems.find((fi) => fi.label === value) ??
                        facet?.facetItems
                          .flatMap((fi) => fi.children ?? [])
                          .find((c) => c.label === value);
                      if (facetItem) {
                        removeFilter(filter.key, facetItem.value);
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

      {/* Count of active filters + boolean formula */}
      <Text className="text-xs text-gray-500">
        {totalCount} filter{totalCount !== 1 ? 's' : ''} active
        {formula && (
          <span className="ml-1 text-gray-400">— {formula}</span>
        )}
      </Text>
    </VFlex>
  );
};

export type AppliedFiltersProps = {
  facets: Facet[];
  selectedFacets: SelectedFacet[];
  crossFacetOperators: ('AND' | 'OR')[];
};

export default AppliedFilters;
