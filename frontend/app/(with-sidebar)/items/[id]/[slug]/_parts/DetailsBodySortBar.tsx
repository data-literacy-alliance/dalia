'use client';
import React, { FC, useEffect } from 'react';
import { HFlex } from '@/components/Flex';
import IconButton, { IconButtonGroup } from '@/components/IconButton';
import { cn } from '@/lib/utils';
import useWindowDimensions, { ScreenSizes } from '@/lib/useWindowDimensions';

const DetailsBodySortBar: FC<DetailsBodySortBarProps> = ({
  onChangeView,
  view,
}) => {
  const { width } = useWindowDimensions();

  useEffect(() => {
    if (width < ScreenSizes.xl) {
      onChangeView('grid');
    }
  }, [onChangeView, width]);

  return (
    <HFlex
      className={cn(
        'h-10 w-full items-center justify-end border border-x-0 border-t-0 border-primary max-xl:hidden'
      )}
    >
      <IconButtonGroup
        value={view}
        onChange={(newValue) => onChangeView(newValue as 'list' | 'grid')}
      >
        <IconButton
          source={'grid'}
          small
          key={'grid'}
          value={'grid'}
          iconProps={{ size: 24 }}
          borderless
          className={cn('border border-primary')}
        />
        <IconButton
          source={'list'}
          small
          key={'list'}
          value={'list'}
          iconProps={{ size: 24 }}
          borderless
          className={cn('border border-primary')}
        />
      </IconButtonGroup>
    </HFlex>
  );
};

export type DetailsBodySortBarProps = {
  view: 'list' | 'grid';
  onChangeView: (view: 'list' | 'grid') => void;
};

export default DetailsBodySortBar;
