import React, { FC } from 'react';
import Button from '@/components/Button';
import { HFlex, VFlex } from '@/components/Flex';
import Icon from '@/components/Icon';
import { ResourceItem } from '@/lib/types/ItemTypes';
import { cn } from '@/lib/utils';
import ResourceButton from '@/components/ResourceButton';

const DetailsDescriptionAndStats: FC<DetailsDescriptionAndStatsProps> = ({
  item,
  className,
}) => {
  return (
    <VFlex className={cn('gap-6', className)}>
      <div
        className={
          'flex w-full flex-col items-center gap-5 lg:flex-row lg:justify-between lg:gap-2'
        }
      >
        <HFlex className={'gap-2'}>
          <Button
            trailIcon={'arrow-down'}
            link={{
              href: '#description',
            }}
          >
            More Info
          </Button>
          <ResourceButton mainLink={item.url} links={item.links ?? []} />
        </HFlex>

        <HFlex
          className={
            'w-full gap-2.5 border-primary max-lg:border-t max-lg:p-3 lg:w-auto'
          }
        >
          <HFlex className={'gap-1.5'}>
            <Icon source={'eye'} size={24} />
            {item.views}
          </HFlex>
          <HFlex className={'gap-1.5'}>
            <Icon source={'heart'} size={24} />
            {item.likes}
          </HFlex>
          <HFlex className={'gap-1.5'}>
            <Icon source={'comment'} size={24} />
            {item.comments}
          </HFlex>
        </HFlex>
      </div>
    </VFlex>
  );
};

export type DetailsDescriptionAndStatsProps = {
  item: ResourceItem;
  className?: string;
};

export default DetailsDescriptionAndStats;
