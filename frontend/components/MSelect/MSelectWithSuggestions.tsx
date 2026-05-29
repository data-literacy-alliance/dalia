'use client';
import React, { FC, useMemo, useState } from 'react';
import MSelect2, { MSelect2Props } from '@/components/MSelect/MSelect2';
import { useNewSuggestions } from '@/lib/api/newSuggestions';

const MSelectWithSuggestions: FC<MSelectWithStaticSuggestionsProps> = ({
  suggestionKey,
  additionalSuggestionParams,
  ...props
}) => {
  const [openedOnce, setOpenedOnce] = useState(false);
  const [query, setQuery] = useState('');
  const searchParams = useMemo(
    () =>
      query
        ? new URLSearchParams({ ...additionalSuggestionParams, search: query })
        : new URLSearchParams(additionalSuggestionParams),
    [additionalSuggestionParams, query]
  );

  const { items, isLoading } = useNewSuggestions(
    openedOnce ? suggestionKey : null,
    searchParams
  );

  return (
    <MSelect2
      {...props}
      items={items}
      loading={isLoading || props.loading}
      onOpenChange={() => {
        setOpenedOnce(true);
      }}
      shouldFilter={false}
      query={query}
      onQueryChange={setQuery}
    />
  );
};

export type MSelectWithStaticSuggestionsProps = Omit<
  MSelect2Props,
  'items' | 'onOpenChange' | 'query' | 'onQueryChange'
> & {
  suggestionKey: string;
  additionalSuggestionParams?: Record<string, string>;
};

export default React.memo(MSelectWithSuggestions);
