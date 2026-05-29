import React from 'react';
import { getItem } from '@/lib/api/item';
import DetailsSide from './_parts/DetailsSide';

type ItemDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function ItemDetails({ params: { id } }: ItemDetails) {
  const item = await getItem(id);

  return <DetailsSide item={item} />;
}
