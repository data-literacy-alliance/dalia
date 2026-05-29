import React, { FC } from 'react';
import Link from 'next/link';
import { LoginURL } from '@/lib/settings.mjs';
import { cn } from '@/lib/utils';

const LoginWarning: FC<LoginWarningProps> = ({ className }) => {
  return (
    <div className={cn('my-10 max-w-md border border-primary p-2', className)}>
      You need to{' '}
      <Link className={'underline'} href={LoginURL}>
        login
      </Link>{' '}
      to see this page.
    </div>
  );
};

export type LoginWarningProps = {
  className?: string;
};

export default LoginWarning;
