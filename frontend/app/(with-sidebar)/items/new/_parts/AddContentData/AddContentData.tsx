'use client';
import React, { BaseSyntheticEvent, FC, useState } from 'react';
import { useRouter } from 'next/navigation';
import { HFlex, VFlex } from '@/components/Flex';
import Button from '@/components/Button';
import Text from '@/components/Text';
import TextBox from '@/components/Textbox';
import {
  calculateFairScore,
  createTempResourceItem,
  findDisciplinesFromString,
  loadErrorsToForm,
  randomString,
  submitData,
  submitEditData,
} from '@/app/(with-sidebar)/items/new/_parts/AddContentData/utils';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  addNewItemSchema,
  NewItemData,
} from '@/app/(with-sidebar)/items/new/_parts/schema';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useFormState, useWatch } from 'react-hook-form';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import ContentAuthors from '@/app/(with-sidebar)/items/new/_parts/AddContentData/ContentAuthors';
import ContentCommunities from '@/app/(with-sidebar)/items/new/_parts/AddContentData/ContentCommunities';
import ContentLinks from '@/app/(with-sidebar)/items/new/_parts/AddContentData/ContentLinks';
import ContentRelations from '@/app/(with-sidebar)/items/new/_parts/AddContentData/ContentRelations';
import { ResourceItem } from '@/lib/types/ItemTypes';
import MSelectWithSuggestions from '@/components/MSelect/MSelectWithSuggestions';
import { LabelValuePair } from '@/lib/types/Common';
import ScoreMeter from '@/components/ScoreMeter';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import LoginWarning from '@/app/_parts/LoginWarning';
import Checkbox from '@/components/Checkbox';
import ContentDisciplines from '@/app/(with-sidebar)/items/new/_parts/AddContentData/ContentDisciplines';
import { useUserInfo } from '@/lib/auth/authApi';
import { useNewDisciplines } from '@/lib/api/newSuggestions';
import { Loader2Icon } from 'lucide-react';
import Tooltip from '@/components/Tooltip';
import Link from 'next/link';
import DetailsBody from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody';

