'use client';
import React, { FC, ReactNode } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import CopyButton from '@/components/CopyButton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ResourceItem } from '@/lib/types/ItemTypes';

const ShareDialog: FC<ShareDialogProps> = ({ children, item }) => {
  const url = `https://bioregistry.io/dalia.oer:${item.id}`;

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className={'max-w-lg'}>
        <DialogHeader>
          <DialogTitle className={'flex items-center gap-2'}>
            Share this resource <CopyButton text={url} />
          </DialogTitle>
        </DialogHeader>
        <div className={'w-full font-semibold'}>
          <ScrollArea
            className={
              'max-w-md overflow-x-auto text-nowrap border border-primary p-1'
            }
            orientation={'horizontal'}
          >
            <pre className={'select-all'}>{url}</pre>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export type ShareDialogProps = {
  children: ReactNode;
  item: ResourceItem;
};

export default ShareDialog;
