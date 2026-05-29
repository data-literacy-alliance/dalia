import { Pageable } from '@/lib/types/Common';
import { ResourceItem } from '@/lib/types/ItemTypes';
import { Facet, FacetItem, SelectedFacet } from '@/lib/types/Filters';
import { ResultsPageSize } from '@/lib/settings.mjs';
import { searchItems } from '@/lib/api/item';

export async function getResultsAndFacets(
  filters: Record<string, string>,
  query?: string,
  strOffset?: string,
  strLimit?: string
): Promise<{
  results: (Pageable<ResourceItem> & { facets: Facet[] }) | null;
  selectedFacets: SelectedFacet[];
}> {
  const offset = strOffset ? Number(strOffset) : 0;
  const limit = strLimit ? Number(strLimit) : ResultsPageSize;

  // Extract date filter parameters
  const datePublished_after = filters['datePublished_after'];
  const datePublished_before = filters['datePublished_before'];

  // Remove non-facet parameters from filters before parsing as facets
  // - datePublished_* are date range filters, not facets
  // - newFilter is UI state from advanced search dropdown
  // - source indicates search origin (basic/advanced)
  // - view is UI state for grid/list view
  const {
    datePublished_after: _after,
    datePublished_before: _before,
    newFilter: _newFilter,
    source: _source,
    view: _view,
    ...facetFilters
  } = filters;

  const selectedFacets = parseFilters(facetFilters);

  const results = await searchItems(
    query || '',
    offset,
    limit,
    selectedFacets,
    'relevance',
    'dsc',
    datePublished_after,
    datePublished_before
  );

  return {
    results: results,
    selectedFacets,
  };
}

export function parseFilters(
  filters: Record<string, string | string[]>
): SelectedFacet[] {
  const results: SelectedFacet[] = [];

  for (const filter in filters) {
    const value = filters[filter];

    // Skip empty values
    if (!value || (Array.isArray(value) && value.length === 0)) {
      continue;
    }
    if (typeof value === 'string' && value.trim() === '') {
      continue;
    }

    // Filter out empty strings from arrays
    const selected = Array.isArray(value)
      ? value.filter((v) => v && v.trim() !== '')
      : [value];

    // Only add if there are valid selections
    if (selected.length > 0) {
      results.push({
        key: filter,
        selected,
      });
    }
  }

  return results;
}

export function isFacetSelected(
  facet: FacetItem,
  key: string,
  selectedFacets: SelectedFacet[]
): boolean {
  const selectedValues = selectedFacets.find(
    (sFacet) => sFacet.key === key
  )?.selected;

  if (selectedValues) {
    return selectedValues.includes(facet.value);
  }

  return false;
}
