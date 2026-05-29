'use client';
import React, { FC, useState } from 'react';
import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import { HFlex } from '@/components/Flex';
import Button from '@/components/Button';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import MSelectWithSuggestions from '@/components/MSelect/MSelectWithSuggestions';
import CreateCommunityDialog from '@/app/(with-sidebar)/items/new/_parts/CreateCommunityDialog';

const ContentCommunities: FC<ContentCommunitiesProps> = () => {
  const form = useFormContext<NewItemData>();

  const {
    fields: communities,
    append: addCommunity,
    remove: removeCommunity,
  } = useFieldArray({ control: form.control, name: 'communities' });

  const allCommunities = useWatch({ control: form.control, name: 'communities' });
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  return (
    <div className={'space-y-5'}>
      {communities.map((community, index) => {
        return (
          <FormField
            key={community.id}
            control={form.control}
            name={`communities.${index}`}
            render={({ field }) => {
              return (
                <FormItem>
                  <FormControl>
                    <HFlex className={'w-full gap-y-1 max-lg:flex-col'}>
                      <MSelectWithSuggestions
                        name={field.name}
                        label={'Community'}
                        placeholder={'Select a Community'}
                        priority={'Recommended'}
                        suggestionKey={'communities'}
                        className={'w-full'}
                        single
                        shouldFilter={false}
                        values={[field.value]}
                        onChange={(value) => {
                          const selected = value[0];
                          const alreadyAdded = allCommunities.some(
                            (c, i) => i !== index && c.value === selected?.value
                          );
                          if (!alreadyAdded) {
                            field.onChange(selected);
                          }
                        }}
                      />
                    </HFlex>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              );
            }}
          />
        );
      })}

      <HFlex className={'gap-3 max-lg:flex-col'}>
        <Button
          trailIcon={'plus'}
          onClick={() => {
            addCommunity({
              label: '',
              value: '',
            });
          }}
        >
          Add Community
        </Button>
        <Button
          trailIcon={'plus'}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create new community
        </Button>
        {communities.length > 0 && (
          <Button
            trailIcon={'minus'}
            onClick={() => removeCommunity(communities.length - 1)}
          >
            Remove Last Community
          </Button>
        )}
      </HFlex>

      <CreateCommunityDialog
        open={createDialogOpen}
        onClose={(newCommunity) => {
          setCreateDialogOpen(false);
          if (newCommunity) {
            const emptyIndices = allCommunities
              .map((c, i) => (!c.value ? i : -1))
              .filter((i): i is number => i !== -1);
            if (emptyIndices.length > 0) {
              removeCommunity(emptyIndices);
            }
            addCommunity(newCommunity);
          }
        }}
      />
    </div>
  );
};

export type ContentCommunitiesProps = {};

export default ContentCommunities;
