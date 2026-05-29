import React from 'react';
import { HFlex, VFlex } from '@/components/Flex';
import TopBar from '@/app/_parts/TopBar';
import { BASE_PATH } from '@/lib/settings.mjs';

export default function SearchLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <VFlex
      className={'relative h-dvh flex-1 bg-cover'}
      style={{
        backgroundImage: `url(${BASE_PATH}/images/search-bg.svg)`,
      }}
    >
      <TopBar />
      <HFlex className="items-center justify-center">
        <div className="flex justify-center">{children}</div>
      </HFlex>
    </VFlex>
  );
}
