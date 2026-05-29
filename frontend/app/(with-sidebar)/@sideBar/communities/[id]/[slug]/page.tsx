import { getCommunity } from '@/lib/api/community';
import CommunitiesSide from './_parts/CommunitiesSide';
import React from 'react';
export const dynamic = 'force-dynamic';

type CommunityDetails = {
  params: {
    id: string;
    slug: string;
  };
};

export default async function Communities({
  params: { id },
}: CommunityDetails) {
  const community = await getCommunity(id);

  return <CommunitiesSide community={community} />;
}
