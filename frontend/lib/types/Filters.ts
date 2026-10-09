export type BasicSearchFilter = {
  key: {
    label: string;
    name: string;
  };
  values: {
    label: string;
    value: string;
  }[];
};

export type FacetCategory = {
  label: string;
  name: string;
};

export type FacetItem = {
  label: string;
  value: string;
  active: boolean;
  count?: number; // Number of results with this facet value
  children?: FacetItem[];
  hasChildren?: boolean;
};

export type Facet = {
  facetCategory: FacetCategory;
  facetItems: FacetItem[];
};

export type SelectedFacet = {
  key: string;
  selected: string[];
  operator?: 'AND' | 'OR';  // within-group operator, default 'OR'
};
