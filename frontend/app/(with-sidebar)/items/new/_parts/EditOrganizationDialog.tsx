import React, { FC, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import Button from '@/components/Button';
import { useFormContext } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import TextBox from '@/components/Textbox/Textbox';
import OrganizationSearchBox from '@/app/(with-sidebar)/items/new/_parts/AddContentData/OrganizationSearchBox';
import { saveOrganization } from '@/app/(with-sidebar)/items/new/_parts/AddContentData/utils';
import { useAuthLogin } from '@/lib/auth/clientAuth';

const EditOrganizationDialog: FC<EditOrganizationDialogProps> = ({
  organizationIndex,
  open,
  onClose,
}) => {
  const form = useFormContext<NewItemData>();
  const currentOrg = form.watch(`organizations.${organizationIndex}`);
  const [step, setStep] = useState<'search' | 'new' | 'selected'>('search');
  const { access } = useAuthLogin();

  if (
    step === 'search' &&
    (currentOrg?.name !== '' || currentOrg?.ror !== '')
  ) {
    setStep('selected');
  }

  return organizationIndex > -1 ? (
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
          <DialogTitle>Organization</DialogTitle>
        </DialogHeader>
        {step === 'search' ? (
          <div>
            <OrganizationSearchBox
              onSelected={(org) => {
                form.setValue(`organizations.${organizationIndex}`, org);
                form.resetField(`organizations.${organizationIndex}`, {
                  defaultValue: org,
                  keepDirty: false,
                  keepTouched: false,
                  keepError: false,
                });
                setStep('selected');
              }}
              hide={false}
            />
            <div className={'mt-4 flex items-center justify-end'}>
              <Button onClick={() => setStep('new')}>Add Organization</Button>
            </div>
          </div>
        ) : (
          <div>
            <FormField
              control={form.control}
              name={`organizations.${organizationIndex}.name`}
              render={({ field }) => (
                <FormItem className={'flex-1'}>
                  <FormControl>
                    <TextBox
                      label={'Name'}
                      priority={'Mandatory'}
                      {...field}
                      className={'mb-1'}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name={`organizations.${organizationIndex}.ror`}
              render={({ field }) => (
                <FormItem className={'flex-1'}>
                  <FormControl>
                    <TextBox
                      label={'ROR Link'}
                      priority={'Recommended'}
                      placeholder={'https://ror.org/'}
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
                const valid = await form.trigger(
                  [`organizations.${organizationIndex}`],
                  {
                    shouldFocus: true,
                  }
                );

                if (valid) {
                  if (step === 'new' && access) {
                    const result = await saveOrganization(currentOrg, access);
                    if (result) {
                      form.setValue(
                        `organizations.${organizationIndex}.id`,
                        result.id
                      );
                    } else {
                      form.setError(`organizations.${organizationIndex}.name`, {
                        message: 'Failed to save organization.',
                      });
                      return;
                    }
                  } else if (step === 'selected' && access) {
                    // check if edited
                    const dirtyFields =
                      form.formState.dirtyFields.organizations?.[
                        organizationIndex
                      ];
                    if (dirtyFields?.name || dirtyFields?.ror) {
                      const result = await saveOrganization(currentOrg, access);
                      if (!result) {
                        form.setError(
                          `organizations.${organizationIndex}.name`,
                          {
                            message: 'Failed to save organization.',
                          }
                        );
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

export type EditOrganizationDialogProps = {
  organizationIndex: number;
  open: boolean;
  onClose: (save: boolean) => void;
};

export default EditOrganizationDialog;
