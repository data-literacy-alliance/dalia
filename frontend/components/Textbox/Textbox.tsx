import React, { forwardRef, useId } from 'react';
import clsx from 'clsx';
import Tooltip from '@/components/Tooltip';
import { InputPriority } from '@/lib/types/UI';

const Textbox = forwardRef<HTMLDivElement, TextboxProps>(
  (
    {
      label,
      numberOfLines,
      inputClassname,
      tooltipMessage,
      priority,
      ...props
    },
    ref
  ) => {
    const id = useId();
    const Component = numberOfLines && numberOfLines > 1 ? 'textarea' : 'input';

    return (
      <div className={clsx('relative', props.className)} ref={ref}>
        <Component
          id={id}
          placeholder={' '}
          rows={numberOfLines}
          {...props}
          className={clsx(
            'group peer block h-full w-full appearance-none rounded-sm border border-primary px-3 outline-none ring-primary focus:ring-1',
            !!label && 'pb-2 pt-6',
            inputClassname
          )}
        />
        {!!label && (
          <label
            htmlFor={id}
            className={clsx(
              'group-focused:text-primary absolute left-px right-0.5 top-px flex w-auto transform justify-between bg-white px-3 pe-4 pt-0.5 text-sm text-daliaGray-300 duration-300 peer-focus:text-primary lg:text-base'
            )}
          >
            <div className={'flex grow gap-2'}>
              {label}{' '}
              {!!tooltipMessage && <Tooltip message={tooltipMessage}></Tooltip>}
            </div>
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
        )}
      </div>
    );
  }
);

Textbox.displayName = 'Textbox';

export type TextboxProps = Omit<
  React.DetailedHTMLProps<
    React.InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement>,
    HTMLInputElement | HTMLTextAreaElement
  >,
  'ref'
> & {
  label?: string;
  numberOfLines?: number;
  inputClassname?: string;
  tooltipMessage?: string;
  priority?: InputPriority;
};

export default Textbox;
