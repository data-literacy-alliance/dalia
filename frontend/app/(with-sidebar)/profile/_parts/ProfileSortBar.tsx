'use client';
import React, { FC } from 'react';
import { HFlex } from '@/components/Flex';
import { cn } from '@/lib/utils';
import IconButton, { IconButtonGroup } from '@/components/IconButton';
import { useParams, useSearchParams } from 'next/navigation';
import { useRouter } from 'nextjs-toploader/app';
import ButtonGroup from '@/components/Button/ButtonGroup';
import Button from '@/components/Button';
import { IconSource } from '@/components/Icon';
import { useUserPerson } from '@/lib/api/person';

type FilterOption = {
  value: string;
  icon: string;
  label: string;
  requiresCurator?: boolean;
  requiresAuth?: boolean;
};

const validFilters = {
  activities: [
    {
      value: 'history',
      icon: 'history',
      label: 'History',
    },
    {
      value: 'bookmark',
      icon: 'bookmark',
      label: 'Bookmarks',
    },
    {
      value: 'likes',
      icon: 'heart-outline',
      label: 'Likes',
    },
  ],
  contributions: [
    {
      value: 'my-resources',
      icon: 'document',
      label: 'My Resources',
    },
    {
      value: 'published',
      icon: 'checkmark-circle',
      label: 'Published',
    },
    {
      value: 'pending',
      icon: 'edit',
      label: 'Pending',
    },
    {
      value: 'archived',
      icon: 'archive',
      label: 'Archived',
    },
    {
      value: 'unpublished',
      icon: 'document-slash',
      label: 'Unpublished',
    },
    {
      value: 'all-resources',
      icon: 'users',
      label: 'All Resources',
      requiresAuth: true,  // visible to any logged-in user (NOT requiresCurator)
    },
  ],
};

const ProfileSortBar: FC<ProfileSortBarProps> = ({ className }) => {
  const searchParams = useSearchParams();
  const { part } = useParams<{ part: 'activities' | 'contributions' }>();
  const router = useRouter();
  const { userInfo } = useUserPerson();

  // Check if user is curator or superuser
  const isCuratorOrSuperuser = Boolean(userInfo?.is_curator);

  // Filter options based on user role
  const allFilters = validFilters[part];
  const filters = allFilters.filter((filter: FilterOption) => {
    // If filter requires curator role, only show to curators/superusers
    if (filter.requiresCurator) {
      return isCuratorOrSuperuser;
    }
    // If filter requires auth, only show to logged-in users
    if (filter.requiresAuth) {
      return !!userInfo;
    }
    return true;
  });

  const view = searchParams.get('view') || 'list';
  const filter = searchParams.get('filter') || '';

  const changeFilters = (newFilter: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (filter === newFilter) {
      newParams.set('filter', 'my-resources');
    } else {
      newParams.set('filter', newFilter);
    }
    router.push('?' + newParams.toString());
  };

  const changeView = (newView: string) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('view', newView);
    newParams.set('limit', newView === 'grid' ? '18' : '9');
    router.push('?' + newParams.toString());
  };

  return (
    <HFlex
      className={cn(
        'h-10 w-full items-center border-b border-primary',
        className
      )}
    >
      <div className={'grow'}>
        <ButtonGroup value={filter} onChange={changeFilters}>
          {filters.map((filter) => (
            <Button
              key={filter.value}
              small
              value={filter.value}
              className={'border-x-0'}
              leadIcon={filter.icon as IconSource}
            >
              <span className={'max-sm:hidden'}>{filter.label}</span>
            </Button>
          ))}
        </ButtonGroup>
      </div>
      <IconButtonGroup value={view} onChange={changeView}>
        <IconButton
          source={'grid'}
          small
          key={'grid'}
          value={'grid'}
          iconProps={{ size: 24 }}
        />
        <IconButton
          source={'list'}
          small
          key={'list'}
          value={'list'}
          iconProps={{ size: 24 }}
        />
      </IconButtonGroup>
    </HFlex>
  );
};

export type ProfileSortBarProps = {
  className?: string;
};

export default ProfileSortBar;
