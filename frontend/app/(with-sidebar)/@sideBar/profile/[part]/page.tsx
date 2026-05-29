'use client';
import React from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import Text from '@/components/Text';
import Button from '@/components/Button';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { VFlex } from '@/components/Flex';
import { useUserInfo } from '@/lib/auth/authApi';
import { NEXT_PUBLIC_BACKEND_ROOT } from '@/lib/settings.mjs';

export default function ProfileSideBarPage() {
  const { userInfo } = useUserInfo();

  if (!userInfo) {
    return null;
  }

  return (
    <div
      className={
        'sticky top-[4.5rem] mx-5 mb-1 h-[calc(100dvh-4.5rem)] overflow-auto border border-b-0 border-primary lg:mx-auto lg:border-0'
      }
    >
      <ScrollArea className={'h-full'}>
        <div
          className={
            'space-y-1 border-b border-primary pb-4 pe-px disabled:border-daliaGray-300 lg:border lg:border-r-0 lg:border-t-0'
          }
        >
          <Text className={'block py-3 ps-4'}>User Settings</Text>
          <Button
            borderless
            leftAligned
            small
            leadIcon={'user'}
            link={{
              href: '/profile/',
            }}
          >
            View Account
          </Button>
          <Button
            borderless
            leftAligned
            small
            leadIcon={'cog'}
            link={{ href: '/profile/preferences/' }}
          >
            Preferences
          </Button>
        </div>
        <Accordion
          type={'multiple'}
          defaultValue={['browse', 'your-files']}
          className={'border-primary lg:border-l'}
        >
          <AccordionItem
            value={'browse'}
            className={'mt-px overflow-hidden first:mt-0'}
          >
            <AccordionTrigger
              className={
                'flex h-12 flex-1 cursor-default items-center justify-between border-b border-primary px-5 leading-none outline-none'
              }
            >
              Browse
            </AccordionTrigger>
            <AccordionContent className={'border-b border-primary pr-px'}>
              <VFlex className="gap-2 pb-2 pt-4">
                {userInfo.is_curator && (
                  <Button
                    borderless
                    leftAligned
                    small
                    leadIcon={'data'}
                    link={{
                      target: '_blank',
                      href: `${NEXT_PUBLIC_BACKEND_ROOT}/admin/`,
                    }}
                  >
                    Admin Panel
                  </Button>
                )}
                <Button
                  borderless
                  leftAligned
                  small
                  leadIcon={'document'}
                  link={{
                    href: '/profile/activities/',
                  }}
                >
                  My Activities
                </Button>
                <Button
                  borderless
                  leftAligned
                  small
                  leadIcon={'document'}
                  link={{
                    href: '/profile/contributions/',
                  }}
                >
                  My Contributions
                </Button>
                {/*<Button*/}
                {/*  borderless*/}
                {/*  leftAligned*/}
                {/*  small*/}
                {/*  leadIcon={'library'}*/}
                {/*  disabled*/}
                {/*  // link={{*/}
                {/*  //   href: '/profile/bookmarks',*/}
                {/*  // }}*/}
                {/*>*/}
                {/*  My Communities*/}
                {/*</Button>*/}
                {/*<Button*/}
                {/*  borderless*/}
                {/*  leftAligned*/}
                {/*  small*/}
                {/*  leadIcon={'comment'}*/}
                {/*  disabled*/}
                {/*  // link={{*/}
                {/*  //   href: '/profile/likes',*/}
                {/*  // }}*/}
                {/*>*/}
                {/*  My Reviews*/}
                {/*</Button>*/}
              </VFlex>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem
            value={'your-files'}
            className={'mt-px overflow-hidden first:mt-0'}
          >
            <AccordionTrigger
              className={
                'flex h-12 flex-1 cursor-default items-center justify-between border-b border-primary px-5 leading-none outline-none'
              }
            >
              Your Files
            </AccordionTrigger>
            <AccordionContent className={'border-b border-primary'}>
              <VFlex className="gap-2 pb-2 pr-px pt-4">
                <Button
                  borderless
                  leftAligned
                  small
                  leadIcon={'plus-circle'}
                  link={{
                    href: '/items/new',
                  }}
                >
                  Add Content
                </Button>
              </VFlex>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </ScrollArea>
    </div>
  );
}
