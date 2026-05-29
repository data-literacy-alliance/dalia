import { getItem } from '@/lib/api/item';
import { redirect, RedirectType } from 'next/navigation';

type ItemId = {
  params: {
    id: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function IdToSlugPage({ params: { id } }: ItemId) {
  const item = await getItem(id);

  redirect(`/items/${id}/${item.slug}`, RedirectType.replace);
}
