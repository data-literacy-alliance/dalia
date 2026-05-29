'use client';

import React, { FC, useEffect, useState } from 'react';
import DetailsSide from '@/app/(with-sidebar)/@sideBar/items/[id]/[slug]/_parts/DetailsSide';
import { ResourceItem } from '@/lib/types/ItemTypes';

const PreviewDetailsSide: FC<PreviewDetailsSideProps> = ({ tempItemId }) => {
  const [item, setItem] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setItem(window.sessionStorage.getItem(tempItemId));
    }
  }, [tempItemId]);

  return item ? <DetailsSide item={JSON.parse(item) as ResourceItem} preview /> : null;
};

export type PreviewDetailsSideProps = {
  tempItemId: string;
};

export default PreviewDetailsSide;
