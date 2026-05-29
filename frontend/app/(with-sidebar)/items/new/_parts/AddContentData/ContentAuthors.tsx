'use client';
import React, { FC, useState } from 'react';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import Button from '@/components/Button';
import EditPersonDialog from '@/app/(with-sidebar)/items/new/_parts/EditPersonDialog';
import EditOrganizationDialog from '@/app/(with-sidebar)/items/new/_parts/EditOrganizationDialog';
import Tooltip from '@/components/Tooltip';
import AuthorButton from '@/components/AuthorButton';
import { useFieldArray, useFormContext } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';

const ContentAuthors: FC<ContentAuthorsProps> = () => {
  const form = useFormContext<NewItemData>();
  const [peopleEditIndex, setPeopleEditIndex] = useState(-1);
  const [isNewPerson, setIsNewPerson] = useState(false);
  const [organizationEditIndex, setOrganizationEditIndex] = useState(-1);
  const [isNewOrganization, setIsNewOrganization] = useState(false);

  const {
    fields: people,
    append: addPerson,
    remove: removePerson,
  } = useFieldArray({ control: form.control, name: 'people' });
  const {
    fields: organizations,
    append: addOrganization,
    remove: removeOrganization,
  } = useFieldArray({ control: form.control, name: 'organizations' });

  const error =
    form.formState.errors.people ?? form.formState.errors.organizations;

  return (
    <VFlex className={'gap-5'}>
      <HFlex className={'items-center gap-1'}>
        <Text variant={'h4'} className="font-semibold">
          Authors
        </Text>
        <Tooltip
          message={
            'The name(s) of the person(s) or organization(s) who created (wrote, made, presented ...) the resource.'
          }
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button trailIcon={'plus'} small>
              Add
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem
              onClick={() => {
                setPeopleEditIndex(people.length);
                setIsNewPerson(true);
                addPerson({
                  firstname: '',
                  lastname: '',
                  orcid: '',
                  authorType: 'PersonAuthor',
                });
              }}
            >
              Person
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                setOrganizationEditIndex(organizations.length);
                setIsNewOrganization(true);
                addOrganization({
                  name: '',
                  ror: '',
                  authorType: 'OrganizationAuthor',
                });
              }}
            >
              Organization
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <span className={'text-xs text-dalia4'}>Mandatory</span>
      </HFlex>
      {error && !Array.isArray(error) && (
        <p className={'mb-3 text-[0.8rem] font-medium text-red-500'}>
          {String(error.message ?? '')}
        </p>
      )}
      <EditPersonDialog
        personIndex={peopleEditIndex}
        open={peopleEditIndex > -1}
        key={peopleEditIndex}
        onClose={(save) => {
          if (!save && isNewPerson) {
            removePerson(peopleEditIndex);
          }
          setIsNewPerson(false);
          setPeopleEditIndex(-1);
        }}
      />
      <EditOrganizationDialog
        organizationIndex={organizationEditIndex}
        open={organizationEditIndex > -1}
        key={organizationEditIndex}
        onClose={(save) => {
          if (!save && isNewOrganization) {
            removeOrganization(organizationEditIndex);
          }
          setIsNewOrganization(false);
          setOrganizationEditIndex(-1);
        }}
      />
      {people.length === 0 && organizations.length === 0 && (
        <span>No Authors.</span>
      )}
      {people.length > 0 && (
        <div>
          <HFlex className={'items-center gap-1'}>
            <Text variant={'subheader'} className={'text-daliaGray-300'}>
              People
            </Text>
            <Tooltip message={'The list of selected people as authors'} />
          </HFlex>
          <div className={'p-3'}>
            {people.map((person, index) => (
              <AuthorButton
                key={person.id}
                onClick={() => {
                  setPeopleEditIndex(index);
                }}
                personAuthor={form.getValues(`people.${index}`)}
                className={'m-1'}
                actions={[
                  {
                    icon: 'close',
                    onClick: () => {
                      removePerson(index);
                    },
                    title: 'Remove this author',
                    className: 'bg-red-500 hover:bg-red-700',
                  },
                ]}
              />
            ))}
          </div>
        </div>
      )}
      {organizations.length > 0 && (
        <div>
          <HFlex className={'items-center gap-1'}>
            <Text variant={'subheader'} className={'text-daliaGray-300'}>
              Organizations
            </Text>
            <Tooltip
              message={'The list of selected organizations as authors'}
            />
          </HFlex>
          <div className={'p-3'}>
            {organizations.map((organization, index) => (
              <AuthorButton
                onClick={() => {
                  setOrganizationEditIndex(index);
                }}
                key={organization.id}
                organizationAuthor={form.getValues(`organizations.${index}`)}
                className={'m-1'}
                actions={[
                  {
                    icon: 'close',
                    onClick: () => {
                      removeOrganization(index);
                    },
                    title: 'Remove this organization',
                    className: 'bg-red-500',
                  },
                ]}
              />
            ))}
          </div>
        </div>
      )}
    </VFlex>
  );
};

export type ContentAuthorsProps = {};

export default ContentAuthors;
