'use client';
import React, { FC, ReactElement, useMemo, useRef, useState } from 'react';
import IconButton from '@/components/IconButton';
import styles from './SearchInput.module.css';
import useWritableSearchParams from '@/lib/useWritableSearchParams';
import { cn } from '@/lib/utils';

const SearchInput: FC<SearchInputProps> = ({ mobile, ...props }) => {
  const params = useWritableSearchParams();
  const lastParamQuery = useRef(params.get('query'));

  const inputRef = useRef<HTMLInputElement>(null);
  const clearRef = useRef<HTMLElement>(null);
  const submitRef = useRef<HTMLElement>(null);
  const [value, setValue] = useState(params.get('query') ?? '');
  const [focused, setFocused] = useState(false);

  if (params.has('query')) {
    lastParamQuery.current = params.get('query') || '';
    setValue(lastParamQuery.current);
  }

  params.delete('query');
  params.delete('offset');

  const jsxParams = useMemo(() => {
    const res: ReactElement[] = [];
    params.forEach((value, name) =>
      res.push(
        <input
          type={'hidden'}
          name={name}
          value={value}
          key={`${name}_${value}`}
        />
      )
    );
    return res;
  }, [params]);

  return (
    <form
      className={cn(
        'relative h-full items-center border-primary',
        {
          'hidden border-e lg:flex': !mobile,
          'flex border p-2': mobile,
        },
        props.className
      )}
      method={'GET'}
      action={`?${params}`}
    >
      <input
        {...props}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        name={'query'}
        className={cn('outline-none', {
          'h-8 w-full': mobile,
          'h-full w-52 pe-12 ps-2 transition-all xl:w-72': !mobile,
          'w-60 xl:w-80': focused && !mobile,
        })}
        onFocus={() => setFocused(true)}
        onBlur={(e) => {
          if (
            e.relatedTarget !== clearRef.current &&
            e.relatedTarget !== submitRef.current
          ) {
            setFocused(false);
          }
        }}
        ref={inputRef}
      />
      {focused && value !== '' && (
        <IconButton
          source={'close'}
          small
          borderless
          className={'absolute end-12 top-[calc(50%-1.25rem)]'}
          onClick={() => {
            setValue('');
            inputRef.current?.focus();
          }}
          tabIndex={-1}
          ref={clearRef}
        />
      )}
      <IconButton
        source={'search'}
        small
        borderless
        dark={focused}
        className={styles.icon}
        type={'submit'}
        ref={submitRef}
      />
      <input type={'hidden'} name={'offset'} value={0} key={'offset'} />
      {jsxParams}
    </form>
  );
};

export type SearchInputProps = Omit<
  React.DetailedHTMLProps<
    React.InputHTMLAttributes<HTMLInputElement>,
    HTMLInputElement
  >,
  'children'
> & {
  mobile?: boolean;
};

export default SearchInput;
