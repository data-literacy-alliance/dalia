import React, { FC } from 'react';
import { HFlex, VFlex } from '@/components/Flex';
import ResponsiveSidebar from '@/app/(with-sidebar)/ResponsiveSidebar';

const Layout: FC<LayoutProps> = ({ children, sideBar, topBar }) => {
  return (
    <VFlex>
      {topBar}
      <HFlex
        className={'relative w-full'}
        vocab="https://schema.org/"
        prefix="
        dcterms:  https://purl.org/dc/terms/
        fabio:    https://purl.org/spar/fabio/
        mo:       https://purl.org/ontology/modalia
      "
      >
        <ResponsiveSidebar>{sideBar}</ResponsiveSidebar>
        <div className={'ml-[-1px] flex min-w-0 max-w-full flex-1'}>{children}</div>
      </HFlex>
    </VFlex>
  );
};

export type LayoutProps = {
  children: React.ReactNode;
  sideBar: React.ReactNode;
  topBar: React.ReactNode;
};

export default Layout;
