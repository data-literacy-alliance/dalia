import { IconButtonProps } from '@/components/IconButton';
import { FC, ReactNode } from 'react';
import CiteDialog from '@/components/CiteDialog';
import { ResourceItem } from '@/lib/types/ItemTypes';
import ShareDialog from '@/components/ShareDialog';

type ItemAction = IconButtonProps & {
  Parent?: FC<{ children: ReactNode; item: ResourceItem }>;
};

export const ItemActions: ItemAction[] = [
  {
    dark: true,
    iconProps: { size: 14 },
    source: 'bookmark',
    disabled: true,
  },
  {
    dark: true,
    iconProps: { size: 14 },
    source: 'share',
    Parent: ShareDialog,
  },
  {
    dark: true,
    iconProps: { size: 14 },
    source: 'cite',
    Parent: CiteDialog,
  },
  {
    dark: true,
    iconProps: { size: 14 },
    source: 'heart',
    disabled: true,
    onClick: () => {

    }
  },
];
