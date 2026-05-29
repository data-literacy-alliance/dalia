'use client';
import React, { FC, useMemo } from 'react';
import { HFlex } from '@/components/Flex';
import IconButton from '@/components/IconButton';
import Button from '@/components/Button';
import useWindowDimensions, { ScreenSizes } from '@/lib/useWindowDimensions';

const Pagination: FC<PaginationProps> = ({
  pageCount,
  currentPage,
  linkGenerator,
}) => {
  const { width } = useWindowDimensions();

  const span =
    width < ScreenSizes.md
      ? 1
      : width < ScreenSizes.lg
        ? 2
        : width < ScreenSizes.xl
          ? 3
          : 4;

  const pages = useMemo(
    () =>
      // create an array from span * 2 - 1 and then filter out negative and too large ones.
      Array.from(
        { length: span * 2 + 1 },
        (_, index) => index + currentPage - span
      ).filter((page) => page > 0 && page <= pageCount),
    [currentPage, pageCount, span]
  );

  return (
    <HFlex
      className={
        'my-1 h-24 items-center justify-center gap-7 border border-r-0 border-primary px-5 md:border-r'
      }
    >
      <HFlex className={'gap-0.5 md:gap-2.5'}>
        <IconButton
          source={'arrow-left-end'}
          borderless
          disabled={currentPage === 1}
          link={{
            href: linkGenerator(1),
          }}
          small
        />
        <IconButton
          source={'arrow-left'}
          borderless
          disabled={currentPage === 1}
          link={{
            href: linkGenerator(currentPage - 1),
          }}
          small
        />
      </HFlex>
      <HFlex className={'items-center border border-primary'}>
        {pages.map((page) => (
          <Button
            small
            dark={page === currentPage}
            key={page}
            borderless
            link={{
              href: linkGenerator(page),
            }}
            className={`border-x-0 transition-transform duration-300 ease-in-out ${
              page === currentPage ? 'scale-125' : ''
            }`}
          >
            {page}
          </Button>
        ))}
      </HFlex>
      <HFlex className={'gap-0.5 md:gap-2.5'}>
        <IconButton
          source={'arrow-right'}
          borderless
          disabled={currentPage === pageCount}
          link={{
            href: linkGenerator(currentPage + 1),
          }}
          small
        />
        <IconButton
          source={'arrow-right-end'}
          borderless
          disabled={currentPage === pageCount}
          link={{
            href: linkGenerator(pageCount),
          }}
          small
        />
      </HFlex>
    </HFlex>
  );
};

export type PaginationProps = {
  pageCount: number;
  currentPage: number;
  linkGenerator: (newPage: number) => string;
};

export default Pagination;
