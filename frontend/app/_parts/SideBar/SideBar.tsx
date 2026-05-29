'use client';

import React, { Dispatch, FC, SetStateAction } from 'react';
import Button from '@/components/Button';
import { topMenuItems1, topMenuItems2 } from '@/app/_parts/TopBar';
import { usePathname } from 'next/navigation';
import { ScrollArea } from '@/components/ui/scroll-area';

const SideBar: FC<SideBarProps> = ({ setShowSidebar, activePage }) => {
  const path = usePathname();

  return (
    <ScrollArea className={'max-h-dvh'}>
      {topMenuItems1.map((menuItem) => (
        <Button
          key={menuItem.path}
          dark={
            path === menuItem.path ||
            activePage?.toLowerCase() === menuItem.label
          }
          disabled={menuItem.disabled}
          borderless
          leftAligned
          onClick={() => setShowSidebar?.(false)}
          className={'w-full py-6'}
          link={
            !menuItem.disabled
              ? {
                  href: menuItem.path,
                  target: menuItem.path.startsWith('http') ? '_blank' : '_self',
                }
              : undefined
          }
        >
          {menuItem.label}
        </Button>
      ))}
      <hr />
      {topMenuItems2.map((menuItem) => (
        <Button
          key={menuItem.path}
          dark={
            path === menuItem.path ||
            activePage?.toLowerCase() === menuItem.label
          }
          disabled={menuItem.disabled}
          borderless
          leftAligned
          className={'w-full py-6'}
          onClick={() => setShowSidebar?.(false)}
          link={
            !menuItem.disabled
              ? {
                  href: menuItem.path,
                  target: menuItem.path.startsWith('http') ? '_blank' : '_self',
                }
              : undefined
          }
        >
          {menuItem.label}
        </Button>
      ))}
    </ScrollArea>
  );
};

export type SideBarProps = {
  setShowSidebar?: Dispatch<SetStateAction<boolean>>;
  activePage?: string;
};

export default SideBar;
