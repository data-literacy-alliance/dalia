'use client';
import React, { FC, useRef, useState } from 'react';
import { HFlex } from '@/components/Flex';
import Icon from '@/components/Icon/Icon';
import useTypingSearch from '@/app/(search)/basic/useTypingSearch';
import { BASE_PATH } from '@/lib/settings.mjs';
import Link from 'next/link';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faX } from '@fortawesome/free-solid-svg-icons';
import { cn } from '@/lib/utils';

const SearchBox: FC<SearchBoxProps> = ({ initQuery }) => {
  const [query, setQuery] = useState(initQuery);

  const form = useRef<HTMLFormElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useTypingSearch(input);

  return (
    <form method={'GET'} action={`${BASE_PATH}/search`} ref={form}>
      <div
        className={
          'absolute left-[50%] top-[calc(50%-2.5rem)] w-full translate-x-[-50%] md:w-auto'
        }
      >
        <HFlex
          className={
            'w-full items-center justify-center gap-2 border border-white/35 bg-accent/20 px-5 py-2 focus-within:border-white/75 focus-within:bg-accent/40'
          }
        >
          <input
            type={'search'}
            name={'query'}
            value={query}
            placeholder={'Type to start searching'}
            autoComplete={'off'}
            className={
              'grow appearance-none bg-transparent text-xl text-white placeholder-white focus:placeholder-zinc-400 focus:outline-none md:text-2xl lg:text-h3'
            }
            onChange={(e) => setQuery(e.target.value)}
            ref={input}
          />
          <FontAwesomeIcon
            icon={faX}
            className={cn(
              'cursor-pointer text-xl text-white md:text-2xl lg:text-3xl',
              {
                invisible: !query,
                visible: !!query,
              }
            )}
            title={'Clear Search'}
            onClick={() => {
              if (query) {
                setQuery('');
              }
              input.current?.focus();
            }}
          />
          <Icon
            source={'search'}
            color={'white'}
            size={32}
            title={
              'Leave the search box empty and click to see all the results'
            }
            className={'cursor-pointer'}
            onClick={() => {
              form.current?.submit();
            }}
          />
        </HFlex>
        <div className={'mt-2 px-1 text-end'}>
          <Link
            href={`/advanced?query=${query}`}
            className={'text-white/80 hover:text-white'}
          >
            Advanced Search &gt;
          </Link>
        </div>
      </div>
      <input name={'source'} value={'basic'} type={'hidden'} />
    </form>
  );
};

type SearchBoxProps = {
  initQuery: string;
};

export default SearchBox;
