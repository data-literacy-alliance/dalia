'use client';
import React, { FC, MouseEventHandler, ReactNode } from 'react';
import * as Accordion from '@radix-ui/react-accordion';
import { AccordionSingleProps } from '@radix-ui/react-accordion';
import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/Collapsible/utils';
import { cn } from '@/lib/utils';

const Collapsible: FC<CollapsibleProps> = ({
  children,
  title,
  defaultOpen,
  hideIcon,
  triggerClassName,
  contentClassName,
  onTitleClick,
  ...props
}) => {
  return (
    <Accordion.Root
      collapsible
      {...props}
      type={'single'}
      defaultValue={defaultOpen ? 'item' : undefined}
    >
      <AccordionItem value={'item'}>
        <AccordionTrigger
          hideIcon={hideIcon}
          className={cn(triggerClassName)}
          onClick={onTitleClick}
        >
          {title}
        </AccordionTrigger>
        <AccordionContent className={cn(contentClassName)}>
          {children}
        </AccordionContent>
      </AccordionItem>
    </Accordion.Root>
  );
};

export type CollapsibleProps = Omit<
  AccordionSingleProps,
  'type' | 'defaultValue' | 'title'
> & {
  triggerClassName?: string;
  contentClassName?: string;
  children: ReactNode;
  title: ReactNode;
  defaultOpen?: boolean;
  hideIcon?: boolean;
  onTitleClick?: MouseEventHandler<HTMLButtonElement>;
};

export default Collapsible;
