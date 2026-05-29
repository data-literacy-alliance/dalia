import React from 'react';
import { HFlex } from '@/components/Flex';
import Button from '@/components/Button';

const filters = [
  'Research Data Management',
  'Master Materials',
  'Top 10 Courses',
  'FAIR Data Principles',
  'Bachelor Materials',
  'Open Educational Resource',
  'Most Reviewed Content',
];

const FiltersBar = () => {
  return (
    <HFlex
      className={
        'max-lg:grid max-lg:grid-cols-2 flex-wrap justify-center gap-2.5 px-5 overflow-hidden'
      }
    >
      {filters.map((filter) => (
        <Button className={'max-lg:text-sm'} key={filter}>
          {filter}
        </Button>
      ))}
    </HFlex>
  );
};

export default FiltersBar;
