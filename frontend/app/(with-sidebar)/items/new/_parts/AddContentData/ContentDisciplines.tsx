'use client';
import React, { FC } from 'react';
import { useFieldArray, useFormContext } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import { HFlex } from '@/components/Flex';
import Text from '@/components/Text';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import ModalSelector from '@/components/ModalSelector';
import Button from '@/components/Button';
import { useNewDisciplines } from '@/lib/api/newSuggestions';
import { Loader2Icon } from 'lucide-react';
import Tooltip from '@/components/Tooltip';

const ContentDisciplines: FC<ContentDisciplinesProps> = ({}) => {
  const form = useFormContext<NewItemData>();
  const { items: allDisciplines, isLoading } = useNewDisciplines(false);

  const {
    fields: disciplines,
    append: addDisciplines,
    remove: removeDisciplines,
  } = useFieldArray({ control: form.control, name: 'disciplines' });

  return (
    <div className={'space-y-5'}>
      <HFlex className={'gap-1'}>
        <Text variant={'h4'} className="font-semibold">
          Disciplines
        </Text>
        <Tooltip message={'The discipline or university/college subject the learning resource belongs to.'} />
      </HFlex>
      {disciplines.map((discipline, index) => (
        <FormField
          key={discipline.id}
          control={form.control}
          name={`disciplines.${index}`}
          render={({ field }) => {
            return (
              <FormItem>
                <FormControl>
                  <ModalSelector
                    label={'Disciplines'}
                    value={field.value || []}
                    onChange={field.onChange}
                    priority={'Recommended'}
                    changeLabel={'Change Discipline'}
                    items={allDisciplines}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            );
          }}
        />
      ))}

      <HFlex className={'gap-3 max-lg:flex-col'}>
        <Button
          trailIcon={'plus'}
          onClick={() => {
            addDisciplines([[]]);
          }}
          disabled={isLoading}
        >
          {isLoading && <Loader2Icon className={'animate-spin'} />}
          Add Discipline
        </Button>
        {disciplines.length > 0 && (
          <Button
            trailIcon={'minus'}
            onClick={() => removeDisciplines(disciplines.length - 1)}
          >
            Remove Last Discipline
          </Button>
        )}
      </HFlex>
    </div>
  );
};

export type ContentDisciplinesProps = {};

export default ContentDisciplines;
