'use client';
import React, { FC, ReactNode, useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import CopyButton from '@/components/CopyButton';
import { ScrollArea } from '@/components/ui/scroll-area';

const ShareDialog: FC<ShareDialogProps> = ({ children, userUUID }) => {
  const [url, setUrl] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      setUrl(url.protocol + '//' + url.host + '/profiles/' + userUUID);
    } else {
      setUrl('');
    }
  }, [userUUID]);

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className={'max-w-lg'}>
        <DialogHeader>
          <DialogTitle className={'flex items-center gap-2'}>
            Share Profile <CopyButton text={url} />
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
  userUUID: string;
};

export default ShareDialog;
