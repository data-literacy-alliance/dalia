import React, { FC } from 'react';
import TopBar from '@/app/_parts/TopBar';

export const dynamic = 'force-dynamic';

const NewOnDaliaTopBar: FC = () => {
  return <TopBar activePage={'New on DALIA'} smallUser />;
};

export default NewOnDaliaTopBar;
