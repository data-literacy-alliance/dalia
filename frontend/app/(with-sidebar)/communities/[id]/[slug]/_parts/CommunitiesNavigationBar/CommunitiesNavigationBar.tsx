import React, { Dispatch, FC, SetStateAction } from 'react';
import { HFlex } from '@/components/Flex';
import Button from '@/components/Button/Button';
import { CommunitiesTabs } from '@/app/(with-sidebar)/communities/[id]/[slug]/page';

const CommunitiesNavigationBar: FC<CommunitiesNavigationBarProps> = ({
  activeTab,
  setActiveTab,
}) => {
  return (
    <HFlex
      className={
        'mt-14 h-[3.25rem] border-t border-primary bg-white lg:mt-5 lg:border-r'
      }
    >
      <HFlex className={'h-full flex-1 items-center'}>
        <Button
          className={'h-full flex-1 items-center'}
          dark={activeTab === 'Featured'}
          borderless
          // onClick={() => setActiveTab('Featured')}
          disabled
        >
          Featured
        </Button>
        <Button
          className={'h-full flex-1 items-center'}
          dark={activeTab === 'All Results'}
          borderless
          onClick={() => setActiveTab('All Results')}
        >
          All Results
        </Button>
        <Button
          className={'h-full flex-1 items-center'}
          dark={activeTab === 'Members'}
          borderless
          // onClick={() => setActiveTab('Members')}
          disabled
        >
          Members
        </Button>
      </HFlex>
    </HFlex>
  );
};

export type CommunitiesNavigationBarProps = {
  activeTab: string;
  setActiveTab: Dispatch<SetStateAction<CommunitiesTabs>>;
};

export default CommunitiesNavigationBar;
