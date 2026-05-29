import TopBar from '@/app/_parts/TopBar';
import React from 'react';

export const dynamic = 'force-dynamic';

export default function CommunitiesTopBar() {
  return <TopBar activePage={'community'} />;
}

export type CommunitiesTopBarProps = {
  params: {
    id: string;
    slug: string;
  };
};
