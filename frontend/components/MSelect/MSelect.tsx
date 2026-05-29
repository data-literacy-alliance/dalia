'use client';

import React, { FC, useState } from 'react';
import { LabelValuePair } from '@/lib/types/Common';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { ChevronsUpDown, SquareCheckBigIcon, SquareIcon } from 'lucide-react';
import {
  Command,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';

const MSelect: FC<MSelectProps> = ({
  items,
  values,
  onChange,
  placeholder,
  name,
  className,
  maxNumberToShow = 3,
}) => {
  const [open, setOpen] = useState(false);

  const selectedLabel =
    values.length >= maxNumberToShow
      ? `${values.length} selected`
      : items
          .filter((item) => values.includes(item.value))
          .map((item) => item.label)
          .join(', ');

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            className={cn(
              'flex items-center justify-between gap-2 border border-primary p-2',
              className
            )}
          >
            <div className={'line-clamp-1 text-left'}>
              {values.length > 0 ? selectedLabel : placeholder}
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </button>
        </PopoverTrigger>
        <PopoverContent>
          <Command>
            <CommandInput
              placeholder="Search options"
              className={'h-9 w-full p-1'}
            />
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
                      const newValues = [...values];
                      if (newValues.includes(newValue)) {
                        newValues.splice(newValues.indexOf(newValue), 1);
                      } else {
                        newValues.push(newValue);
                      }
                      onChange(newValues);
                    }}
                  >
                    {values.includes(item.value) ? (
                      <SquareCheckBigIcon className={'mr-2 h-4 w-4'} />
                    ) : (
                      <SquareIcon className={'mr-2 h-4 w-4'} />
                    )}
                    <span>{item.label}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {name &&
        values.map((value) => (
          <input key={value} name={name} value={value} type={'hidden'} />
        ))}
    </>
  );
};

export type MSelectProps = {
  items: LabelValuePair[];
  values: string[];
  onChange: (newValues: string[]) => void;
  placeholder?: string;
  maxNumberToShow?: number;
  name?: string;
  className?: string;
};

export default MSelect;
