'use client';
import React, { FC } from 'react';
import Image from 'next/image';
import { HFlex } from '@/components/Flex';
import Text from '@/components/Text';
import { Loader2Icon } from 'lucide-react';
import Icon from '@/components/Icon';
import ShareProfileDialog from '@/components/ShareProfileDialog';
import Button from '@/components/Button';
import { BASE_PATH } from '@/lib/settings.mjs';
import { useUserPerson } from '@/lib/api/person';
import DeletionRequestDialog from '@/app/(with-sidebar)/profile/_parts/DeletionRequestDialog';

const ProfileHeader: FC<ProfileHeaderProps> = () => {
  const { person, isLoading, userInfo } = useUserPerson();
  const isCurator = Boolean(userInfo?.is_curator);

  return isLoading ? (
    <Loader2Icon className={'animate-spin'} />
  ) : (
    userInfo && person && (
      <div
        className={
          'border-b border-primary px-5 pb-5 pt-16 lg:flex lg:pl-24 lg:pt-28'
        }
      >
        <div className={'pr-4 lg:flex-[2] lg:border-r lg:border-primary'}>
          <div className={'lg:flex lg:gap-6'}>
            <HFlex className={'items-center justify-between'}>
              <Icon size={120} source={'logo'} />
            </HFlex>
            <div className={'w-full pt-6'}>
              <Text variant={'h1'} className={'block leading-normal -ml-1'}>
                {person.first_name} {person.last_name}
              </Text>

              <Text className={'text-gray-600'}>{userInfo.email}</Text>
            </div>
          </div>

          <div className={'mt-8 grid grid-cols-1 gap-4 pl-2 lg:grid-cols-2'}>
            <div>
              <div className={'text-sm text-gray-500'}>Given Name</div>
              <div>{person.first_name}</div>
            </div>
            <div>
              <div className={'text-sm text-gray-500'}>Family Name</div>
              <div>{person.last_name}</div>
            </div>
            <div>
              <div className={'text-sm text-gray-500'}>ORCID</div>
              <div className={'truncate'} title={person.orcid}>
                {person.orcid}
              </div>
            </div>
            <div>
              <div className={'text-sm text-gray-500'}>Profile Visibility</div>
              <div className={'capitalize'}>{person.privacy_level}</div>
            </div>
            <div>
              <div className={'text-sm text-gray-500'}>Role</div>
              <div>{isCurator ? 'Curator' : 'Learner'}</div>
            </div>
          </div>
        </div>
        <div
          className={
            'flex flex-col items-start justify-end gap-2 pl-4 pt-4 lg:flex-1 xl:pr-36'
          }
        >
          <DeletionRequestDialog />
          <Button
            small
            className={'w-full'}
            link={
              person.homepage
                ? { href: person.homepage, target: '_blank' }
                : undefined
            }
            disabled={!person.homepage}
          >
            <Icon source={'arrow-top-right'} size={10} />
            My Homepage
          </Button>
          <Button
            small
            className={'w-full'}
            link={
              person.orcid
                ? {
                    href: `https://orcid.org/${person.orcid}`,
                    target: '_blank',
                  }
                : undefined
            }
            disabled={!person.orcid}
          >
            <Image
              src={`${BASE_PATH}/images/ORCIDLogo.png`}
              alt={'ORCID'}
              width={18}
              height={18}
            />
            My ORCID Page
          </Button>
          <ShareProfileDialog userUUID={person.uuid}>
            <Button
              small
              leadIcon={'share'}
              className={'w-full'}
              disabled={person.privacy_level !== 'public'}
            >
              Share My Public Profile
            </Button>
          </ShareProfileDialog>
        </div>
      </div>
    )
  );
};

export type ProfileHeaderProps = {};

export default ProfileHeader;
