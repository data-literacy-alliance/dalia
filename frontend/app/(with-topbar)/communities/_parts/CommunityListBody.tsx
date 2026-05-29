'use client';

import React, { FC } from 'react';
import Text from '@/components/Text';
import Link from 'next/link';
import { LabelValuePair } from '@/lib/types/Common';
import { UsersIcon } from 'lucide-react';

const CommunityListBody: FC<CommunityListBodyProps> = ({ communities }) => {
  // using new API
  // const { communities, isLoading } = useCommunities();

  return (
    <div className={'mx-auto w-full'}>
      <Text variant={'h4'} className={'block text-center'}>
        Communities in DALIA
      </Text>
      <div
        className={
          'mt-6 grid grid-cols-1 gap-4 p-2 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6'
        }
      >
        {/*{isLoading ? (*/}
        {/*  <div className={'flex gap-2'}>*/}
        {/*    <Spinner /> Loading...*/}
        {/*  </div>*/}
        {/*) : (*/}
        {/*  communities.map((community) => (*/}
        {/*    <Link href={`/communities/${community.uuid}`} key={community.id} className={'border hover:bg-daliaGray-200 border-primary p-2'}>*/}
        {/*      <div>{community.title}</div>*/}
        {/*    </Link>*/}
        {/*)}*/}
        {communities.map((community) => {
          const url = new URL(community.value);
          const uuid = url.pathname.split('/').pop();
          return (
            <Link
              href={`/communities/${uuid}`}
              key={community.value}
              className={
                'flex h-20 items-center gap-2 border border-primary p-2 hover:bg-daliaGray-200'
              }
            >
              <UsersIcon className={'shrink-0'} />
              <div className={'text-wrap break-all'}>{community.label}</div>
            </Link>
          );
        })}
      </div>
    </div>
  );
};

export type CommunityListBodyProps = {
  communities: LabelValuePair[];
};

export default CommunityListBody;
