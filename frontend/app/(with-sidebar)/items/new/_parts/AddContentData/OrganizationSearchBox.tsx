'use client';

import React, { FC, useRef, useState } from 'react';
import TextBox from '@/components/Textbox/Textbox';
import { OrganizationAuthor } from '@/lib/types/ItemTypes';
import { useDebouncedState } from '@/lib/useDebouncedState';
import { useSearchOrganizations } from '@/lib/api/newSuggestions';
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

const OrganizationSearchBox: FC<OrganizationSearchBoxProps> = ({
  onSelected,
  hide,
}) => {
  const [open, setOpen] = useState(false);
  const {
    liveValue: liveQuery,
    debouncedValue: query,
    setValue: setQuery,
  } = useDebouncedState(700, '');
  const popoverRef = useRef<HTMLDivElement>(null);

  const { organizations, isLoading } = useSearchOrganizations(query);

  const loading = isLoading || liveQuery !== query;

  return !hide ? (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <TextBox
          label={'Search Organizations'}
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
            {loading ? (
              <Spinner className={'mx-auto my-2'} />
            ) : (
              <CommandEmpty>No Organization Found.</CommandEmpty>
            )}
            <CommandGroup>
              {!loading &&
                organizations &&
                organizations.map((org) => (
                  <CommandItem
                    key={org.id}
                    onSelect={() => {
                      onSelected({
                        name: org.name,
                        ror: org.ror_id,
                        id: org.id,
                        uuid: org.uuid,
                        authorType: 'OrganizationAuthor',
                      });
                      setQuery(org.name);
                      setOpen(false);
                    }}
                  >
                    {org.name}
                  </CommandItem>
                ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  ) : null;
};

export type OrganizationSearchBoxProps = {
  onSelected: (organization: OrganizationAuthor) => void;
  hide: boolean;
};

export default OrganizationSearchBox;
