import CommunityBody from '@/app/(with-sidebar)/communities/[id]/[slug]/_parts/CommunityBody';
import { getCommunity, getCommunityItems } from '@/lib/api/community';
import { notFound, redirect, RedirectType } from 'next/navigation';

export type CommunitiesTabs = 'Featured' | 'All Results' | 'Members';
export const dynamic = 'force-dynamic';

type CommunityDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export default async function Communities({
  params: { id, slug },
}: CommunityDetails) {
  const community = await getCommunity(id);
  const communityItems = await getCommunityItems(id);

  if (!community) {
    notFound();
  } else if (community.slug !== slug) {
    redirect(`/communities/${id}/${community.slug}`, RedirectType.replace);
  }

  return <CommunityBody community={community} items={communityItems} />;
}
