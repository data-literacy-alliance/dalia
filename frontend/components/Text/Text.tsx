import React, { forwardRef } from 'react';
import clsx from 'clsx';

const Text = forwardRef<HTMLSpanElement, TextProps>(
  ({ variant = 'text', ...props }, ref) => {
    return (
      <span
        {...props}
        className={clsx(`text-${variant}`, props.className)}
        ref={ref}
      />
    );
  }
);

Text.displayName = 'Text';

export type TextVariant =
  | 'h1'
  | 'h2'
  | 'h3'
  | 'h4'
  | 'subheader'
  | 'footerTitle'
  | 'button'
  | 'mobileText'
  | 'text'
  | 'footerText';

export type TextProps = React.DetailedHTMLProps<
  React.HTMLAttributes<HTMLSpanElement>,
  HTMLSpanElement
> & {
  variant?: TextVariant;
};

export default Text;
