'use client';

import React, { FC } from 'react';
import { useFieldArray, useFormContext } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import Button from '@/components/Button';
import { HFlex, VFlex } from '@/components/Flex';
import TextBox from '@/components/Textbox';
import Text from '@/components/Text';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import MSelectWithSuggestions from '@/components/MSelect/MSelectWithSuggestions';
import Tooltip from '@/components/Tooltip';

const ContentRelations: FC<ContentRelationsProps> = ({}) => {
  const form = useFormContext<NewItemData>();

  const {
    fields: relations,
    append: addRelation,
    remove: removeRelation,
  } = useFieldArray({ control: form.control, name: 'relations' });

  return (
    <VFlex className={'gap-5'}>
      <HFlex className={'gap-1'}>
        <Text variant={'h4'} className="font-semibold">
          Related Items
        </Text>
        <Tooltip message={'The relation(s) to other resources. It is required to identify the related resource by means of a URL.'} />
      </HFlex>
      <VFlex className="w-full items-center gap-5 max-lg:flex-col">
        {relations.map((relation, index) => (
          <HFlex className="w-full gap-y-1 max-lg:flex-col lg:h-[3.625rem]" key={relation.id}>
            <FormField
              control={form.control}
              name={`relations.${index}.type`}
              render={({ field }) => (
                <FormItem className={'lg:w-[12.5rem]'}>
                  <FormControl>
                    <MSelectWithSuggestions
                      className={'w-full h-full'}
                      innerClassName={'lg:border-r-0'}
                      suggestionKey={'relation-types'}
                      additionalSuggestionParams={{
                        category: 'Content Relations,Version Relations,Reference Relations,Supplement Relations,Translation Relations,Item Relation',
                      }}
                      label={'Relation Type'}
                      values={field.value ? [field.value] : []}
                      onChange={(newValues) => {
                        field.onChange(newValues[0]);
                      }}
                      placeholder="Select One"
                      single
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name={`relations.${index}.link`}
              render={({ field }) => (
                <FormItem className={'flex-1'}>
                  <FormControl>
                    <TextBox
                      label={'Related Work'}
                      placeholder={'Enter URL or DOI'}
                      priority={'Optional'}
                      className={'h-full'}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </HFlex>
        ))}
      </VFlex>
      <HFlex className={'gap-3 max-lg:flex-col'}>
        <Button
          trailIcon="plus"
          onClick={() =>
            addRelation({
              type: undefined,
              link: '',
            })
          }
        >
          Add a Related Work
        </Button>
        {relations.length > 0 && (
          <Button
            trailIcon="minus"
            onClick={() => removeRelation(relations.length - 1)}
          >
            Remove last related work
          </Button>
        )}
      </HFlex>
    </VFlex>
  );
};

export type ContentRelationsProps = {};

export default ContentRelations;
