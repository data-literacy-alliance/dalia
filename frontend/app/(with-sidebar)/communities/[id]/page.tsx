import { redirect, RedirectType } from 'next/navigation';
import { getCommunity } from '@/lib/api/community';

type ItemId = {
  params: {
    id: string;
  };
};

export const dynamic = 'force-dynamic';

export default async function IdToSlugPage({ params: { id } }: ItemId) {
  const community = await getCommunity(id);

  redirect(`/communities/${id}/${community.slug}`, RedirectType.replace);
}
