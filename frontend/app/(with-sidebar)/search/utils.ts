import { Pageable } from '@/lib/types/Common';
import { ResourceItem } from '@/lib/types/ItemTypes';
import { Facet, FacetItem, SelectedFacet } from '@/lib/types/Filters';
import { ResultsPageSize } from '@/lib/settings.mjs';
import { searchItems } from '@/lib/api/item';

export type ParsedFilters = {
  selectedFacets: SelectedFacet[];
  crossFacetOperators: ('AND' | 'OR')[];
};

const OP_PREFIX = '_op_';
const CROSS_OP_PREFIX = '_crossOp_';

export async function getResultsAndFacets(
  filters: Record<string, string>,
  query?: string,
  strOffset?: string,
  strLimit?: string,
  ssrHeaders?: Record<string, string>
): Promise<{
  results: (Pageable<ResourceItem> & { facets: Facet[] }) | null;
  selectedFacets: SelectedFacet[];
  crossFacetOperators: ('AND' | 'OR')[];
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

  const { selectedFacets, crossFacetOperators } = parseFilters(facetFilters);

  const results = await searchItems(
    query || '',
    offset,
    limit,
    selectedFacets,
    crossFacetOperators,
    'relevance',
    'dsc',
    datePublished_after,
    datePublished_before,
    ssrHeaders
  );

  return {
    results,
    selectedFacets,
    crossFacetOperators,
  };
}

export function parseFilters(
  filters: Record<string, string | string[]>
): ParsedFilters {
  const selectedFacets: SelectedFacet[] = [];
  const withinOpMap: Record<string, 'AND' | 'OR'> = {};
  const crossOpMap: Record<number, 'AND' | 'OR'> = {};

  for (const key in filters) {
    const value = filters[key];
    const strValue = Array.isArray(value) ? value[0] : value;

    if (key.startsWith(OP_PREFIX)) {
      const facetKey = key.slice(OP_PREFIX.length);
      if (strValue === 'AND' || strValue === 'OR') {
        withinOpMap[facetKey] = strValue;
      }
      continue;
    }

    if (key.startsWith(CROSS_OP_PREFIX)) {
      const idx = parseInt(key.slice(CROSS_OP_PREFIX.length), 10);
      if (!isNaN(idx) && (strValue === 'AND' || strValue === 'OR')) {
        crossOpMap[idx] = strValue;
      }
      continue;
    }

    // Skip empty values (existing logic)
    if (!value || (Array.isArray(value) && value.length === 0)) continue;
    if (typeof value === 'string' && value.trim() === '') continue;

    const selected = Array.isArray(value)
      ? value.filter((v) => v && v.trim() !== '')
      : [value];

    if (selected.length > 0) {
      selectedFacets.push({ key, selected });
    }
  }

  // Apply within-group operators
  selectedFacets.forEach((sf) => {
    if (withinOpMap[sf.key]) {
      sf.operator = withinOpMap[sf.key];
    }
  });

  // Build ordered cross-facet operators array
  const maxIdx = Object.keys(crossOpMap).length
    ? Math.max(...Object.keys(crossOpMap).map(Number))
    : -1;
  const crossFacetOperators: ('AND' | 'OR')[] = [];
  for (let i = 0; i <= maxIdx; i++) {
    crossFacetOperators.push(crossOpMap[i] ?? 'AND');
  }

  return { selectedFacets, crossFacetOperators };
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
