'use client';
import React, { FC } from 'react';
import { HFlex } from '@/components/Flex';
import IconButton, { IconButtonGroup } from '@/components/IconButton';
import Icon from '@/components/Icon';
import useWritableSearchParams from '@/lib/useWritableSearchParams';
import { useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';

const SortBar: FC<SortBarProps> = ({ className, showTopBorder }) => {
  const params = useWritableSearchParams();
  const view = useSearchParams().get('view') || 'list';
  params.delete('view');
  params.delete('limit');

  return (
    <HFlex
      className={cn(
        'h-10 w-full items-center justify-between border border-e-0 border-t-0 border-primary',
        className
      )}
    >
      <Icon source={'filter-outline'} className={'mx-2'} size={20} />
      <IconButtonGroup value={view}>
        <IconButton
          source={'grid'}
          small
          key={'grid'}
          value={'grid'}
          iconProps={{ size: 24 }}
          borderless
          className={cn('border border-primary', {
            'border-t-0': !showTopBorder,
          })}
          link={{
            href: `?view=grid&limit=18&${params}`,
          }}
        />
        <IconButton
          source={'list'}
          small
          key={'list'}
          value={'list'}
          iconProps={{ size: 24 }}
          borderless
          className={cn('border border-primary', {
            'border-t-0': !showTopBorder,
          })}
          link={{
            href: `?view=list&limit=15&${params}`,
          }}
        />
      </IconButtonGroup>
    </HFlex>
  );
};

export type SortBarProps = {
  className?: string;
  showTopBorder?: boolean;
};

export default SortBar;
