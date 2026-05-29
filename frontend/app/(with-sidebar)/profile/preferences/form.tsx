'use client';
import React, { FC, useState } from 'react';
import { Person } from '@/lib/api/person';
import { useForm } from 'react-hook-form';
import { preferencesForm } from '@/app/(with-sidebar)/profile/preferences/utils';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import Text from '@/components/Text';
import { MSelect2 } from '@/components/MSelect';
import { LabelValuePair } from '@/lib/types/Common';
import Button from '@/components/Button';
import TextBox from '@/components/Textbox/Textbox';
import { apiFetch } from '@/lib/auth/apiFetch';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import { mutate } from 'swr';

const allVisibilityItems = [
  {
    label: 'Public',
    value: 'public',
  },
  {
    label: 'Internal Only',
    value: 'internal',
  },
  {
    label: 'Private',
    value: 'private',
  },
];

const PreferencesForm: FC<PreferencesFormProps> = ({ person }) => {
  const [message, setMessage] = useState('');
  const form = useForm<preferencesForm>({
    resolver: zodResolver(preferencesForm),
    defaultValues: {
      orcid: person.orcid,
      last_name: person.last_name,
      first_name: person.first_name,
      homepage: person.homepage,
      privacy_level: person.privacy_level,
    },
  });
  const { access } = useAuthLogin();

  const loading = form.formState.isSubmitting;

  const onSubmit = async (values: preferencesForm) => {
    if (!access) {
      setMessage('Authentication error. Please refresh the page and try again.');
      setTimeout(() => {
        setMessage('');
      }, 3000);
      return;
    }

    try {
      const result = await apiFetch(`/api/curation/persons/${person.uuid}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${access}`,
        },
        body: JSON.stringify(values),
      });

      if (result.ok) {
        setMessage('Your preferences have been saved.');
        await mutate(`/api/auth/profile/search?user_id=${person.user}`);
      } else {
        setMessage('Could not update your preferences. Please try again later.');
      }
    } catch {
      setMessage('Network error. Please check your connection and try again.');
    }

    setTimeout(() => {
      setMessage('');
    }, 3000);
  };

  return (
    <Form {...form}>
      <form
        // eslint-disable-next-line @typescript-eslint/no-misused-promises
        onSubmit={form.handleSubmit(onSubmit)}
        className={'h-full w-full border-primary pb-4 lg:border-l'}
      >
        <div
          className={
            'border-b border-primary px-5 pb-16 pt-16 lg:flex lg:pl-24 lg:pt-28'
          }
        >
          <Text variant={'h1'}>Your Preferences</Text>
        </div>
        <div
          className={
            'relative grid grid-cols-1 gap-4 px-4 py-8 lg:grid-cols-2 2xl:pl-10'
          }
        >
          {message && (
            <div
              className={
                'absolute left-1/2 top-2 z-10 -translate-x-1/2 border border-primary bg-white p-3 lg:col-span-2'
              }
            >
              {message}
            </div>
          )}
          <FormField
            name={'first_name'}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <TextBox
                    label={'Given Name'}
                    priority={'Mandatory'}
                    disabled={loading}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            name={'last_name'}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <TextBox
                    label={'Family Name'}
                    priority={'Mandatory'}
                    disabled={loading}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            name={'homepage'}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <TextBox
                    label={'Homepage'}
                    priority={'Optional'}
                    disabled={loading}
                    placeholder={'https://'}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            name={'orcid'}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <TextBox
                    label={'ORCID'}
                    priority={'Recommended'}
                    disabled={loading}
                    placeholder={'0000-0000-0000-000X'}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            name={'privacy_level'}
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <MSelect2
                    items={allVisibilityItems}
                    values={[
                      allVisibilityItems.find(
                        (item) => item.value === field.value
                      ) || allVisibilityItems[0],
                    ]}
                    priority={'Mandatory'}
                    single
                    className={'w-full'}
                    label={'Profile Visibility'}
                    onChange={function (values: LabelValuePair[]): void {
                      field.onChange(values[0].value);
                    }}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div
          className={'flex items-center justify-end gap-2 px-4 py-4 2xl:pl-10'}
        >
          <Button dark type={'submit'}>
            Save
          </Button>
        </div>
      </form>
    </Form>
  );
};

export type PreferencesFormProps = {
  person: Person;
};

export default PreferencesForm;
