'use client';

import React, { FC, useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Loader2Icon, SquareCheckBigIcon, SquareIcon } from 'lucide-react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';
import Tooltip from '@/components/Tooltip';
import { InputPriority } from '@/lib/types/UI';
import Icon from '@/components/Icon';
import clsx from 'clsx';
import { useWidth } from '@/lib/useWidth';
import { SuggestionLicense } from '@/lib/types/Suggestion';
import { MSelect2Props } from '@/components/MSelect/MSelect2';
import Link from 'next/link';

const MSelect2: FC<MSelectLicenseProps> = ({
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
}) => {
  const [open, setOpen] = useState(false);

  const [ref, width] = useWidth<HTMLButtonElement>();

  const selectedLabel =
    values.length >= maxNumberToShow
      ? `${values.length} selected`
      : values.map((item) => item.licenseName).join(', ');

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button className={cn('relative', className)} ref={ref}>
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
                'flex cursor-pointer items-start justify-between border border-primary p-2',
                innerClassName
              )}
            >
              <div className="flex flex-wrap gap-1 px-1 pt-4">
                {values.length > 0 ? selectedLabel : placeholder}
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
                onValueChange={onQueryChange}
                className={
                  'h-8 w-full border border-primary px-2 py-4 outline-none ring-primary focus:ring-1'
                }
              />
              {loading && (
                <Loader2Icon className={'absolute end-1 top-1 animate-spin'} />
              )}
            </div>
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
                    className={'flex gap-2'}
                  >
                    {values.find((v) => v.value === item.value) ? (
                      <SquareCheckBigIcon className={'mr-2 h-4 w-4'} />
                    ) : (
                      <SquareIcon className={'mr-2 h-4 w-4'} />
                    )}
                    <div>
                      <div>{item.licenseName}</div>
                      <div className={'line-clamp-2 text-xs'}>
                        {item.licenseDescription}
                      </div>
                      {item.licenseLink && (
                        <Link href={item.licenseLink}>More info</Link>
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
              <CommandEmpty>No item to select.</CommandEmpty>
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

type MSelectLicenseProps = Omit<
  MSelect2Props,
  'items' | 'onChange' | 'values'
> & {
  items: SuggestionLicense[];
  values: SuggestionLicense[];
  onChange: (values: SuggestionLicense[]) => void;
  label: string;
  priority?: InputPriority;
  tooltipMessage?: string;
  single?: boolean;
  innerClassName?: string;
  shouldFilter?: boolean;
  query?: string;
  onQueryChange?: (query: string) => void;
  loading?: boolean;
};

export default MSelect2;
