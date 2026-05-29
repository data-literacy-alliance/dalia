'use client';
import React, { forwardRef } from 'react';
import * as Accordion from '@radix-ui/react-accordion';
import clsx from 'clsx';
import {
  AccordionContentProps,
  AccordionTriggerProps,
} from '@radix-ui/react-accordion';
import Icon from '@/components/Icon';

export const AccordionItem = forwardRef<
  HTMLDivElement,
  Accordion.AccordionItemProps & React.RefAttributes<HTMLDivElement>
>(({ children, className, ...props }, forwardedRef) => (
  <Accordion.Item
    className={clsx('mt-px overflow-hidden first:mt-0', className)}
    {...props}
    ref={forwardedRef}
  >
    {children}
  </Accordion.Item>
));
AccordionItem.displayName = 'AccordionItem';

export const AccordionTrigger = forwardRef<
  HTMLButtonElement,
  AccordionTriggerProps &
    React.RefAttributes<HTMLButtonElement> & { hideIcon?: boolean }
>(({ children, className, hideIcon, ...props }, forwardedRef) => (
  <Accordion.Header className="flex">
    <Accordion.Trigger
      className={clsx(
        'group flex flex-1 cursor-default items-center justify-between border-b border-primary bg-white px-5 leading-none shadow-sm outline-none hover:bg-daliaGray-100 focus:bg-daliaGray-100',
        className
      )}
      {...props}
      ref={forwardedRef}
    >
      {children}
      {!hideIcon && (
        <Icon
          source={'chevron-down'}
          size={14}
          className="transition-transform duration-300 ease-[cubic-bezier(0.87,_0,_0.13,_1)] group-data-[state=open]:rotate-180"
          aria-hidden
        />
      )}
    </Accordion.Trigger>
  </Accordion.Header>
));
AccordionTrigger.displayName = 'AccordionTrigger';

export const AccordionContent = forwardRef<
  HTMLDivElement,
  AccordionContentProps & React.RefAttributes<HTMLDivElement>
>(({ children, className, ...props }, forwardedRef) => (
  <Accordion.Content
    className={clsx(
      'overflow-hidden border-b border-primary data-[state=closed]:animate-slideUp data-[state=open]:animate-slideDown',
      className
    )}
    {...props}
    ref={forwardedRef}
  >
    {children}
  </Accordion.Content>
));
AccordionContent.displayName = 'AccordionContent';
