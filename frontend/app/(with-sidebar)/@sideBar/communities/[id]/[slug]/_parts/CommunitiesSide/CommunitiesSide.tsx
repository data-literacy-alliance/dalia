import React, { FC } from 'react';
import Button, { SocialMediaButton } from '@/components/Button';
import Text from '@/components/Text';
import { Community } from '@/lib/types/Community';
import { ScrollArea } from '@/components/ui/scroll-area';

type CommunitiesSideProps = {
  community: Community;
};

const CommunitiesSide: FC<CommunitiesSideProps> = ({ community }) => {
  return (
    <div
      className={
        'sticky top-[4.5rem] mx-5 mb-1 h-[calc(100dvh-4.5rem)] overflow-auto border border-b-0 border-primary lg:mx-auto lg:border-0'
      }
    >
      <ScrollArea className={'h-full'}>
        <div
          className={
            'space-y-1 border border-b border-primary pb-4 disabled:border-daliaGray-300 lg:border lg:border-r-0 lg:border-t-0'
          }
        >
          <Text className={'block py-3 ps-4'}>Interact</Text>
          <Button borderless leftAligned small disabled leadIcon={'heart'}>
            Follow
          </Button>
          <Button borderless leftAligned small disabled leadIcon={'connect'}>
            Join
          </Button>
          <Button borderless leftAligned small disabled leadIcon={'mail'}>
            Contact
          </Button>
        </div>
        {community.social_media && community.social_media.length > 0 && (
          <div
            className={
              'space-y-1 border border-b border-primary px-1 pb-4 lg:border lg:border-r-0 lg:border-t-0'
            }
          >
            <Text className={'block py-4 ps-4'}>Social media</Text>
            {community.social_media.map((socialMedia) => (
              <SocialMediaButton
                borderless
                leftAligned
                small
                socialMedia={socialMedia.name}
                key={socialMedia.url}
                link={{
                  href: socialMedia.url,
                  target: '_blank',
                }}
              />
            ))}
          </div>
        )}
        {/*<div className={styles.spacer} />*/}
        {/*<div className={'p-5'}>*/}
        {/*  <Button dark leadIcon={'share'} className={'w-full'}>*/}
        {/*    Share community*/}
        {/*  </Button>*/}
        {/*</div>*/}
      </ScrollArea>
    </div>
  );
};

export default CommunitiesSide;
