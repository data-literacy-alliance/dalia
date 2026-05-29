'use client';
import React, { FC, useState } from 'react';
import { VFlex } from '@/components/Flex';
import CommunitiesHeader from '@/app/(with-sidebar)/communities/[id]/[slug]/_parts/CommunitiesHeader';
import CommunitiesNavigationBar from '@/app/(with-sidebar)/communities/[id]/[slug]/_parts/CommunitiesNavigationBar';
import AllResults from '@/app/(with-sidebar)/communities/[id]/[slug]/_parts/AllResults';
import { CommunitiesTabs } from '@/app/(with-sidebar)/communities/[id]/[slug]/page';
import { Community } from '@/lib/types/Community';
import { ItemObject } from '@/lib/types/ItemTypes';

const CommunityBody: FC<CommunityBodyProps> = ({ community, items }) => {
  const [tab, setTab] = useState<CommunitiesTabs>('All Results');

  return (
    <VFlex className={'flex-1 border-l border-primary mb-1'}>
      <CommunitiesHeader
        followersCount={community.followers}
        likesCount={community.views}
        viewsCount={community.likes}
        description={community.about}
        title={community.title}
        socialMedias={community.social_media}
      />
      <CommunitiesNavigationBar activeTab={tab} setActiveTab={setTab} />
      {tab === 'Featured' ? (
        <div
          className={
            'grid sm:grid-cols-1 lg:grid-cols-2 auto-rows-min lg:my-10 lg:mx-16'
          }
        >
          {/*{dummyItems.map((item) => (*/}
          {/*  <FeaturedItems item={item} className={''} key={item.id} />*/}
          {/*))}*/}
        </div>
      ) : (
        tab === 'All Results' && <AllResults items={items} />
      )}
    </VFlex>
  );
};

export type CommunityBodyProps = {
  community: Community;
  items: ItemObject[];
};

export default CommunityBody;
