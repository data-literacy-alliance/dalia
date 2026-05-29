import React, { FC } from 'react';
import { notFound } from 'next/navigation';
import PreviewDetailsSide from '@/app/(with-sidebar)/@sideBar/items/new/preview/PreviewDetailsSide';

type PageProps = {
  searchParams: {
    item?: string;
  };
};

const Page: FC<PageProps> = ({ searchParams }) => {
  const { item } = searchParams;
  if (!item) {
    notFound();
  }

  return <PreviewDetailsSide tempItemId={item} />;
};

export default Page;
