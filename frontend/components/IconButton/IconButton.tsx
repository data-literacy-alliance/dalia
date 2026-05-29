import React, { ComponentProps, forwardRef, MouseEventHandler } from 'react';
import Icon, { IconProps, IconSource } from '@/components/Icon';
import Link, { LinkProps } from 'next/link';
import { cn } from '@/lib/utils';

const IconButton = forwardRef<HTMLElement, IconButtonProps>(
  (
    { source, small, iconProps, link, dark, borderless, className, ...props },
    ref
  ) => {
    return !link || (link && props.disabled) ? (
      <button
        type={'button'}
        {...props}
        className={cn(
          'flex items-center justify-center outline-none hover:bg-accent focus:bg-accent',
          {
            'h-[3.125rem] w-[3.125rem]': !small,
            'h-[2.5rem] w-[2.5rem]': small,
            'border border-primary disabled:border-daliaGray-300': !borderless,
            'bg-primary text-white hover:text-primary focus:text-primary disabled:bg-daliaGray-200 disabled:text-white':
              dark,
            'bg-white text-primary disabled:bg-white disabled:text-daliaGray-300':
              !dark,
          },
          className
        )}
        // @ts-expect-error multi type ref
        ref={ref}
      >
        <Icon source={source} size={small ? 14 : 24} {...iconProps} />
      </button>
    ) : (
      <Link
        role={'button'}
        {...props}
        {...link}
        className={cn(
          'flex items-center justify-center outline-none hover:bg-accent focus:bg-accent',
          {
            'h-[3.125rem] w-[3.125rem]': !small,
            'h-[2.5rem] w-[2.5rem]': small,
            'border border-primary disabled:border-daliaGray-300': !borderless,
            'bg-primary text-white hover:text-primary focus:text-primary disabled:bg-daliaGray-200 disabled:text-white':
              dark,
            'bg-white text-primary disabled:bg-white disabled:text-daliaGray-300':
              !dark,
          },
          className
        )}
        aria-disabled={props.disabled}
        // @ts-expect-error multi type ref
        ref={ref}
      >
        <Icon source={source} size={small ? 14 : 24} {...iconProps} />
      </Link>
    );
  }
);

IconButton.displayName = 'IconButton';

export type IconButtonProps = Pick<
  ComponentProps<'button'>,
  'title' | 'value' | 'disabled' | 'tabIndex' | 'type'
> & {
  source: IconSource;
  onClick?: MouseEventHandler;
  small?: boolean;
  dark?: boolean;
  link?: Omit<LinkProps, 'children'>;
  borderless?: boolean;
  iconProps?: Omit<IconProps, 'source'>;
  className?: string;
};

export default IconButton;
