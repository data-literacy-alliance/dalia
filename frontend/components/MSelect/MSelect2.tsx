'use client';

import React, { FC, useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import {
  Loader2Icon,
  SquareCheckBigIcon,
  SquareChevronRightIcon,
  SquareIcon,
} from 'lucide-react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { MSelectProps } from '@/components/MSelect/MSelect';
import Tooltip from '@/components/Tooltip';
import { InputPriority } from '@/lib/types/UI';
import Icon from '@/components/Icon';
import clsx from 'clsx';
import { useWidth } from '@/lib/useWidth';
import { LabelValuePair } from '@/lib/types/Common';

const MSelect2: FC<MSelect2Props> = ({
  items,
  values,
  onChange,
  placeholder,
  name,
  className,
  maxNumberToShow = 3,
  label,
  tooltipMessage,
  priority,
  single,
  innerClassName,
  shouldFilter,
  query,
  onQueryChange,
  loading,
  disabled,
  onOpenChange,
}) => {
  const [open, setOpen] = useState(false);

  const [ref, width] = useWidth<HTMLButtonElement>();

  const selectedLabel = values.map((v) => v.label).join(', ');

  const isEmpty = values.length === 0 || selectedLabel === '';

  return (
    <>
      <Popover
        open={open}
        onOpenChange={(newOpen) => {
          setOpen(newOpen);
          onOpenChange?.(newOpen);
        }}
      >
        <PopoverTrigger asChild>
          <button
            className={cn('relative', className)}
            ref={ref}
            disabled={disabled}
          >
            <label
              className={
                'absolute top-1 flex w-full flex-grow items-center justify-between px-3 text-base text-gray-500 transition-all duration-200'
              }
            >
              <span>
                {label}
                {!!tooltipMessage && (
                  <Tooltip message={tooltipMessage}></Tooltip>
                )}
              </span>
              {!!priority && (
                <span
                  className={cn('text-xs', {
                    'text-dalia4': priority === 'Mandatory',
                    'text-dalia5': priority === 'Recommended',
                    'text-dalia1': priority === 'Optional',
                  })}
                >
                  {priority}
                </span>
              )}
            </label>

            <div
              className={cn(
                'flex cursor-pointer w-full h-full items-start justify-between border border-primary p-2',
                innerClassName
              )}
            >
              <div className="flex flex-wrap gap-1 px-1 pt-4">
                {!isEmpty ? selectedLabel : placeholder}
              </div>
              <Icon
                source={'chevron-down'}
                className={clsx('mr-1', !!priority && 'mt-6')}
                size={12}
              />
            </div>
          </button>
        </PopoverTrigger>
        <PopoverContent
          className={'p-0'}
          align={'start'}
          style={{ minWidth: width }}
        >
          <Command shouldFilter={shouldFilter}>
            <div className={'relative'}>
              <CommandInput
                placeholder={'Search...'}
                value={query}
                disabled={disabled}
                onValueChange={onQueryChange}
                className={
                  'h-8 w-full border border-primary px-2 py-4 outline-none ring-primary focus:ring-1'
                }
              />
              {loading && (
                <Loader2Icon className={'absolute end-1 top-1 animate-spin'} />
              )}
            </div>
            {loading ? (
              <Loader2Icon className={'animate-spin p-2'} />
            ) : (
              <CommandEmpty>No item to select.</CommandEmpty>
            )}
            <CommandList
              style={{
                scrollbarColor: 'var(--primaryColor) #DDD',
                scrollbarWidth: 'thin',
              }}
            >
              <CommandGroup>
                {items.map((item) => (
                  <CommandItem
                    key={item.value}
                    value={item.value}
                    onSelect={(newValue) => {
                      if (!single) {
                        const newValues = [...values];
                        const newValueIndex = newValues.findIndex(
                          (v) => v.value === newValue
                        );
                        if (newValueIndex > -1) {
                          newValues.splice(newValueIndex, 1);
                        } else {
                          newValues.push(item);
                        }
                        onChange(newValues);
                      } else {
                        // single selection
                        if (values.length > 0 && values[0].value === newValue) {
                          onChange([]);
                        } else {
                          onChange([item]);
                        }
                      }
                    }}
                  >
                    {values.find((v) => v.value === item.value) ? (
                      single ? (
                        <SquareChevronRightIcon className={'mr-2 h-4 w-4'} />
                      ) : (
                        <SquareCheckBigIcon className={'mr-2 h-4 w-4'} />
                      )
                    ) : (
                      <SquareIcon className={'mr-2 h-4 w-4'} />
                    )}
                    {item.label}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {name &&
        values.map((value) => (
          <input
            key={value.value}
            name={name}
            value={value.value}
            type={'hidden'}
          />
        ))}
    </>
  );
};

export type MSelect2Props = Omit<MSelectProps, 'values' | 'onChange'> & {
  values: LabelValuePair[];
  onChange: (values: LabelValuePair[]) => void;
  label: string;
  priority?: InputPriority;
  tooltipMessage?: string;
  single?: boolean;
  innerClassName?: string;
  shouldFilter?: boolean;
  query?: string;
  onQueryChange?: (query: string) => void;
  loading?: boolean;
  disabled?: boolean;
  onOpenChange?: (newOpen: boolean) => void;
};
export default MSelect2;
