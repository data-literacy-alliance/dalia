'use client';

import React, { FC } from 'react';
import Icon from '@/components/Icon';
import { HFlex, VFlex } from '@/components/Flex';
import Button, { SocialMediaButton } from '@/components/Button';
import Text from '@/components/Text';
import Image from 'next/image';
import { SocialMediaField } from '@/lib/types/Common';

const CommunitiesHeader: FC<CommunityHeaderProps> = ({
  followersCount,
  viewsCount,
  likesCount,
  description,
  title,
  socialMedias,
}) => {
  const logoBgPath = `/images/logo-bg.png`;

  return (
    <VFlex className={'w-full'}>
      <div
        className={
          'w-full px-5 pt-16 lg:pt-28 lg:pl-24 pb-5 border-b border-primary disabled:border-daliaGray-300'
        }
      >
        <div className={'flex lg:flex-row items-start flex-col w-full'}>
          <HFlex className={'w-44'}>
            <div
              className={
                'relative inset-0 flex justify-center items-center w-44 h-44'
              }
            >
              <Image
                src={logoBgPath}
                alt={title}
                fill={true}
                sizes="(max-width: 175 max-height: 175)"
              />
              <Icon
                className={'absolute'}
                source={'logo'}
                size={75}
                color="white"
              />
            </div>
          </HFlex>
          <VFlex className={'w-full lg:pl-5 pt-5 lg:pt-0 flex-1 min-w-0'}>
            <Text className={'font-semibold'}>Community Page</Text>
            <Text variant={'h2'} className={'break-words'}>
              {title}
            </Text>
            <div
              className={
                'items-start lg:items-center lg:pt-5 lg:flex-row flex flex-col gap-1'
              }
            >
              <Button
                borderless
                leftAligned
                small
                noPadding
                className={'select-none enabled:pointer-events-none px-0'}
                leadIcon={'user'}
              >
                {followersCount} followers
              </Button>
              <div className={'hidden lg:block'}>|</div>
              <Button
                borderless
                leftAligned
                small
                noPadding
                className={'select-none enabled:pointer-events-none'}
                leadIcon={'eye'}
              >
                {viewsCount} total views
              </Button>
              <div className={'hidden lg:block'}>|</div>
              <Button
                borderless
                leftAligned
                small
                noPadding
                className={'select-none enabled:pointer-events-none'}
                leadIcon={'heart'}
              >
                {likesCount} likes
              </Button>
            </div>
          </VFlex>
        </div>
      </div>
      <div
        className={
          'pt-8 px-5 lg:pl-12 xl:pl-24 pb-10 max-lg:border-b border-primary disabled:border-daliaGray-300'
        }
      >
        <VFlex>
          <Text variant={'h4'}>About</Text>
          <HFlex
            className={
              'items-start content-evenly gap-x-8 mt-4 flex flex-col lg:items-stretch lg:flex-row'
            }
          >
            <Text
              className={
                'lg:border-r border-primary block disabled:border-daliaGray-300 lg:pr-8 xl:pr-12 md:basis-2/3 sm:basis-3/5'
              }
            >
              {description || <i>No description</i>}
            </Text>
            <VFlex className={'max-lg:pt-5'}>
              {socialMedias?.map((socialMedia) => (
                <SocialMediaButton
                  borderless
                  leftAligned
                  small
                  key={socialMedia.url}
                  socialMedia={socialMedia.name}
                  link={{ href: socialMedia.url, target: '_blank' }}
                />
              ))}
            </VFlex>
          </HFlex>
        </VFlex>
      </div>
    </VFlex>
  );
};

export type CommunityHeaderProps = {
  followersCount: number;
  viewsCount: number;
  likesCount: number;
  description: string;
  title: string;
  socialMedias?: SocialMediaField[];
};

export default CommunitiesHeader;
