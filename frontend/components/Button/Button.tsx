import React, { ComponentProps, forwardRef } from 'react';
import { IconSource } from '@/components/Icon';
import Link, { LinkProps } from 'next/link';
import Icon from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';

const Button = forwardRef<HTMLElement, ButtonProps>(
  (
    {
      children,
      small,
      leftAligned,
      dark,
      leadIcon,
      trailIcon,
      trailIconSize = 14,
      borderless,
      link,
      noPadding,
      ...props
    },
    ref
  ) => {
    return !link ? (
      <button
        type={'button'}
        {...props}
        // @ts-expect-error multi type ref
        ref={ref}
        className={cn(
          'flex items-center justify-center gap-1.5 overflow-hidden outline-none hover:bg-accent focus:bg-accent 2xl:px-[1.563rem]',
          {
            'px-4': !noPadding,
            'border border-primary disabled:border-daliaGray-300': !borderless,
            'h-10': small,
            'h-[3.125rem] min-w-0 2xl:min-w-[9.375rem]': !small,
            'bg-primary text-white hover:text-primary focus:text-primary disabled:bg-daliaGray-200 disabled:text-white':
              dark,
            'bg-white text-primary disabled:bg-white disabled:text-daliaGray-300':
              !dark,
            'justify-start': leftAligned,
          },
          props.className
        )}
      >
        {!!leadIcon && <Icon source={leadIcon} size={14} />}
        {children}
        {!!trailIcon && <Icon source={trailIcon} size={trailIconSize} />}
      </button>
    ) : (
      <Link
        role={'button'}
        {...props}
        // @ts-expect-error multi type ref
        ref={ref}
        aria-disabled={props.disabled}
        {...(props.disabled ? {} : link)}
        className={cn(
          'flex items-center justify-center gap-1.5 overflow-hidden outline-none hover:bg-accent focus:bg-accent 2xl:px-[1.563rem]',
          {
            'px-4': !noPadding,
            'border border-primary disabled:border-daliaGray-300': !borderless,
            'h-10': small,
            'h-[3.125rem] min-w-0 2xl:min-w-[9.375rem]': !small,
            'bg-primary text-white hover:text-primary focus:text-primary disabled:bg-daliaGray-200 disabled:text-white':
              dark,
            'bg-white text-primary disabled:bg-white disabled:text-daliaGray-300':
              !dark,
            'justify-start': leftAligned,
          },
          props.className
        )}
      >
        {!!leadIcon && <Icon source={leadIcon} size={14} />}
        {children}
        {!!trailIcon && <Icon source={trailIcon} size={trailIconSize} />}
      </Link>
    );
  }
);

Button.displayName = 'Button';

export type ButtonProps = {
  children?: React.ReactNode;
  className?: string;
  onClick?: (event: MouseEvent) => void | Promise<void>;
  small?: boolean;
  value?: string;
  dark?: boolean;
  borderless?: boolean;
  leadIcon?: IconSource;
  trailIcon?: IconSource;
  leftAligned?: boolean;
  noPadding?: boolean;
  trailIconSize?: number;
  disabled?: boolean;
  style?: React.CSSProperties;
  name?: string;
} & (
  | {
      link: Omit<LinkProps, 'children'> & {
        target?: HTMLAnchorElement['target'];
      };
    }
  | {
      link?: undefined;
      type?: ComponentProps<'button'>['type'];
    }
);

export default Button;
