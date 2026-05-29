import React from 'react';
import { notFound, redirect, RedirectType } from 'next/navigation';
import { getItem, getRecommendations } from '@/lib/api/item';
import DetailsBody from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody';

type ItemDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function ItemDetails({
  params: { id, slug },
}: ItemDetails) {
  const [item, recommendations] = await Promise.all([
    getItem(id),
    getRecommendations(id),
  ]);

  if (!item) {
    notFound();
  } else if (item.slug !== slug) {
    redirect(`/items/${id}/${item.slug}`, RedirectType.replace);
  }

  return (
    <DetailsBody item={item} recommendedContent={recommendations.results} />
  );
}
