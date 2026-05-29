'use client';
import React, { useMemo, useRef, useState } from 'react';
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from '@/components/ui/popover';
import Textbox from '@/components/Textbox';
import { TextboxProps } from '@/components/Textbox/Textbox';
import { LabelValuePair } from '@/lib/types/Common';
import { useResizeObserver } from 'usehooks-ts';
import { CheckIcon, Loader2 } from 'lucide-react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';

const Autocomplete = <T extends LabelValuePair>({
  value,
  onChange,
  searchValue,
  loading,
  onSearchValueChange,
  items,
  wrapperClassName,
  ...textboxProps
}: AutocompleteProps<T>) => {
  // @Look https://github.com/Balastrong/shadcn-autocomplete-demo/blob/main/src/components/autocomplete.tsx

  const textboxRef = useRef<HTMLDivElement>(null);
  const { width } = useResizeObserver({
    ref: textboxRef,
  });

  const [open, setOpen] = useState(false);

  // convert LabelValuePairs to Record<Value, T>
  const itemsMap = useMemo(
    () =>
      items.reduce(
        (acc, item) => {
          acc[item.value] = item;
          return acc;
        },
        {} as Record<string, T>
      ),
    [items]
  );

  const reset = () => {
    onChange(null);
    onSearchValueChange('');
  };

  const onInputBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    if (
      !e.relatedTarget?.hasAttribute('cmdk-list') &&
      (!value || itemsMap[value].label !== searchValue)
    ) {
      reset();
    }
  };

  const onSelectItem = (inputValue: string) => {
    if (inputValue === value) {
      reset();
    } else {
      onSearchValueChange(itemsMap[inputValue].label ?? '');
      // onChange(itemsMap[inputValue]);
    }
    setOpen(false);
  };

  return (
    <div className="flex w-full items-center">
      <Popover open={open} onOpenChange={setOpen}>
        <Command shouldFilter={false}>
          <PopoverAnchor asChild>
            <CommandInput
              asChild
              value={searchValue}
              onValueChange={onSearchValueChange}
              onKeyDown={(e) => setOpen(e.key !== 'Escape')}
              onMouseDown={() => setOpen((open) => !!searchValue || !open)}
              onFocus={() => setOpen(true)}
              onBlur={onInputBlur}
              wrapperClassName={wrapperClassName}
            >
              <Textbox {...textboxProps} />
            </CommandInput>
          </PopoverAnchor>
          {!open && <CommandList aria-hidden="true" className="hidden" />}
          <PopoverContent
            onOpenAutoFocus={(e) => e.preventDefault()}
            onInteractOutside={(e) => {
              if (
                e.target instanceof Element &&
                e.target.hasAttribute('cmdk-input')
              ) {
                e.preventDefault();
              }
            }}
            className={'p-0'}
            style={{
              width: `${width}px`,
            }}
          >
            <CommandList>
              {loading ? (
                <div className={'flex gap-2 p-2 text-primary'}>
                  <Loader2 className="animate-spin" /> Loading...
                </div>
              ) : (
                <>
                  <CommandEmpty className={'p-2 text-primary'}>
                    No options available.
                  </CommandEmpty>
                  <CommandGroup>
                    {items.map((item) => (
                      <CommandItem
                        key={item.value}
                        value={item.value}
                        onMouseDown={(e) => e.preventDefault()}
                        onSelect={onSelectItem}
                      >
                        <CheckIcon
                          className={cn(
                            'mr-2 h-4 w-4',
                            value === item.value ? 'opacity-100' : 'opacity-0'
                          )}
                        />
                        {item.label}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </PopoverContent>
        </Command>
      </Popover>
    </div>
  );
};

export type AutocompleteProps<T extends LabelValuePair> = Omit<
  TextboxProps,
  'value' | 'onChange'
> & {
  value: string | null;
  onChange: (value: T | null) => void;
  searchValue: string;
  onSearchValueChange: (searchValue: string) => void;
  loading: boolean;
  items: T[];
  wrapperClassName?: string;
};

export default Autocomplete;
