'use client';
import React, { FC, Suspense, useState } from 'react';
import { FlexFiller, HFlex } from '@/components/Flex';
import Icon from '@/components/Icon/Icon';
import IconButton from '@/components/IconButton/IconButton';
import Text from '@/components/Text/Text';
import Button from '@/components/Button/Button';
import { usePathname } from 'next/navigation';
import SearchInput from '@/app/_parts/TopBar/SearchInput';
import UserIconButton from '@/app/_parts/TopBar/UserIconButton';
import Link from 'next/link';
import { topMenuItems1, topMenuItems2 } from '@/app/_parts/TopBar/MenuItems';
import { cn } from '@/lib/utils';
import { Drawer, DrawerContent, DrawerTrigger } from '@/components/ui/drawer';
import SideBar from '@/app/_parts/SideBar';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { LoginURL } from '@/lib/settings.mjs';
import { Loader2Icon } from 'lucide-react';
import { useUserInfo } from '@/lib/auth/authApi';

const searchInputBlacklist: string[] = [
  'search',
  'login',
  'profile',
  'register',
  'community',
  'explore',
  'AddContent',
];

const transparentPages: string[] = ['/basic', '/advanced'];

const TopBar: FC<TopBarProps> = ({ activePage, showSearchInput }) => {
  const path = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { userInfo: loggedIn, isLoading } = useUserInfo();

  const shouldTransparentBg = transparentPages.some((p) => path === p || path === `${p}/`);

  return (
    <div
      className={cn('sticky top-0 z-20 bg-white', {
        'pb-5': shouldTransparentBg,
      })}
    >
      <HFlex
        className={cn(
          'mx-5 mt-5 h-[3.25rem] items-center border border-primary bg-white',
          showSearchInput && 'border-b-0 lg:border-b'
        )}
      >
        <a
          className={cn(
            'flex h-full flex-shrink-0 flex-row items-center gap-2 border-e border-primary px-5 lg:w-[calc(17rem-1px)]',
            path === '/basic' && 'hover:text-primary focus:text-primary'
          )}
          href={path !== '/basic' ? '/' : undefined}
        >
          <Icon source={'logo'} size={28} />
          <Text className={'hidden lg:inline'}>
            <b>DALIA</b> Search Portal
          </Text>
        </a>
        {activePage && !searchInputBlacklist.includes(activePage) && (
          <Suspense>
            <SearchInput />
          </Suspense>
        )}
        <ScrollArea>
          <HFlex>
            <HFlex
              className={
                'hidden h-full items-center border-e border-primary lg:flex lg:flex-row'
              }
            >
              {topMenuItems1.map((menuItem) => (
                <Button
                  key={menuItem.path}
                  dark={
                    path === menuItem.path ||
                    activePage?.toLowerCase() === menuItem.label
                  }
                  disabled={menuItem.disabled}
                  className={cn(menuItem.className)}
                  borderless
                  onClick={() => setDrawerOpen(false)}
                  link={
                    !menuItem.disabled
                      ? {
                          href: menuItem.path,
                          target: menuItem.path.startsWith('http')
                            ? '_blank'
                            : '_self',
                        }
                      : undefined
                  }
                >
                  {menuItem.label}
                </Button>
              ))}
            </HFlex>
            <HFlex
              className={
                'hidden h-full items-center border-e border-primary lg:flex lg:flex-row'
              }
            >
              {topMenuItems2.map((menuItem) => (
                <Button
                  key={menuItem.path}
                  dark={path === menuItem.path}
                  borderless
                  disabled={menuItem.disabled}
                  onClick={() => setDrawerOpen(false)}
                  className={cn(menuItem.className)}
                  link={
                    !menuItem.disabled
                      ? {
                          href: menuItem.path,
                          target: menuItem.path.startsWith('http')
                            ? '_blank'
                            : '_self',
                        }
                      : undefined
                  }
                >
                  {menuItem.label}
                </Button>
              ))}
            </HFlex>
          </HFlex>
          <ScrollBar orientation={'horizontal'} />
        </ScrollArea>
        <Text variant={'mobileText'} className={'ps-5 lg:hidden'}>
          <b>DALIA</b> <span className={'hidden md:inline'}>Search</span> Portal
        </Text>

        <FlexFiller />
        <Drawer
          fadeFromIndex={0}
          snapPoints={[]}
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
        >
          <DrawerTrigger asChild>
            <IconButton
              className={'border-s border-primary lg:hidden'}
              source={'hamburger'}
              borderless
              onClick={() => setDrawerOpen((o) => !o)}
            />
          </DrawerTrigger>
          <DrawerContent>
            <SideBar activePage={activePage} setShowSidebar={setDrawerOpen} />
          </DrawerContent>
        </Drawer>

        {isLoading ? (
          <Loader2Icon className={'mx-2 animate-spin'} />
        ) : loggedIn ? (
          <div className={'invisible max-lg:hidden lg:visible'}>
            <UserIconButton />
          </div>
        ) : (
          <HFlex
            className={
              'hidden h-full items-center gap-2.5 border-s border-primary px-5 lg:flex lg:flex-row'
            }
          >
            <Link href={LoginURL} className={'text-daliaPrimary underline'}>
              Login
            </Link>
            {/*  or*/}
            {/*  <Button*/}
            {/*    borderless*/}
            {/*    dark*/}
            {/*    className={'h-full'}*/}
            {/*    disabled*/}
            {/*    link={{*/}
            {/*      href: `${NEXT_PUBLIC_BACKEND_ROOT}/accounts/signup`,*/}
            {/*    }}*/}
            {/*  >*/}
            {/*    Create an account*/}
            {/*  </Button>*/}
          </HFlex>
        )}
      </HFlex>
      {showSearchInput && (
        <div className={'mx-5 block lg:hidden'}>
          <Suspense fallback={'Loading...'}>
            <SearchInput mobile />
          </Suspense>
        </div>
      )}
    </div>
  );
};

export type TopBarProps = {
  activePage?: string;
  query?: string;
  smallUser?: boolean;
  showSearchInput?: boolean;
  // setShowSidebar?: Dispatch<SetStateAction<boolean>>;
};

export default TopBar;
