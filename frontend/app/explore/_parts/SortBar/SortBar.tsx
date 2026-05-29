import React, { FC } from 'react';
import { HFlex } from '@/components/Flex';
import IconButton, { IconButtonGroup } from '@/components/IconButton';

const SortBar: FC<SortBarProps> = ({ view, onViewChange }) => {
  return (
    <HFlex
      className={
        'w-full justify-between items-center border border-primary h-10'
      }
    >
      <IconButton
        small
        source={'filter-outline'}
        className={'border-0 border-e'}
      />
      <IconButtonGroup
              className={'max-lg:hidden'}

        value={view}
        onChange={(newValue) => onViewChange(newValue as 'list' | 'grid')}
      >
        <IconButton
          source={'grid'}
          small
          key={'grid'}
          value={'grid'}
          iconProps={{ size: 24 }}
        />
        <IconButton
          source={'list'}
          small
          key={'list'}
          value={'list'}
          iconProps={{ size: 24 }}
        />
      </IconButtonGroup>
    </HFlex>
  );
};

export type SortBarProps = {
  view: 'list' | 'grid';
  onViewChange: (newView: 'list' | 'grid') => void;
};

export default SortBar;
