'use client';
import React, { FC } from 'react';
import Pagination from '@/components/Pagination';
import { ResultsPageSize } from '@/lib/settings.mjs';
import useWritableSearchParams from '@/lib/useWritableSearchParams';

const Pages: FC<PagesProps> = ({ limit = ResultsPageSize, offset, count }) => {
  const params = useWritableSearchParams();

  params.delete('limit');
  params.delete('offset');

  const currentPage = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(count / limit);

  return count > 0 ? (
    <Pagination
      pageCount={pages}
      currentPage={currentPage}
      linkGenerator={(newPage) =>
        `?offset=${(newPage - 1) * limit}&limit=${limit}&${params.toString()}`
      }
    />
  ) : null;
};

type PagesProps = {
  limit: number;
  offset: number;
  count: number;
};

export default Pages;
