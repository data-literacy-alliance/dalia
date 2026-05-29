'use client';
import React, { FC } from 'react';
import * as ScrollArea from '@radix-ui/react-scroll-area';
import { ScrollAreaProps } from '@radix-ui/react-scroll-area';
import clsx from 'clsx';

// @TODO replace with shadcn scroll-area eventually.
// Do NOT update this component.

const ScrollView: FC<ScrollViewProps> = ({ children, className, ...props }) => {
  return (
    <ScrollArea.Root {...props} className={clsx(className, 'overflow-hidden')}>
      <ScrollArea.Viewport className={'w-full h-full'}>
        {children}
      </ScrollArea.Viewport>
      <ScrollArea.Scrollbar
        className="flex select-none touch-none p-0.5 bg-daliaGray-200 transition-colors duration-[160ms] ease-out hover:bg-daliaGray-200 data-[orientation=vertical]:w-2.5 data-[orientation=horizontal]:flex-col data-[orientation=horizontal]:h-2.5"
        orientation="vertical"
      >
        <ScrollArea.Thumb className="flex-1 bg-primary rounded-[10px] relative before:content-[''] before:absolute before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:w-full before:h-full before:min-w-[44px] before:min-h-[44px]" />
      </ScrollArea.Scrollbar>
      <ScrollArea.Scrollbar
        className="flex select-none touch-none p-0.5 bg-daliaGray-200 transition-colors duration-[160ms] ease-out hover:bg-daliaGray-200 data-[orientation=vertical]:w-2.5 data-[orientation=horizontal]:flex-col data-[orientation=horizontal]:h-2.5"
        orientation="horizontal"
      >
        <ScrollArea.Thumb className="flex-1 bg-daliaGray-300 rounded-[10px] relative before:content-[''] before:absolute before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:w-full before:h-full before:min-w-[44px] before:min-h-[44px]" />
      </ScrollArea.Scrollbar>
      <ScrollArea.Corner className="bg-blackA5" />
    </ScrollArea.Root>
  );
};

export type ScrollViewProps = ScrollAreaProps & {};

export default ScrollView;