const AddContentData: FC<AddContentDataProps> = ({ item }) => {
  const isEdit = !!item;
  const [saved, setSaved] = useState(false);
  const router = useRouter();
  const form = useForm<NewItemData>({
    resolver: zodResolver(addNewItemSchema),
    defaultValues: {
      title: item?.title ?? '',
      url: item?.url ?? '',
      publicationDate: item?.publication_date ?? '',
      people:
        item?.authors
          .filter((a) => a.authorType === 'PersonAuthor')
          .map((a) => ({
            ...a,
            orcid: a.orcid
              ? (a.orcid.startsWith('http')
                  ? a.orcid
                  : `https://orcid.org/${a.orcid}`)
              : '',
          })) ?? [],
      organizations:
        item?.authors
          .filter((a) => a.authorType === 'OrganizationAuthor')
          .map((a) => ({
            ...a,
            ror: a.ror
              ? (a.ror.startsWith('http')
                  ? a.ror
                  : `https://ror.org/${a.ror}`)
              : '',
          })) ?? [],
      learningResourceTypes: item?.learning_resource_types ?? [],
      communities: item?.communities
        ? item.communities.map((c) => ({
            value: c.id,
            label: c.title,
            is_recommending: c.is_recommending,
            is_supporting: c.is_supporting,
          }))
        : [],
      disciplines: item?.disciplines
        ? item.disciplines.map((d) => [d.value])
        : [],
      licenses: item?.license
        ? [
            {
              value: item.license.id,
              label: item.license.name,
            },
          ]
        : [],
      links: item?.links ?? [],
      description: item?.description ?? '',
      languages: item?.languages
        ? item.languages.map((l) =>
            typeof l === 'string'
              ? { label: l, value: l }
              : { label: l.label, value: String(l.id) }
          )
        : [],
      proficiencies: item?.proficiency_levels ?? [],
      targetGroups: item?.target_groups ?? [],
      fileFormats: item?.format
        ? typeof item.format === 'string'
          ? item.format
              .split(', ')
              .map((f) => ({ label: f.toLowerCase(), value: f.toLowerCase() }))
          : item.format.map((f) => ({
              label: f.label,
              value: String(f.id),
            }))
        : [],
      mediaTypes: item?.media_types ?? [],
      version: item?.version ?? '',
      size: item?.file_size ? item?.file_size.replace(' MB', '') : '',
      keywords: item?.tags ? item.tags.join(', ') : '',
      relations: item?.related_works ?? [],
    },
  });
  const [acceptedRules, setAcceptedRules] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<ResourceItem | null>(null);
  const { loggedIn, isLoading: loginIsLoading, access } = useAuthLogin();
  const { userInfo } = useUserInfo();
  const { items: disciplines } = useNewDisciplines(false);

  // Reset form when item prop changes (for edit mode)
  React.useEffect(() => {
    if (item) {
      const formValues = {
        title: item.title ?? '',
        url: item.url ?? '',
        publicationDate: item.publication_date ?? '',
        people: item.authors
          .filter((a) => a.authorType === 'PersonAuthor')
          .map((a) => ({
            ...a,
            orcid: a.orcid
              ? (a.orcid.startsWith('http')
                  ? a.orcid
                  : `https://orcid.org/${a.orcid}`)
              : '',
          })),
        organizations: item.authors
          .filter((a) => a.authorType === 'OrganizationAuthor')
          .map((a) => ({
            ...a,
            ror: a.ror
              ? (a.ror.startsWith('http')
                  ? a.ror
                  : `https://ror.org/${a.ror}`)
              : '',
          })),
        learningResourceTypes: item.learning_resource_types ?? [],
        communities: item.communities
          ? item.communities.map((c) => ({
              value: c.id,
              label: c.title,
              is_recommending: c.is_recommending,
              is_supporting: c.is_supporting,
            }))
          : [],
        disciplines: item.disciplines
          ? item.disciplines.map((d) => [d.value])
          : [],
        licenses: item.license
          ? [
              {
                value: item.license.id,
                label: item.license.name,
              },
            ]
          : [],
        links: item.links ?? [],
        description: item.description ?? '',
        languages: item.languages
          ? item.languages.map((l) =>
              typeof l === 'string'
                ? { label: l, value: l }
                : { label: l.label, value: String(l.id) }
            )
          : [],
        proficiencies: item.proficiency_levels ?? [],
        targetGroups: item.target_groups ?? [],
        fileFormats: item.format
          ? typeof item.format === 'string'
            ? item.format
                .split(', ')
                .map((f: string) => ({ label: f.toLowerCase(), value: f.toLowerCase() }))
            : item.format.map((f: { id: number; label: string; slug: string }) => ({
                label: f.label,
                value: String(f.id),
              }))
          : [],
        mediaTypes: item.media_types ?? [],
        version: item.version ?? '',
        size: item.file_size ? item.file_size.replace(' MB', '') : '',
        keywords: item.tags ? item.tags.join(', ') : '',
        relations: item.related_works ?? [],
      };
      // Reset with keepDefaultValues to update both values and baseline
      form.reset(formValues, { keepDefaultValues: false });
    } else {
      form.reset({
        title: '',
        url: '',
        publicationDate: '',
        people: [],
        organizations: [],
        learningResourceTypes: [],
        languages: [],
        communities: [],
        disciplines: [],
        licenses: [],
        links: [],
        description: '',
        proficiencies: [],
        targetGroups: [],
        fileFormats: [],
        mediaTypes: [],
        version: '',
        size: '',
        keywords: '',
        relations: [],
      });
      setAcceptedRules(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id]);

  const isLoading = form.formState.isSubmitting;
  const onSubmit = async (data: NewItemData, e?: BaseSyntheticEvent) => {
    if (!access || !userInfo) {
      return;
    }
    const submitter = (e?.nativeEvent as SubmitEvent).submitter as
      | HTMLButtonElement
      | undefined;

    if (submitter?.name === 'save') {
      if (isEdit) {
        if (item.submitted_for_review) {
          // RC already pending — PATCH in-place, do not create a new version
          const result = await submitEditData(data, item.id, access, userInfo.id, disciplines);
          if (!result) {
            form.setError('title', { message: 'Failed to save data!' });
          } else if ('id' in result) {
            setSaved(true);
            router.push(`/items/new?id=${item.id}`);
          } else {
            loadErrorsToForm(form, result);
          }
        } else {
          // RC not pending — create a new version under the same Resource
          const result = await submitData(data, access, userInfo.id, disciplines, item.resource_uuid);
          if (!result) {
            form.setError('title', { message: 'Failed to save data!' });
          } else if ('id' in result) {
            setSaved(true);
            const newUuid = (result as { uuid?: string }).uuid;
            if (newUuid) {
              router.push(`/items/new?id=${newUuid}`);
            } else {
              router.refresh();
            }
          } else {
            loadErrorsToForm(form, result);
          }
        }
      } else {
        try {
          const result = await submitData(
            data,
            access,
            userInfo.id,
            disciplines
          );
          if (!result) {
            form.setError('title', { message: 'Failed to save data!' });
          } else if ('id' in result) {
            // success - result is ResourceItem
            setSaved(true);
            // Refresh router to invalidate cache and fetch updated data
            router.refresh();
          } else {
            // error - result is validation errors or detail message
            loadErrorsToForm(form, result);
          }
        } catch (e) {
          form.setError('title', { message: 'Failed to save data!' });
        }
      }
    } else if (submitter?.name === 'preview') {
      handlePreview(data);
    }
  };

  const handlePreview = (data: NewItemData) => {
    const dis: LabelValuePair[] = data.disciplines
      .map((disc) =>
        disc
          .map((s) => findDisciplinesFromString(disciplines, s))
          .filter((s) => s !== undefined)
      )
      .flat();

    const resource = createTempResourceItem({
      title: data.title,
      authors: {
        people: data.people,
        organizations: data.organizations,
      },
      languages: data.languages,
      url: data.url,
      communities: data.communities,
      description: data.description,
      disciplines: dis,
      fileFormats: data.fileFormats,
      keywords: data.keywords.split(','),
      licenses: data.licenses,
      links: data.links,
      mediaTypes: data.mediaTypes,
      publicationDate: data.publicationDate
        ? new Date(data.publicationDate)
        : undefined,
      size: data.size ? data.size + 'MB' : '',
      proficiencies: data.proficiencies,
      version: data.version,
      types: data.learningResourceTypes,
      targetGroups: data.targetGroups,
      relations: data.relations,
    });

    // Open preview in modal instead of new window
    setPreviewData(resource);
    setPreviewOpen(true);
  };

  const fairScore = useWatch({
    control: form.control,
    compute: (data) =>
      calculateFairScore({
        authors: {
          people: data.people,
          organizations: data.organizations,
        },
        languages: data.languages,
        communities: data.communities,
        description: data.description,
        disciplines: data.disciplines
          .map((disc) =>
            disc
              .map((s) => findDisciplinesFromString(disciplines, s))
              .filter((s) => s !== undefined)
          )
          .flat(),
        fileFormats: data.fileFormats,
        keywords: data.keywords.split(','),
        mediaTypes: data.mediaTypes,
        publicationDate: data.publicationDate
          ? new Date(data.publicationDate)
          : undefined,
        size: data.size,
        proficiencies: data.proficiencies,
        types: data.learningResourceTypes,
        version: data.version,
        targetGroups: data.targetGroups,
        relations: data.relations,
      }),
  });
  const loading = form.formState.isSubmitting;
  const state = useFormState({ control: form.control });

  return saved ? (
    <div className={'m-10 min-h-screen text-h4'}>
      Your data is saved and will be available after review.
    </div>
  ) : loginIsLoading ? (
    <span>Loading...</span>
  ) : !loggedIn ? (
    <LoginWarning className={'mx-4'} />
  ) : (
    <VFlex className={'m-10 gap-10'}>
      <Form {...form}>
        <form
          // eslint-disable-next-line @typescript-eslint/no-misused-promises
          onSubmit={form.handleSubmit(onSubmit)}
          className={'m-10 flex flex-col gap-10 p-0'}
        >
          <div
            className={
              'sticky top-[calc(4.5rem-1px)] z-10 w-full space-y-2 self-center border border-primary bg-white p-2 lg:max-w-md xl:max-w-lg 2xl:max-w-xl'
            }
          >
            <HFlex className={'gap-2'}>
              <span className={'font-semibold'}>FAIRness Score</span>
              <Dialog>
                <DialogTrigger asChild>
                  <Text
                    className={
                      'flex size-4 cursor-pointer items-center justify-center rounded-full bg-daliaGray-200 text-xs font-semibold text-white'
                    }
                  >
                    i
                  </Text>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>FAIRness Score</DialogTitle>
                    <DialogDescription>
                      The FAIRness Score measures how well your data aligns with
                      the FAIR principles — Findable, Accessible, Interoperable,
                      and Reusable. It is calculated based on the recommended
                      and optional metadata you provide. The more complete and
                      high-quality your metadata, the higher your FAIRness
                      Score, helping ensure that your data can be easily
                      discovered, understood, and reused by others.
                    </DialogDescription>
                  </DialogHeader>
                </DialogContent>
              </Dialog>
            </HFlex>
            <ScoreMeter score={fairScore} />
          </div>

          {!!form.formState.errors.root && (
            <div className={'text-red-500 p-2 mx-auto border border-dalia4'}>{form.formState.errors.root.message}</div>
          )}

          <Text variant={'h4'} className="font-semibold">
            Title
          </Text>

          <FormField
            name={'title'}
            render={({ field }) => (
              <FormItem className={'flex-1'}>
                <FormControl>
                  <TextBox
                    label={'Title'}
                    priority={'Mandatory'}
                    disabled={loading}
                    tooltipMessage={'The title of the resource.'}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <ContentLinks />

          <ContentAuthors />

          <VFlex className={'gap-5'}>
            <Text variant={'h4'} className="font-semibold">
              Classification
            </Text>

            <div>
              <FormField
                control={form.control}
                name={'publicationDate'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <TextBox
                        label={'Publication Date'}
                        priority="Recommended"
                        disabled={loading}
                        type={'date'}
                        placeholder={'Enter a valid date.'}
                        tooltipMessage={
                          'The date of first publication or broadcast.'
                        }
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <HFlex className="gap-5 max-lg:flex-col">
              <FormField
                control={form.control}
                name={'languages'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <MSelectWithSuggestions
                        className={'w-full'}
                        label="Languages"
                        suggestionKey={'languages'}
                        placeholder={'Select languages.'}
                        priority={'Mandatory'}
                        tooltipMessage={'The language(s) of the resource.'}
                        values={field.value}
                        onChange={field.onChange}
                        disabled={field.disabled || loading}
                        name={field.name}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name={'learningResourceTypes'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <MSelectWithSuggestions
                        className={'w-full'}
                        label="Learning Resource Type"
                        suggestionKey={'learning-resource-types'}
                        placeholder={'Select a learning resource type.'}
                        priority={'Recommended'}
                        tooltipMessage={
                          'The pedagogical type of the resource: information for the educational use. This includes the most specific type: rather textbook than book.'
                        }
                        values={field.value}
                        onChange={field.onChange}
                        disabled={field.disabled || loading}
                        name={field.name}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </HFlex>

            <HFlex className={'gap-1'}>
              <Text variant={'h4'} className="font-semibold">
                Communities
              </Text>
              <Tooltip
                message={
                  'The associated community(ies) of the resource, these can include an organization, institution, project, body, or online group.'
                }
              />
            </HFlex>
            <ContentCommunities />
          </VFlex>

          <ContentDisciplines />

          <VFlex className={'gap-5'}>
            <HFlex className={'gap-1'}>
              <Text variant={'h4'} className="font-semibold">
                Licensing
              </Text>
              <Tooltip
                message={
                  'The  license identifier of the resource which refers to a legal document giving official permission to do something with the resource. If the license is not open, choose proprietary.'
                }
              />
            </HFlex>
            <FormField
              control={form.control}
              name={'licenses'}
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <MSelectWithSuggestions
                      values={field.value}
                      onChange={field.onChange}
                      className={'w-full'}
                      suggestionKey={'licenses'}
                      single
                      label={'Licenses'}
                      placeholder={'Select valid licenses.'}
                      priority={'Mandatory'}
                      disabled={field.disabled || loading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </VFlex>

          <VFlex className={'gap-5'}>
            <Text variant={'h4'} className="font-semibold">
              Information
            </Text>
            <HFlex className="h-full w-full flex-1">
              <FormField
                control={form.control}
                name={'description'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <TextBox
                        numberOfLines={7}
                        label={'Description'}
                        priority={'Recommended'}
                        placeholder={'Enter description.'}
                        disabled={field.disabled || loading}
                        tooltipMessage={'The description of the resource.'}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </HFlex>
            <HFlex className="gap-5 max-lg:flex-col">
              <FormField
                control={form.control}
                name={'proficiencies'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <MSelectWithSuggestions
                        className={'w-full'}
                        suggestionKey={'proficiency-levels'}
                        label={'Proficiency Level'}
                        priority={'Recommended'}
                        placeholder={'Select appropriate proficiency levels.'}
                        tooltipMessage={
                          'The proposed level of proficiency in research data management and data literacy of the learners in regard to the learning content.'
                        }
                        values={field.value}
                        onChange={field.onChange}
                        disabled={field.disabled || loading}
                        name={field.name}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name={'targetGroups'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <MSelectWithSuggestions
                        className={'w-full'}
                        suggestionKey={'target-groups'}
                        label={'Target Group'}
                        placeholder={'Select target groups.'}
                        tooltipMessage={
                          'The target group refers to the learners of the resource: A class of agents for whom the learning resource is intended or useful.'
                        }
                        priority={'Recommended'}
                        values={field.value}
                        onChange={field.onChange}
                        disabled={field.disabled || loading}
                        name={field.name}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </HFlex>
          </VFlex>

          <VFlex className={'gap-5'}>
            <Text variant={'h4'} className="font-semibold">
              Additional Information
            </Text>
            <HFlex className="w-full gap-5 max-lg:flex-col">
              <FormField
                control={form.control}
                name={'fileFormats'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <MSelectWithSuggestions
                        className={'w-full'}
                        suggestionKey={'file-formats'}
                        label={'File Format'}
                        tooltipMessage={
                          'The (technical) file format(s) of the resource. If the resource exists in different formats (e.g. .pptx and .pdf), all of them should be provided. For non-downloadable resources, e.g. streams, no format can be provided (e.g. YouTube videos).'
                        }
                        priority={'Recommended'}
                        placeholder={'Select all available formats.'}
                        values={field.value}
                        onChange={field.onChange}
                        disabled={field.disabled || loading}
                        name={field.name}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name={'mediaTypes'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <MSelectWithSuggestions
                        className={'w-full'}
                        suggestionKey={'media-types'}
                        label={'Media Type'}
                        priority={'Recommended'}
                        tooltipMessage={
                          'The general type of data content encoded in a computer file in sense of the modality (text, audio, picture etc.).'
                        }
                        placeholder={'Select all available media types.'}
                        values={field.value}
                        onChange={field.onChange}
                        disabled={field.disabled || loading}
                        name={field.name}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </HFlex>
            <HFlex className="gap-5 max-lg:flex-col">
              <FormField
                control={form.control}
                name={'version'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <TextBox
                        label={'Version'}
                        priority={'Optional'}
                        placeholder={'1.0'}
                        disabled={field.disabled || loading}
                        tooltipMessage={'The version of the learning resource.'}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name={'size'}
                render={({ field }) => (
                  <FormItem className={'flex-1'}>
                    <FormControl>
                      <TextBox
                        label={'Size'}
                        priority={'Optional'}
                        placeholder={'Size in MB'}
                        disabled={field.disabled || loading}
                        tooltipMessage={
                          'Size of the application / package (e.g. 18MB). Please enter the size in MB without the unit.'
                        }
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </HFlex>
            <HFlex className="gap-5 max-lg:flex-col">
              <VFlex className={'relative w-full flex-1'}>
                <FormField
                  control={form.control}
                  name={'keywords'}
                  render={({ field }) => (
                    <FormItem className={'flex-1'}>
                      <FormControl>
                        <TextBox
                          label={'Keywords'}
                          priority={'Recommended'}
                          disabled={field.disabled || loading}
                          tooltipMessage={
                            'Essential and characteristic topics or content of the resource.'
                          }
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Separate the tags with commas (,). It is not necessary
                        to add hashtags (#), as these are automatically added by
                        our system.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </VFlex>
            </HFlex>
          </VFlex>

          <ContentRelations />

          <div className={'my-4'}>
            <Checkbox
              checked={acceptedRules}
              onCheckedChange={(newState) => setAcceptedRules(!!newState)}
              label={
                <div className={'lg:pt-2 leading-none'}>
                  I confirm that I understand the metadata is released under a
                  CC0 license and I accept{' '}
                  <Link
                    href={
                      '/en/terms'
                    }
                    target={'_blank'}
                    className={'underline'}
                  >
                    the Terms and Conditions of DALIA
                  </Link>
                  .
                </div>
              }
            />
          </div>

          <HFlex className="justify-end gap-3 max-lg:flex-col lg:gap-5">
            {Object.keys(form.formState.errors).length > 0 && (
              <div className={'flex items-center justify-end'}>
                <div className={'border border-dalia4 p-2 text-dalia4'}>
                  There are some errors in the data.
                </div>
              </div>
            )}
            {isEdit && (
              <Button
                className={'flex min-h-[3.4rem]'}
                type={'reset'}
                disabled={isLoading}
                onClick={() => form.reset()}
              >
                Reset
              </Button>
            )}
            <Button
              className={'flex min-h-[3.4rem]'}
              type={'submit'}
              disabled={isLoading || !acceptedRules}
              name={'preview'}
            >
              Preview
            </Button>
            <Button
              dark={true}
              className={'flex min-h-[3.4rem]'}
              disabled={isLoading || !acceptedRules || (isEdit && !state.isDirty)}
              name={'save'}
              type={'submit'}
            >
              {isLoading && <Loader2Icon className={'animate-spin'} />}
              Send
            </Button>
          </HFlex>
          <div
            className={
              'mt-[-2rem] w-fit self-end border bg-daliaGray-200 p-1 text-xs'
            }
          >
            {isEdit
              ? 'This edit suggestion will be validated by DALIA Curators. Once accepted, it will be available in our knowledge base.'
              : 'This resource will be validated by DALIA Curators. Once accepted, it will be added to our knowledge base.'}
          </div>
        </form>
      </Form>

      {/* Full-screen Preview Modal */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-full h-screen max-h-screen p-0 m-0 rounded-none border-0">
          {previewData && (
            <div className="relative h-full overflow-auto">
              <DetailsBody
                item={previewData}
                recommendedContent={[]}
                preview={true}
                onPreviewClose={() => setPreviewOpen(false)}
              />
              <div className="sticky bottom-0 left-0 right-0 z-50 flex justify-end gap-4 border-t border-primary bg-white p-4 shadow-lg">
                <Button onClick={() => setPreviewOpen(false)}>
                  Back to Form
                </Button>
                <Button
                  dark
                  onClick={async () => {
                    // Validate form first
                    const isValid = await form.trigger();
                    if (!isValid) {
                      return;
                    }

                    // Get current form data
                    const data = form.getValues();

                    // Create event object with proper structure
                    const fakeButton = { name: 'save' } as HTMLButtonElement;
                    const submitEvent = {
                      nativeEvent: {
                        submitter: fakeButton,
                      } as unknown as SubmitEvent,
                    } as BaseSyntheticEvent;

                    // Submit the form and wait for completion
                    await onSubmit(data, submitEvent);

                    // Close modal only after successful submission
                    // Give state a moment to update, then check if submission succeeded
                    setTimeout(() => {
                      if (saved) {
                        setPreviewOpen(false);
                      }
                    }, 100);
                  }}
                  disabled={isLoading || !acceptedRules || (isEdit && !state.isDirty)}
                >
                  {isLoading && <Loader2Icon className={'animate-spin'} />}
                  Send
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </VFlex>
  );
};

type AddContentDataProps = {
  item?: ResourceItem;
};

export default AddContentData;
