'use client';
import React, { FC, Suspense, useEffect, useRef } from 'react';
import Text from '@/components/Text';
import { HFlex, VFlex } from '@/components/Flex';
import Item, { GridItem } from '@/components/Item';
import useWindowDimensions, { ScreenSizes } from '@/lib/useWindowDimensions';
import { useSearchParams } from 'next/navigation';
import { ResourceItem } from '@/lib/types/ItemTypes';
import ProfileSortBar from '@/app/(with-sidebar)/profile/_parts/ProfileSortBar';
import { LoginURL } from '@/lib/settings.mjs';
import { useRouter } from 'nextjs-toploader/app';
import { useUserInfo } from '@/lib/auth/authApi';

const ProfileItems: FC<ProfileLatestUploadsProps> = ({ items, title, pagination, editable: editableProp, deletable: deletableProp }) => {
  const params = useSearchParams();
  const { width } = useWindowDimensions();
  const view =
    width < ScreenSizes.xl
      ? 'grid'
      : ((params.get('view') || 'list') as 'list' | 'grid');
  const activeFilter = params.get('filter') || 'my-resources';
  const deletable = deletableProp !== undefined ? deletableProp : activeFilter !== 'all-resources';
  const editable = editableProp !== undefined ? editableProp : true;

  const titleRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    titleRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [activeFilter]);

  const { userInfo: loggedIn, isLoading: loginIsLoading } = useUserInfo();
  const router = useRouter();

  if (!loginIsLoading && !loggedIn) {
    router.push(LoginURL);
    return null;
  }

  return (
    <>
      {!!title && (
        <div ref={titleRef} className={'py-6'}>
          <Text variant={'h4'} className={'lg:pl-24'}>
            {title}
          </Text>
        </div>
      )}
      <Suspense fallback={'Loading...'}>
        <ProfileSortBar className={'mb-4 border-x-0 border-t'} />
      </Suspense>
      {items.length === 0 ? (
        <div className={'grow'}>
          <Text className={'m-2'}>No items.</Text>
        </div>
      ) : view === 'grid' ? (
        <HFlex
          className={
            'ml-[-1px] grid w-[calc(100%+1px)] grid-cols-1 border-l border-t border-primary xl:grid-cols-2 2xl:grid-cols-3'
          }
        >
          {items.map((item) => (
            <GridItem
              item={item}
              key={item.id}
              noBorder
              className={'w-full border-b border-primary lg:border-r'}
              editable={editable}
              deletable={deletable}
              onRemove={!editable && !deletable ? () => router.refresh() : undefined}
            />
          ))}
        </HFlex>
      ) : (
        <VFlex
          className={
            'ml-[-1px] w-[calc(100%+1px)] border-l border-t border-primary'
          }
        >
          {items.map((item) => (
            <Item
              item={item}
              key={item.id}
              noBorder
              className={'w-full border-b border-primary lg:border-r'}
              editable={editable}
              deletable={deletable}
              onRemove={!editable && !deletable ? () => router.refresh() : undefined}
            />
          ))}
        </VFlex>
      )}
      {pagination && (pagination.previous || pagination.next) && (
        <div className="flex items-center justify-between border-t border-primary px-4 py-3">
          <span className="text-sm text-gray-600">
            {pagination.count} item{pagination.count !== 1 ? 's' : ''}
          </span>
          <div className="flex gap-2">
            <button
              disabled={!pagination.previous}
              onClick={() => {
                const p = new URLSearchParams(params.toString());
                p.set('page', String(pagination.page - 1));
                router.push('?' + p.toString());
              }}
              className="px-3 py-1 text-sm border border-primary rounded disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={!pagination.next}
              onClick={() => {
                const p = new URLSearchParams(params.toString());
                p.set('page', String(pagination.page + 1));
                router.push('?' + p.toString());
              }}
              className="px-3 py-1 text-sm border border-primary rounded disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export type ProfileLatestUploadsProps = {
  items: ResourceItem[];
  title?: string;
  pagination?: { count: number; next: string | null; previous: string | null; page: number };
  editable?: boolean;
  deletable?: boolean;
};

export default ProfileItems;
