'use client';
import React, { FC, useState } from 'react';
import Text from '@/components/Text';
import clsx from 'clsx';

export type TooltipProps = {
  message: string;
  className?: string;
};

const Tooltip: FC<TooltipProps> = ({ message, className }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className={clsx(
        'relative ms-1 inline-flex items-center align-top',
        className
      )}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onTouchStart={() => setShowTooltip(!showTooltip)}
    >
      <Text
        className={
          'flex h-4 w-4 cursor-default place-content-center rounded-full bg-daliaGray-200 text-xs font-semibold text-white'
        }
      >
        i
      </Text>

      {showTooltip && (
        <div
          className={
            'absolute bottom-1/2 z-10 mt-2 w-max max-w-60 -translate-x-1/2 translate-y-[-10px] transform whitespace-normal rounded-sm bg-daliaGray-200 p-2 text-sm text-primary shadow-lg lg:left-1/2 lg:max-w-md'
          }
        >
          {message}
        </div>
      )}
    </div>
  );
};

export default Tooltip;
