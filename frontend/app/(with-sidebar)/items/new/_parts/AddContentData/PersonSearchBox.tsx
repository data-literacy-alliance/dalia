'use client';

import React, { FC, useRef, useState } from 'react';
import TextBox from '@/components/Textbox/Textbox';
import { PersonAuthor } from '@/lib/types/ItemTypes';
import { useDebouncedState } from '@/lib/useDebouncedState';
import { useSearchPersons } from '@/lib/api/newSuggestions';
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Spinner } from '@/components/ui/spinner';

const PersonSearchBox: FC<PersonSearchBoxProps> = ({ onSelected, hide }) => {
  const [open, setOpen] = useState(false);
  const {
    liveValue: liveQuery,
    debouncedValue: query,
    setValue: setQuery,
  } = useDebouncedState(700, '');
  const popoverRef = useRef<HTMLDivElement>(null);

  const minChars = 3;
  const hasEnoughChars = liveQuery.length >= minChars;
  const { persons, isLoading } = useSearchPersons(hasEnoughChars ? query : '');

  const loading = hasEnoughChars && (isLoading || liveQuery !== query);

  return !hide ? (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <TextBox
          label={'Search for a Person'}
          value={liveQuery}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={(e) => {
            if (!popoverRef.current?.contains(e.relatedTarget)) {
              setOpen(false);
            }
          }}
        />
      </PopoverAnchor>
      <PopoverContent
        align={'start'}
        onOpenAutoFocus={(e) => {
          e.preventDefault();
        }}
        onInteractOutside={(e) => {
          e.preventDefault();
        }}
        ref={popoverRef}
      >
        <Command>
          <CommandList>
            {!hasEnoughChars ? (
              <CommandEmpty>Type at least {minChars} letters to search.</CommandEmpty>
            ) : loading ? (
              <Spinner className={'mx-auto my-2'} />
            ) : (
              <CommandEmpty>No Person Found.</CommandEmpty>
            )}
            <CommandGroup>
              {hasEnoughChars &&
                !loading &&
                persons &&
                persons.map((person) => (
                  <CommandItem
                    key={person.id}
                    onSelect={() => {
                      onSelected({
                        firstname: person.first_name,
                        lastname: person.last_name,
                        orcid: person.orcid ? `https://orcid.org/${person.orcid}` : '',
                        id: person.id,
                        uuid: person.uuid,
                        authorType: 'PersonAuthor',
                      });
                      setQuery(`${person.first_name} ${person.last_name}`);
                      setOpen(false);
                    }}
                  >
                    {person.first_name} {person.last_name}
                  </CommandItem>
                ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  ) : null;
};

export type PersonSearchBoxProps = {
  onSelected: (organization: PersonAuthor) => void;
  hide: boolean;
};

export default PersonSearchBox;
