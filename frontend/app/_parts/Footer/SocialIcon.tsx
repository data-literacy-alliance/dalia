import React, { FC } from 'react';
import Icon from '@/components/Icon/Icon';
import { IconSource } from '@/components/Icon';
import Link from 'next/link';

const SocialIcon: FC<SocialIconProp> = ({ link, icon }) => {
  return (
    <Link href={link} target={'_blank'}>
      <div
        className={
          'rounded-e-xl rounded-ss-xl bg-daliaGray-200 p-1 hover:bg-daliaGray-300 focus:bg-daliaGray-300'
        }
      >
        <Icon source={icon} size={35} />
      </div>
    </Link>
  );
};

type SocialIconProp = {
  link: string;
  icon: IconSource;
};

export default SocialIcon;
