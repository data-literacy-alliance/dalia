import React from 'react';
import TopBar from '@/app/_parts/TopBar';

type ItemDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function ItemDetailsTopBar({}: ItemDetails) {
  return <TopBar />;
}
