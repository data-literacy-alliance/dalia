'use client';
import React, { FC, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { VFlex } from '@/components/Flex';
import Button from '@/components/Button';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import { useFormContext } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import TextBox from '@/components/Textbox/Textbox';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import PersonSearchBox from '@/app/(with-sidebar)/items/new/_parts/AddContentData/PersonSearchBox';
import { savePerson } from '@/app/(with-sidebar)/items/new/_parts/AddContentData/utils';

const EditPersonDialog: FC<EditPersonDialogProps> = ({
  personIndex,
  open,
  onClose,
}) => {
  const form = useFormContext<NewItemData>();
  const fieldKey = `people.${personIndex}` as const;
  const currentPerson = form.watch(fieldKey);
  const [step, setStep] = useState<'search' | 'new' | 'selected'>(
    currentPerson?.id ? 'selected' : 'search'
  );
  const { access } = useAuthLogin();

  if (
    step === 'search' &&
    (currentPerson?.firstname !== '' || currentPerson?.lastname !== '')
  ) {
    setStep('selected');
  }

  return personIndex > -1 ? (
    <Dialog
      open={open}
      onOpenChange={(newOpen) => {
        if (!newOpen) {
          onClose(false);
        }
      }}
    >
      <DialogContent className={'md:w-max-[37.5rem] w-full'}>
        <DialogHeader>
          <DialogTitle>Author</DialogTitle>
        </DialogHeader>
        {step === 'search' ? (
          <div>
            <PersonSearchBox
              onSelected={(person) => {
                form.setValue(fieldKey, person);
                form.resetField(fieldKey, {
                  defaultValue: person,
                  keepDirty: false,
                  keepTouched: false,
                  keepError: false,
                });
                setStep('selected');
              }}
              hide={false}
            />
            <div className={'mt-4 flex items-center justify-end'}>
              <Button onClick={() => setStep('new')}>Add Person</Button>
            </div>
          </div>
        ) : (
          <div className={'space-y-2'}>
            <VFlex className={'gap-2 lg:flex-row'}>
              <FormField
                control={form.control}
                name={`people.${personIndex}.firstname`}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <TextBox
                        label={'Given Name'}
                        priority={'Mandatory'}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name={`people.${personIndex}.lastname`}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <TextBox
                        label={'Family Name'}
                        priority={'Mandatory'}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </VFlex>
            <FormField
              name={`people.${personIndex}.orcid`}
              render={({ field }) => (
                <FormItem className={'flex-1'}>
                  <FormControl>
                    <TextBox
                      label={'ORCID'}
                      priority={'Recommended'}
                      placeholder={'https://'}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}

        {step !== 'search' && (
          <DialogFooter>
            <Button
              type="button"
              dark
              onClick={async () => {
                const valid = await form.trigger([fieldKey], {
                  shouldFocus: true,
                });

                if (valid) {
                  const latestPerson = form.getValues(fieldKey);
                  if (step === 'new' && access) {
                    const result = await savePerson(latestPerson, access);
                    if (result) {
                      form.setValue(`${fieldKey}.id`, result.id);
                      form.setValue(`${fieldKey}.uuid`, result.uuid);
                    } else {
                      form.setError(`${fieldKey}.firstname`, {
                        message: 'Failed to save person.',
                      });
                      return;
                    }
                  } else if (step === 'selected' && access) {
                    // check if edited
                    const dirtyFields =
                      form.formState.dirtyFields.people?.[personIndex];
                    if (
                      dirtyFields?.firstname ||
                      dirtyFields?.lastname ||
                      dirtyFields?.orcid
                    ) {
                      const result = await savePerson(latestPerson, access);
                      if (!result) {
                        form.setError(`${fieldKey}.firstname`, {
                          message: 'Failed to save person.',
                        });
                        return;
                      }
                    }
                  }
                  onClose(true);
                }
              }}
            >
              Save Changes
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  ) : null;
};

export type EditPersonDialogProps = {
  personIndex: number;
  open: boolean;
  onClose: (save: boolean) => void;
};

export default EditPersonDialog;
