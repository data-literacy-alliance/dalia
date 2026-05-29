'use client';
import React, { FC, Fragment, useEffect, useRef, useState } from 'react';
import { BASE_PATH } from '@/lib/settings.mjs';
import { BasicSearchFilter } from '@/lib/types/Filters';
import Button from '@/components/Button';
import useTypingSearch from '@/app/(search)/basic/useTypingSearch';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import MSelect from '@/components/MSelect';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '@/components/ui/select';
import { InfoIcon, PlusIcon } from 'lucide-react';
import IconButton from '@/components/IconButton';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faX } from '@fortawesome/free-solid-svg-icons';

const AdvancedSearchBox: FC<AdvancedSearchBoxProps> = ({
  filters: allFilters,
  initQuery,
}) => {
  const [query, setQuery] = useState(initQuery);
  const [whiteBg, setWhiteBg] = useState(false);
  const [activeFilters, setActiveFilters] = useState<BasicSearchFilter[]>([]);
  const [availableFilters, setAvailableFilters] = useState<BasicSearchFilter[]>(
    [...allFilters]
  );

  const [selectedValues, setSelectedValues] = useState<
    Record<string, string[]>
  >(
    allFilters.reduce<Record<string, string[]>>((acc, filter) => {
      acc[filter.key.name] = [];
      return acc;
    }, {})
  );

  useEffect(() => {
    const timeout = setTimeout(() => {
      setWhiteBg(true);
    }, 200);
    return () => {
      clearTimeout(timeout);
    };
  }, []);

  const input = useRef<HTMLInputElement>(null);

  useTypingSearch(input);

  return (
    <form method={'GET'} action={`${BASE_PATH}/search`}>
      <div
        className={
          'absolute left-[50%] top-[50%] w-full translate-x-[-50%] translate-y-[-50%] md:w-auto'
        }
      >
        <div
          className={cn('w-full transition duration-500', {
            'border border-primary bg-white/90': whiteBg,
          })}
        >
          <div className={'flex items-center gap-2 p-2'}>
            <input
              type={'search'}
              name={'query'}
              value={query}
              placeholder={'Type to start searching'}
              autoComplete={'off'}
              ref={input}
              className={
                'my-2 flex-grow appearance-none bg-transparent pe-0 text-2xl focus:outline-none md:p-2 md:pe-0 lg:text-h3'
              }
              onChange={(e) => setQuery(e.target.value)}
            />
            <FontAwesomeIcon
              icon={faX}
              className={cn(
                'shrink-0 cursor-pointer text-xl text-primary md:pe-6 lg:text-3xl',
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
          </div>

          <hr
            className={cn('h-0.5 bg-primary', {
              invisible: !whiteBg,
              visible: whiteBg,
            })}
          />
          <div
            className={cn('p-2', {
              invisible: !whiteBg,
              visible: whiteBg,
            })}
          >
            <div className={'text-lg'}>Advanced Filters</div>
            <div
              className={'mb-3 flex items-center gap-1 text-xs text-gray-600'}
            >
              <InfoIcon size={14} />
              <strong>Multiple facets:</strong> AND logic. <strong>Multiple values in same facet:</strong> OR logic.
            </div>
            <div
              className={
                'grid grid-cols-1 items-center gap-y-2 py-2 md:grid-cols-3'
              }
            >
              {activeFilters.length === 0 ? (
                <i className={'ms-2'}>No Filters Selected.</i>
              ) : (
                activeFilters.map((filter) => (
                  <Fragment key={filter.key.name}>
                    <label htmlFor={filter.key.name} className={'text-sm'}>
                      {filter.key.label}
                    </label>
                    <div className={'flex items-center gap-1 md:col-span-2'}>
                      <MSelect
                        items={filter.values}
                        values={selectedValues[filter.key.name]}
                        onChange={(newValues) => {
                          setSelectedValues((prev) => {
                            const newSelectedValues = { ...prev };
                            newSelectedValues[filter.key.name] = newValues;
                            return newSelectedValues;
                          });
                        }}
                        placeholder={'Select ...'}
                        name={filter.key.name}
                        className={'flex-grow'}
                      />
                      <IconButton
                        source={'minus'}
                        className={'shrink-0'}
                        small
                        onClick={() => {
                          setActiveFilters((oldActiveFilter) =>
                            oldActiveFilter.filter(
                              (activeFilter) =>
                                activeFilter.key.name !== filter.key.name
                            )
                          );
                          setAvailableFilters((oldAvailableFilters) => [
                            ...oldAvailableFilters,
                            allFilters.find(
                              (availableFilter) =>
                                availableFilter.key.name === filter.key.name
                            )!,
                          ]);
                        }}
                      />
                    </div>
                  </Fragment>
                ))
              )}
            </div>

            {/* Publication Date Filter */}
            <div className={'border-t border-gray-200 pt-4 mt-4'}>
              <div className={'text-sm font-medium mb-2'}>Publication Date</div>
              <div className={'grid grid-cols-1 md:grid-cols-2 gap-4'}>
                <div>
                  <label
                    htmlFor="datePublished_after"
                    className={'text-xs text-gray-600 mb-1 block'}
                  >
                    From:
                  </label>
                  <input
                    type="date"
                    id="datePublished_after"
                    name="datePublished_after"
                    className={
                      'w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'
                    }
                  />
                </div>
                <div>
                  <label
                    htmlFor="datePublished_before"
                    className={'text-xs text-gray-600 mb-1 block'}
                  >
                    To:
                  </label>
                  <input
                    type="date"
                    id="datePublished_before"
                    name="datePublished_before"
                    className={
                      'w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'
                    }
                  />
                </div>
              </div>
            </div>

            <div className={'flex w-full justify-end gap-2 mt-4'}>
              {availableFilters.length > 0 && (
                <Select
                  name={'newFilter'}
                  onValueChange={(newValue) => {
                    setActiveFilters((oldActiveFilters) => [
                      ...oldActiveFilters,
                      availableFilters.find(
                        (filter) => filter.key.name === newValue
                      )!,
                    ]);
                    setAvailableFilters((oldAvailableFilters) =>
                      oldAvailableFilters.filter(
                        (filter) => filter.key.name !== newValue
                      )
                    );
                  }}
                >
                  <SelectTrigger className={'h-10 max-w-48'}>
                    <PlusIcon />
                    Add a New Filter
                  </SelectTrigger>
                  <SelectContent>
                    {availableFilters.map((filter) => (
                      <SelectItem value={filter.key.name} key={filter.key.name}>
                        {filter.key.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Button small dark leadIcon={'search'} type={'submit'}>
                Search
              </Button>
            </div>
          </div>
        </div>
        <div className={'p-3 text-right'}>
          <Link
            href={`/basic?query=${query}`}
            className={'text-white/80 hover:text-white'}
          >
            &lt; Basic Search
          </Link>
        </div>
      </div>

      <input name={'source'} value={'advanced'} type={'hidden'} />
    </form>
  );
};

export type AdvancedSearchBoxProps = {
  filters: BasicSearchFilter[];
  initQuery: string;
};

export default AdvancedSearchBox;
