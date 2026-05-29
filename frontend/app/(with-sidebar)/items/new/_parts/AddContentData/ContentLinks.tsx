'use client';

import React, { FC } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import Text from '@/components/Text';
import { HFlex, VFlex } from '@/components/Flex';
import TextBox from '@/components/Textbox/Textbox';
import Button from '@/components/Button';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import Tooltip from '@/components/Tooltip';

const ContentLinks: FC<ContentLinksProps> = () => {
  const form = useFormContext<NewItemData>();

  const links = useWatch({ control: form.control, name: 'links' });
  const loading = form.formState.isSubmitting;

  return (
    <VFlex className={'gap-3'}>
      <HFlex className={'gap-1'}>
        <Text variant={'h4'} className="font-semibold">
          Links
        </Text>
        <Tooltip message={'The hyperlink(s) to the resource.'} />
      </HFlex>
      <VFlex className="w-full gap-3">
        <FormField
          name={'url'}
          render={({ field }) => (
            <FormItem className={'flex-1'}>
              <FormControl>
                <TextBox
                  label={links.length > 0 ? 'Link 1' : 'Link'}
                  priority={'Mandatory'}
                  placeholder={'https://'}
                  disabled={loading}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {links.map((link, index) => (
          <FormField
            key={index}
            control={form.control}
            name={`links.${index}`}
            render={({ field }) => (
              <FormItem className={'flex-1'}>
                <FormControl>
                  <TextBox
                    label={`Link ${index + 2}`}
                    priority={'Optional'}
                    placeholder={'Enter additional link.'}
                    disabled={loading}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        ))}
      </VFlex>
      <HFlex className={'gap-3 max-lg:flex-col'}>
        <Button
          trailIcon="plus"
          onClick={() => form.setValue('links', [...links, ''])}
        >
          Add Link
        </Button>
        {links.length > 0 && (
          <Button
            trailIcon="minus"
            onClick={() => form.setValue('links', links.toSpliced(-1, 1))}
          >
            Remove Last Link
          </Button>
        )}
      </HFlex>
    </VFlex>
  );
};

export type ContentLinksProps = {};

export default ContentLinks;
