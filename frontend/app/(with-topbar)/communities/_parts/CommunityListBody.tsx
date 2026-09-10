'use client';

import React, { FC } from 'react';
import Text from '@/components/Text';
import Link from 'next/link';
import { UsersIcon } from 'lucide-react';

export type CommunityItem = {
  uuid: string;
  title: string;
};

const CommunityListBody: FC<CommunityListBodyProps> = ({ communities }) => {
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
        {communities.map((community) => (
          <Link
            href={`/communities/${community.uuid}`}
            key={community.uuid}
            className={
              'flex h-20 items-center gap-2 border border-primary p-2 hover:bg-daliaGray-200'
            }
          >
            <UsersIcon className={'shrink-0'} />
            <div className={'text-wrap break-all'}>{community.title}</div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export type CommunityListBodyProps = {
  communities: CommunityItem[];
};

export default CommunityListBody;
