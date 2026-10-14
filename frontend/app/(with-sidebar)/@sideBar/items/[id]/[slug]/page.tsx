import React from 'react';
import { notFound } from 'next/navigation';
import { getItem, getItemInteractions } from '@/lib/api/item';
import { getJWTTokenFromSession } from '@/lib/auth/serverAuth';
import DetailsSide from './_parts/DetailsSide';

type ItemDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function ItemDetails({ params: { id } }: ItemDetails) {
  const [item, authToken] = await Promise.all([getItem(id), getJWTTokenFromSession()]);

  if (!item) {
    notFound();
  }

  if (authToken) {
    const interactions = await getItemInteractions(id, authToken);
    if (interactions) {
      item.is_bookmarked = interactions.is_bookmarked;
      item.is_liked = interactions.is_liked;
    }
  }

  return <DetailsSide item={item} />;
}
