'use client';
import React, { FC, RefObject } from 'react';
import Icon, { IconSource } from '@/components/Icon';
import Link from 'next/link';
import Image from 'next/image';
import { BASE_PATH } from '@/lib/settings.mjs';
import { OrganizationAuthor, PersonAuthor } from '@/lib/types/ItemTypes';
import { cn } from '@/lib/utils';

const AuthorButton: FC<AuthorButtonProps> = ({
  ref,
  actions,
  className,
  onClick,
  organizationAuthor,
  personAuthor,
}) => {
  const name = personAuthor
    ? `${personAuthor.firstname} ${personAuthor.lastname}`
    : organizationAuthor.name;

  return (
    <div className={cn('group inline-flex h-9 items-center lg:h-8', className)}>
      <button
        className={
          'inline-flex items-center rounded bg-primary px-2 py-1 text-white'
        }
        ref={ref}
        onClick={() => onClick()}
      >
        {name && name.trim().length > 0 ? name : <i>(untitled)</i>}
      </button>
      {personAuthor?.orcid && (
        <Link
          href={personAuthor.orcid}
          target={'_blank'}
          title={'ORCID Link'}
          className={
            'ml-[-2px] inline-flex h-9 w-2 items-center justify-center rounded-r bg-[#a6ce39] py-1 transition-all group-hover:w-8 hover:bg-[#8bb32d] lg:h-8 lg:py-0'
          }
        >
          <Image
            src={`${BASE_PATH}/images/ORCIDLogo.png`}
            alt={'ORCID'}
            width={18}
            height={18}
            className={'opacity-0 transition-opacity group-hover:opacity-100'}
          />
        </Link>
      )}
      {organizationAuthor?.ror && (
        <Link
          href={organizationAuthor.ror}
          target={'_blank'}
          title={'ROR Link'}
          className={
            'ml-[-2px] inline-flex h-9 w-2 items-center justify-center rounded-r bg-green-600 py-1 transition-all group-hover:w-8 hover:bg-green-800 lg:h-8 lg:py-0'
          }
        >
          <Image
            src={`${BASE_PATH}/images/RORLogo.png`}
            alt={'ROR'}
            width={24}
            height={18}
            className={'opacity-0 transition-opacity group-hover:opacity-100'}
          />
        </Link>
      )}

      {actions &&
        actions.map((action, index) => (
          <button
            key={index}
            className={cn(
              'ml-[-2px] inline-flex h-9 w-2 cursor-pointer items-center justify-center rounded-r py-1 text-center text-white transition-all group-hover:w-8 lg:h-8 lg:py-0',
              action.className
            )}
            onClick={action.onClick}
            title={action.title}
          >
            <Icon
              source={action.icon}
              size={10}
              className={'opacity-0 transition-opacity group-hover:opacity-100'}
            />
          </button>
        ))}
    </div>
  );
};

type AuthorButtonAction = {
  icon: IconSource;
  onClick: () => void;
  className?: string;
  title?: string;
};

export type AuthorButtonProps = {
  ref?: RefObject<HTMLButtonElement>;
  actions?: AuthorButtonAction[];
  className?: string;
  onClick: () => void;
} & (
  | {
      personAuthor: PersonAuthor;
      organizationAuthor?: undefined;
    }
  | {
      personAuthor?: undefined;
      organizationAuthor: OrganizationAuthor;
    }
);

export default AuthorButton;
