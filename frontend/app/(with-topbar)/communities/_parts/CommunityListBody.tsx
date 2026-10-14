'use client';

import React, { FC, useMemo, useState } from 'react';
import Text from '@/components/Text';
import Link from 'next/link';
import { UsersIcon } from 'lucide-react';
import TextBox from '@/components/Textbox/Textbox';

export type CommunityItem = {
  uuid: string;
  title: string;
};

const CommunityListBody: FC<CommunityListBodyProps> = ({ communities }) => {
  const [query, setQuery] = useState('');

  const grouped = useMemo((): Array<[string, CommunityItem[]]> => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? communities.filter((c) => c.title.toLowerCase().includes(q))
      : communities;

    const buckets: Record<string, CommunityItem[]> = {};
    for (const c of filtered) {
      const first = c.title[0]?.toUpperCase() ?? '#';
      const key = /^[A-Z]$/.test(first) ? first : '#';
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(c);
    }
    return Object.entries(buckets).sort(([a], [b]) => a.localeCompare(b));
  }, [communities, query]);

  return (
    <div className={'mx-auto w-full'}>
      <Text variant={'h4'} className={'block text-center'}>
        Communities in DALIA
      </Text>
      <div className={'mt-4 max-w-sm'}>
        <TextBox
          label={'Search communities'}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      {grouped.length === 0 && (
        <p className={'mt-8 text-center text-sm text-muted-foreground'}>
          No communities match your search.
        </p>
      )}
      {grouped.map(([letter, items]) => (
        <div key={letter} className={'mt-8'}>
          {grouped.length > 1 && (
            <h2 className={'mb-2 border-b border-primary pb-1 text-sm font-semibold uppercase tracking-wider text-daliaGray-300'}>
              {letter} ({items.length})
            </h2>
          )}
          <div
            className={
              'grid grid-cols-1 gap-4 p-2 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6'
            }
          >
            {items.map((community) => (
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
      ))}
    </div>
  );
};

export type CommunityListBodyProps = {
  communities: CommunityItem[];
};

export default CommunityListBody;
