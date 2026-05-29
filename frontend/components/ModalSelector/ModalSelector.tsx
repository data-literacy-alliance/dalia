'use client';
import React, { FC, useMemo, useState } from 'react';
import clsx from 'clsx';
import Tooltip from '@/components/Tooltip';
import { InputPriority } from '@/lib/types/UI';
import Button from '@/components/Button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { LabelValueChild } from '@/lib/types/Common';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronRightIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import Textbox from '@/components/Textbox';

const ModalSelector: FC<ModalSelectorProps> = ({
  label,
  tooltipMessage,
  priority,
  className,
  value,
  onChange,
  placeholder,
  changeLabel,
  items,
  searchable,
  query,
  onQueryChange,
}) => {
  const [selectedValues, setSelectedValues] = useState<LabelValueChild[]>([]);

  const valueLabels = useMemo(() => {
    if (value.length === 0) {
      return [];
    }

    const labels: string[] = [];

    let lastItem: LabelValueChild | undefined;
    value.forEach((val) => {
      // the first time => check items, afterward => check children of lastItem
      lastItem = !lastItem
        ? items.find((item) => item.value === val)
        : lastItem.children.find((item) => item.value === val);
      if (!lastItem) {
        return;
      }
      labels.push(lastItem.label);
    });
    return labels;
  }, [items, value]);

  const handleSelect = (item: LabelValueChild, level: number) => () => {
    setSelectedValues((oldValues) => {
      const newValues = [...oldValues];
      newValues[level] = item;
      if (newValues.length > level) {
        newValues.splice(level + 1);
      }
      onChange(newValues.map((v) => v.value));
      return newValues;
    });
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="relative w-full transition-colors hover:bg-accent">
          <label
            className={clsx(
              'absolute top-1 flex w-full flex-grow items-center justify-between px-3 text-base text-gray-500 transition-all duration-200'
            )}
          >
            <span>
              {label}
              {!!tooltipMessage && <Tooltip message={tooltipMessage}></Tooltip>}
            </span>
            {!!priority && (
              <span
                className={clsx('text-xs', {
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
            className={clsx(
              'flex items-start justify-between overflow-hidden border border-primary p-2',
              className
            )}
          >
            <div className="flex min-h-4 flex-wrap gap-1 pt-5">
              {valueLabels.length > 0
                ? valueLabels.map((item, index) => (
                    <span
                      key={index}
                      className="rounded bg-primary px-1 text-white"
                    >
                      {item}
                    </span>
                  ))
                : (placeholder ?? <i>No item selected.</i>)}
            </div>
          </div>
        </button>
      </DialogTrigger>
      <DialogContent
        className={'w-full md:min-w-[30rem] md:max-w-none'}
        style={{
          width: `${(selectedValues.length + 2) * 14}rem`,
        }}
      >
        <DialogHeader>
          <DialogTitle>{changeLabel}</DialogTitle>
        </DialogHeader>
        {searchable && (
          <Textbox
            value={query}
            onChange={(e) => onQueryChange?.(e.target.value)}
            placeholder={'Search...'}
          />
        )}
        <ScrollArea orientation={'horizontal'}>
          <div
            className={'flex max-h-96 flex-col gap-1 p-1 md:h-80 md:flex-row'}
          >
            <ScrollArea
              className={'h-full min-w-52 flex-1 border border-primary'}
              key={'root'}
            >
              {items.map((item) => (
                <button
                  className={cn(
                    'flex w-full cursor-pointer items-center p-2',
                    selectedValues.includes(item)
                      ? 'bg-primary text-white'
                      : 'text-primary'
                  )}
                  onClick={handleSelect(item, 0)}
                  key={item.value}
                >
                  <div className={'grow text-start'}>{item.label}</div>
                  {item.children.length > 0 && (
                    <ChevronRightIcon className={'h-4 w-4 shrink-0'} />
                  )}
                </button>
              ))}
            </ScrollArea>
            {selectedValues.map(
              (selectedValue, level) =>
                selectedValue.children.length > 0 && (
                  <ScrollArea
                    className={'h-full min-w-52 flex-1 border border-primary'}
                    key={selectedValue.value}
                  >
                    {selectedValue.children.map((item) => (
                      <button
                        className={cn(
                          'flex w-full cursor-pointer items-center p-2',
                          selectedValues.includes(item)
                            ? 'bg-primary text-white'
                            : 'text-primary'
                        )}
                        onClick={handleSelect(item, level + 1)}
                        key={item.value}
                      >
                        <div className={'grow text-start'}>{item.label}</div>
                        {item.children.length > 0 && (
                          <ChevronRightIcon
                            className={'h-4 w-4 flex-shrink-0'}
                          />
                        )}
                      </button>
                    ))}
                  </ScrollArea>
                )
            )}
          </div>
        </ScrollArea>
        <DialogFooter>
          <DialogClose asChild>
            <Button dark small type={'button'}>
              Save
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export type ModalSelectorProps = {
  label: string;
  tooltipMessage?: string;
  priority?: InputPriority;
  className?: string;
  placeholder?: string;
  value: string[];
  onChange: (newValue: string[]) => void;
  changeLabel: string;
  items: LabelValueChild[];
  searchable?: boolean;
  query?: string;
  onQueryChange?: (query: string) => void;
};

export default ModalSelector;
