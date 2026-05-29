'use client';
import React, { FC, ReactNode } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { citationProviders } from '@/lib/citations';
import CopyButton from '@/components/CopyButton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { ResourceItem } from '@/lib/types/ItemTypes';

const CiteDialog: FC<CiteDialogProps> = ({ children, item }) => {
  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className={'max-w-lg'}>
        <DialogHeader>
          <DialogTitle>Cite this resource</DialogTitle>
        </DialogHeader>
        <div className={'w-full space-y-4'}>
          {citationProviders.map((provider) => {
            const text = provider.generator(item);
            return (
              <div
                key={provider.title}
                className={'flex w-full flex-col items-center space-y-1'}
              >
                <div
                  className={
                    'flex w-full items-center justify-start gap-2 ps-2 font-semibold'
                  }
                >
                  <CopyButton text={text} />
                  {provider.title}
                </div>
                <ScrollArea
                  className={cn(
                    'max-w-md overflow-x-auto border border-primary p-1',
                    !provider.multiline && 'text-nowrap'
                  )}
                  orientation={'horizontal'}
                >
                  <pre className={'select-all'}>{text}</pre>
                </ScrollArea>
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export type CiteDialogProps = {
  children: ReactNode;
  item: ResourceItem;
};

export default CiteDialog;
