'use client';
import React, { FC } from 'react';
import { usePerson } from '@/lib/api/person';
import { Loader2Icon } from 'lucide-react';
import { HFlex } from '@/components/Flex';
import Icon from '@/components/Icon';
import Text from '@/components/Text';
import Button from '@/components/Button';
import Image from 'next/image';
import { BASE_PATH } from '@/lib/settings.mjs';
import ShareProfileDialog from '@/components/ShareProfileDialog';

const PublicProfileBody: FC<PublicProfileBodyProps> = ({ uuid }) => {
  const { person, isLoading } = usePerson(uuid);

  return isLoading ? (
    <Loader2Icon className={'animate-spin'} />
  ) : (
    person ?
      (person.privacy_level !== 'private' ? (
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
                <div className={'flex w-full items-center justify-between'}>
                  <Text variant={'h1'} className={'block leading-normal'}>
                    {person.first_name} {person.last_name}
                  </Text>
                </div>

                <Text className={'text-gray-600'}></Text>
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
                <div className={'text-sm text-gray-500'}>
                  Profile Visibility
                </div>
                <div className={'capitalize'}>{person.privacy_level}</div>
              </div>
            </div>
          </div>
          <div
            className={
              'flex flex-col items-start justify-end gap-2 pl-4 pt-4 lg:flex-1 xl:pr-36'
            }
          >
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
              Visit Homepage
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
              Visit ORCID Page
            </Button>
            <ShareProfileDialog userUUID={person.uuid}>
              <Button small leadIcon={'share'} className={'w-full'}>
                Share This Profile
              </Button>
            </ShareProfileDialog>
          </div>
        </div>
      ) : (
        <div>This profile is not public.</div>
      )) : (<div>No profile found.</div>)
  );
};

export type PublicProfileBodyProps = {
  uuid: string;
};

export default PublicProfileBody;
