import React, { ComponentProps, FC, useState } from 'react';
import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

const AccessibilityButton: FC<AccessibilityButtonProps> = ({
  states,
  className,
  name,
  ...props
}) => {
  const [stateIndex, setStateIndex] = useState(() => {
    const indexStr = localStorage.getItem(name);
    if (indexStr) {
      const index = Number(indexStr);
      if (!isNaN(index) && index >= 0) {
        return (index + 1) % states.length;
      }
    }
    return 0;
  });

  if (states.length < 1) {
    throw new Error('No accessibility state provided for AccessibilityButton.');
  }

  const state = states[stateIndex];

  const handleAction = (action: AccessibilityButtonState['onAction']) => () => {
    action();
    const nextIndex = (stateIndex + 1) % states.length;
    localStorage.setItem(name, stateIndex.toString());
    setStateIndex(nextIndex);
  };

  return (
    <button
      {...props}
      className={cn(
        'flex flex-col items-center justify-center gap-2 border border-primary p-2 transition-colors hover:bg-daliaGray-200 disabled:text-daliaGray-300 hover:disabled:bg-inherit',
        className
      )}
      aria-disabled={state.disabled}
      onClick={handleAction(state.onAction)}
    >
      <span>{state.label}</span>
      <Progress value={state.point} className={'w-[75%]'} />
    </button>
  );
};

export type AccessibilityButtonState = {
  label: string;
  point: number;
  onAction: () => void;
  disabled?: boolean;
};

export type AccessibilityButtonProps = Omit<
  ComponentProps<'button'>,
  'children' | 'onClick'
> & {
  states: AccessibilityButtonState[];
  name: string;
};

export default AccessibilityButton;
