import React, { FC } from 'react';
import TopBar from '@/app/_parts/TopBar';

export const dynamic = 'force-dynamic';

const SearchTopBar: FC<SearchTopBarProps> = ({ searchParams: { query } }) => {
  return (
    <TopBar
      activePage={'Basic Search'}
      query={query}
      smallUser
      showSearchInput
    />
  );
};

export type SearchTopBarProps = {
  searchParams: {
    offset?: string;
    limit?: string;
    query?: string;
    source?: 'basic' | 'advanced';
  } & Record<string, string>;
};

export default SearchTopBar;
