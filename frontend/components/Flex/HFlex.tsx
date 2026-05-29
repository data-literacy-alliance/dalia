import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

const HFlex = forwardRef<HTMLDivElement, HFlexProps>((props, ref) => {
  return (
    <div
      {...props}
      className={cn('flex flex-row', props.className)}
      ref={ref}
    />
  );
});

HFlex.displayName = 'HFlex';

export type HFlexProps = React.DetailedHTMLProps<
  React.HTMLAttributes<HTMLDivElement>,
  HTMLDivElement
>;

export default HFlex;
