'use client';
import { HFlex, VFlex } from '@/components/Flex';
import Item, { GridItem } from '@/components/Item';
import { FC, useState } from 'react';
import { ItemObject } from '@/lib/types/ItemTypes';
import Text from '@/components/Text';
import CommunitiesSortBar from '../CommunitiesSortBar';
import useWindowDimensions, { ScreenSizes } from '@/lib/useWindowDimensions';

const AllResults: FC<AllResultsProps> = ({ items }) => {
  const [itemCount, setItemCount] = useState(12);
  const { width } = useWindowDimensions();
  const [userView, setView] = useState<'list' | 'grid'>('grid');

  const view = width < ScreenSizes.xl ? 'grid' : userView;

  return (
    <>
      {items.length === 0 ? (
        <div className={'border-t border-primary'}>
          <Text className={'p-4 italic'}>No results.</Text>
        </div>
      ) : (
        <>
          <CommunitiesSortBar
            view={view}
            onViewChange={setView}
            className={'border-b-0'}
            items={items}
            itemsShowing={itemCount}
          />
          {view === 'grid' ? (
            <HFlex
              className={
                'ml-[-1px] grid w-[calc(100%+1px)] grid-cols-1 border-l border-t border-primary xl:grid-cols-2 2xl:grid-cols-3'
              }
            >
              {items.slice(0, itemCount).map((item) => (
                <GridItem
                  item={item}
                  key={item.id}
                  noBorder
                  className={'w-full border-b border-primary lg:border-r'}
                />
              ))}
            </HFlex>
          ) : (
            <VFlex
              className={
                'ml-[-1px] w-[calc(100%+1px)] border-l border-t border-primary'
              }
            >
              {items.slice(0, itemCount).map((item) => (
                <Item
                  item={item}
                  key={item.id}
                  noBorder
                  className={'w-full border-b border-primary lg:border-r'}
                />
              ))}
            </VFlex>
          )}
          {itemCount < items.length && (
            <div className={'mt-4 px-10 text-right'}>
              <Text
                className={'cursor-pointer underline'}
                onClick={() => setItemCount((count) => count + 6)}
              >
                Show more...
              </Text>
            </div>
          )}
        </>
      )}
    </>
  );
};

type AllResultsProps = {
  items: ItemObject[];
};

export default AllResults;
