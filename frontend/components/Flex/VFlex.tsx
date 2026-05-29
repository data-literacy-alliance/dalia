import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

const VFlex = forwardRef<HTMLDivElement, VFlexProps>((props, ref) => {
  return (
    <div
      {...props}
      className={cn('flex flex-col', props.className)}
      ref={ref}
    />
  );
});

VFlex.displayName = 'VFlex';

export type VFlexProps = React.DetailedHTMLProps<
  React.HTMLAttributes<HTMLDivElement>,
  HTMLDivElement
>;

export default VFlex;
