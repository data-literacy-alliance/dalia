import React from 'react';
import { notFound } from 'next/navigation';
import { getItem } from '@/lib/api/item';
import Button from '@/components/Button';
import { ScrollArea } from '@/components/ui/scroll-area';

type ItemDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function ItemDetails({ params: { id } }: ItemDetails) {
  const item = await getItem(id);

  if (!item) {
    notFound();
  }


  return (
    <div
      className={
        'sticky top-[4.5rem] mx-5 mb-1 h-[calc(100dvh-4.5rem)] overflow-auto border border-b-0 border-primary lg:mx-auto lg:border-0'
      }
    >
      <ScrollArea className={'h-full'}>
        <Button
          leadIcon={'arrow-left'}
          leftAligned
          borderless
          className={
            'min-h-12 w-full justify-start border-b border-primary lg:border-l lg:border-r'
          }
          link={{
            href: `/items/${id}/${item.slug}`
          }}
        >
          Go to Item
        </Button>
      </ScrollArea>
    </div>
  );
}
