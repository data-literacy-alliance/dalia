import React from 'react';
import { HFlex } from '@/components/Flex';
import TopBar from '@/app/_parts/TopBar';

export default function SearchLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div>
      <TopBar />
      <HFlex className="mx-4 bg-daliaGray-100 p-4 my-2">{children}</HFlex>
    </div>
  );
}
