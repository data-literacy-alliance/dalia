'use client';
import React, { FC, useEffect, useState } from 'react';
import DetailsBody from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody';
import { ResourceItem } from '@/lib/types/ItemTypes';

const PreviewDetailsBody: FC<PreviewDetailsBodyProps> = ({ tempItemId }) => {
  const [item, setItem] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setItem(window.sessionStorage.getItem(tempItemId));
    }
  }, [tempItemId]);
  
  return item ? (
    <DetailsBody
      item={JSON.parse(item) as ResourceItem}
      recommendedContent={[]}
      preview
    />
  ) : null;
};

export type PreviewDetailsBodyProps = {
  tempItemId: string;
};

export default PreviewDetailsBody;
