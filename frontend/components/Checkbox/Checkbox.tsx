import React, { FC, ReactNode, useMemo } from 'react';
import * as RCheckbox from '@radix-ui/react-checkbox';
import { HFlex } from '@/components/Flex';
import Text from '@/components/Text';
import { cn } from '@/lib/utils';

let checkboxId = 0;

const Checkbox: FC<CheckboxProps> = ({ label, ...props }) => {
  const id = useMemo(() => `_checkbox_${++checkboxId}`, []);

  return (
    <HFlex className={'gap-2'}>
      <RCheckbox.Root
        {...props}
        className={cn(
          'flex size-[1.875rem] items-center shrink-0 justify-center rounded-sm border border-primary bg-white hover:bg-daliaGray-100 disabled:cursor-not-allowed',
          props.className
        )}
        id={id}
      >
        <RCheckbox.Indicator className={'block h-5 w-5'}>
          <div className={'h-full w-full bg-primary'} />
        </RCheckbox.Indicator>
      </RCheckbox.Root>
      {!!label &&
        (typeof label === 'string' ? (
          <label htmlFor={id} className={cn('flex items-center leading-none', props.disabled && 'text-daliaGray-300')}>
            <Text>{label}</Text>
          </label>
        ) : (
          label
        ))}
    </HFlex>
  );
};

export type CheckboxProps = Omit<RCheckbox.CheckboxProps, 'asChild' | 'id'> & {
  label?: string | ReactNode;
};

export default Checkbox;
