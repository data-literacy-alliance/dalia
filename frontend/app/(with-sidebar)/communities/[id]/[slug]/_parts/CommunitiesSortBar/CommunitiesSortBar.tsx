import React, { FC } from 'react';
import { HFlex } from '@/components/Flex';
import IconButton, { IconButtonGroup } from '@/components/IconButton';
import clsx from 'clsx';
import { ItemObject } from '@/lib/types/ItemTypes';
import Text from '@/components/Text';

const CommunitiesSortBar: FC<SortBarProps> = ({
  view,
  onViewChange,
  className,
  itemsShowing,
  items,
}) => {
  return (
    <HFlex
      className={clsx(
        'flex h-10 w-full items-center justify-between border border-x-0 border-primary',
        className
      )}
    >
      <Text className={'pl-6'}>
        {items.length > 0 && (
          <>
            Showing {itemsShowing <= items.length ? itemsShowing : items.length} out of {items.length} result
            {items.length > 1 ? 's' : ''}.
          </>
        )}
      </Text>
      <IconButtonGroup
        className={'hidden xl:flex'}
        value={view}
        onChange={(newValue) => onViewChange(newValue as 'list' | 'grid')}
      >
        <IconButton
          source={'grid'}
          small
          key={'grid'}
          value={'grid'}
          iconProps={{ size: 24 }}
          className={'border-y-0 border-r-0'}
        />
        <IconButton
          source={'list'}
          small
          key={'list'}
          value={'list'}
          iconProps={{ size: 24 }}
          className={'border-y-0 border-r-0'}
        />
      </IconButtonGroup>
    </HFlex>
  );
};

export type SortBarProps = {
  view: 'list' | 'grid';
  onViewChange: (newView: 'list' | 'grid') => void;
  className?: string;
  items: ItemObject[];
  itemsShowing: number;
};

export default CommunitiesSortBar;
