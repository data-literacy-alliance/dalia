import React, { forwardRef } from 'react';
import clsx from 'clsx';
import { IconSource } from '@/components/Icon/IconSource';

const Icon = forwardRef<HTMLElement, IconProps>(
  ({ source, size = 24, color, className, ...props }, ref) => {
    return (
      <i
        {...props}
        className={clsx(`icon-${source}`, className)}
        style={{
          fontSize: size,
          lineHeight: `${size - 1}px`,
          color,
        }}
        ref={ref}
      />
    );
  }
);

Icon.displayName = 'Icon';

export type IconProps = Omit<
  React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement>,
  'style' | 'ref'
> & {
  source: IconSource;
  size?: number;
  color?: string;
};

export default Icon;
