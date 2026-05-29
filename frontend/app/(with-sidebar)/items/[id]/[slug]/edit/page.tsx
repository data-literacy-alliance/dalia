import React, { Suspense } from 'react';
import { notFound, redirect, RedirectType } from 'next/navigation';
import { getItem } from '@/lib/api/item';
import { VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import AddContentData from '@/app/(with-sidebar)/items/new/_parts/AddContentData';

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
  const item = await getItem(id);

  if (!item) {
    notFound();
  } else if (item.slug !== slug) {
    redirect(`/items/${id}/${item.slug}`, RedirectType.replace);
  }

  return (
    <VFlex className={'flex-1 border-l border-primary'}>
      <div className={'border-b border-primary px-10 py-14 lg:px-14'}>
        <Text variant={'h2'}>Edit content</Text>
      </div>
      <Suspense fallback={'Loading...'}>
        <AddContentData item={item} />
      </Suspense>
    </VFlex>
  );
}
