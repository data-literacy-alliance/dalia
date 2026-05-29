'use client';
import React, { FC } from 'react';
import clsx from 'clsx';
import styles from './Select.module.css';
import * as RSelect from '@radix-ui/react-select';
import Icon from '@/components/Icon';

const Select: FC<SelectProps> = ({ items, placeholder, className, name }) => {
  return (
    <RSelect.Root name={name}>
      <RSelect.Trigger
        aria-label={placeholder}
        className={clsx(styles.root, className)}
      >
        <RSelect.Value placeholder={placeholder} />
        <RSelect.Icon className={'ms-1'}>
          <Icon source={'chevron-down'} size={12} />
        </RSelect.Icon>
      </RSelect.Trigger>
      <RSelect.Portal>
        <RSelect.Content className="overflow-hidden bg-white border border-primary">
          <RSelect.ScrollUpButton className="flex items-center justify-center bg-white cursor-default">
            <Icon source={'chevron-up'} size={12} />
          </RSelect.ScrollUpButton>
          <RSelect.Viewport className="p-[5px]">
            {items.map((item) => (
              <RSelect.Item
                value={item.value}
                key={item.value}
                className="text-[13px] leading-none flex items-center h-[25px] pr-[35px] pl-[25px] relative select-none data-[disabled]:pointer-events-none data-[highlighted]:outline-none data-[highlighted]:bg-accent data-[highlighted]:text-primary"
              >
                <RSelect.ItemText>{item.label}</RSelect.ItemText>
                <RSelect.ItemIndicator className="absolute left-0 w-[25px] inline-flex items-center justify-center">
                  <Icon source={'checkmark'} size={12} />
                </RSelect.ItemIndicator>
              </RSelect.Item>
            ))}
          </RSelect.Viewport>
        </RSelect.Content>
      </RSelect.Portal>
    </RSelect.Root>
  );
};

export type SelectItem = {
  textValue?: string;
  disabled?: boolean;
  value: string;
  label: string;
};

export type SelectProps = {
  className?: string;
  items: SelectItem[];
  placeholder?: string;
  name?: string;
};

export default Select;
