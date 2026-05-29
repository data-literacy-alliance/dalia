'use client';
import React, { FC } from 'react';
import IconButton from '@/components/IconButton';
import { Drawer, DrawerContent, DrawerTrigger } from '@/components/ui/drawer';
import { useMainContext } from '@/app/Providers';

const ResponsiveSidebar: FC<ResponsiveSidebarProps> = ({ children }) => {
  const { sidebarOpen, setSidebarOpen } = useMainContext();
  return (
    <>
      <div className={'fixed -right-1 top-32 z-10 min-w-0 lg:hidden'}>
        <Drawer modal open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <DrawerTrigger asChild>
            <IconButton
              source={'cog'}
              onClick={() => setSidebarOpen((s) => !s)}
            />
          </DrawerTrigger>
          <DrawerContent>{children}</DrawerContent>
        </Drawer>
      </div>
      <div
        className={`top-0 hidden w-full flex-shrink-0 lg:static lg:ms-5 lg:block lg:w-[17rem]`}
      >
        {children}
      </div>
    </>
  );
};

export type ResponsiveSidebarProps = {
  children: React.ReactNode;
};

export default ResponsiveSidebar;
