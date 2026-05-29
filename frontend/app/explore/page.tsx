'use client';
import { HFlex, VFlex } from '@/components/Flex';
import TopBar from '@/app/_parts/TopBar';
import styles from './explore.module.css';
import Text from '@/components/Text';
import FiltersBar from '@/app/explore/_parts/FiltersBar';
import SortBar from '@/app/explore/_parts/SortBar';
import Item, { GridItem } from '@/components/Item';
import { Suspense, useState } from 'react';
import { dummyItems } from '@/lib/dummy';
import Pages from '@/app/_parts/Pages';

export const dynamic = 'force-dynamic';

export default function Explore() {
  const [view, setView] = useState<'list' | 'grid'>('grid');

  return (
    <Suspense>
      <TopBar />
      <HFlex>
        <VFlex className={styles.body}>
          <Text className={'px-5'} variant={'h1'}>
            Explore
          </Text>
          <FiltersBar />
          <SortBar view={view} onViewChange={setView} />
          {view === 'list' ? (
            <VFlex className={styles.list}>
              {dummyItems.map((item) => (
                <Item item={item} key={item.id} />
              ))}
            </VFlex>
          ) : (
            <HFlex className={styles.grid}>
              {dummyItems.map((item) => (
                <GridItem item={item} className={'flex-1'} key={item.id} />
              ))}
            </HFlex>
          )}
          <Suspense>
            <Pages limit={20} count={20} offset={0} />
          </Suspense>
        </VFlex>
      </HFlex>
    </Suspense>
  );
}
