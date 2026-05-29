'use client';

import React, { FC, Fragment, useEffect, useState } from 'react';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import Image from 'next/image';
import Button from '@/components/Button';
import Icon from '@/components/Icon';
import Collapsible from '@/components/Collapsible';
import Link from 'next/link';
import Item, { GridItem } from '@/components/Item';
import Textbox from '@/components/Textbox';
import { ItemObject } from '@/lib/types/ItemTypes';
import parseAuthor from '@/lib/parseAuthor';
import getImage from '@/lib/getImage';
import { useParams } from 'next/navigation';
import DetailsDescriptionAndStats from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsDescriptionAndStats';
import { cn, formatFileSize } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import DescriptionPart from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DescriptionPart';
import DetailsBodySortBar from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBodySortBar';

type DetailsBodyProps = {
  item: ItemObject;
  recommendedContent: ItemObject[];
  preview?: boolean;
  onPreviewClose?: () => void;
};

const DetailsBody: FC<DetailsBodyProps> = ({
  item,
  recommendedContent,
  preview,
  onPreviewClose,
}) => {
  const [recommendedContentOpen, setRecommendedContentOpen] = useState(true);
  const [recommendationView, setRecommendationView] = useState<'list' | 'grid'>(
    'grid'
  );

  // params is being updated on hash update in url.
  // hack: https://github.com/vercel/next.js/discussions/49465
  const params = useParams();

  useEffect(() => {
    if (window) {
      if (window.location.hash === '#recommended') {
        setRecommendedContentOpen(true);
      }
    }
  }, [params]);

  // Helper function to convert text to title case
  const toTitleCase = (str: string): string => {
    return str
      .toLowerCase()
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="flex">
      {/* Left Metadata Panel - Only in Preview Mode */}
      {preview && (
        <div className="w-[350px] border-r border-primary overflow-auto bg-white p-6">
          <h3 className="text-lg font-semibold mb-4 text-primary">
            Resource Information
          </h3>
          <div className="flex flex-col gap-4">
            {/* Languages */}
            {item.languages && item.languages.length > 0 && (
              <div className="flex flex-col gap-1">
                <span className="text-[0.875rem] text-daliaGray-300">
                  Languages
                </span>
                <div className="flex flex-col gap-1">
                  {item.languages.map((lang, idx) => (
                    <span
                      key={idx}
                      property="dcterms:language"
                      className="text-sm"
                    >
                      {typeof lang === 'string' ? lang : lang.label}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Learning Resource Type */}
            {item.learning_resource_types &&
              item.learning_resource_types.length > 0 && (
                <div className="flex flex-col gap-1">
                  <span className="text-[0.875rem] text-daliaGray-300">
                    Learning Resource Type
                  </span>
                  <div className="flex flex-col gap-1">
                    <span property="mo:hasLearningType" className="text-sm">
                      {item.learning_resource_types
                        .map((type) => toTitleCase(type.label))
                        .join(', ')}
                    </span>
                  </div>
                </div>
              )}

            {/* Media Type */}
            {item.media_types && item.media_types.length > 0 && (
              <div className="flex flex-col gap-1">
                <span className="text-[0.875rem] text-daliaGray-300">
                  Media Type
                </span>
                <div className="flex flex-col gap-1">
                  <span property="mo:hasMediaType" className="text-sm">
                    {item.media_types.map((type) => toTitleCase(type.label)).join(', ')}
                  </span>
                </div>
              </div>
            )}

            {/* File Format */}
            {item.format && (
              <div className="flex flex-col gap-1">
                <span className="text-[0.875rem] text-daliaGray-300">
                  File Format
                </span>
                <div className="flex flex-col gap-1">
                  <span property="dcterms:format" className="text-sm">
                    {typeof item.format === 'string'
                      ? item.format.replace(/\./g, '').toUpperCase()
                      : item.format.map((f) => f.label.replace(/\./g, '').toUpperCase()).join(', ')}
                  </span>
                </div>
              </div>
            )}

            {/* Size */}
            {item.file_size && (
              <div className="flex flex-col gap-1">
                <span className="text-[0.875rem] text-daliaGray-300">Size</span>
                <div className="flex flex-col gap-1">
                  <span property="dcterms:extent" className="text-sm">
                    {formatFileSize(item.file_size)}
                  </span>
                </div>
              </div>
            )}

            {/* Publication Date */}
            {item.publication_date && (
              <div className="flex flex-col gap-1">
                <span className="text-[0.875rem] text-daliaGray-300">
                  Publication Date
                </span>
                <div className="flex flex-col gap-1">
                  <span property="dcterms:issued" className="text-sm">
                    {item.publication_date.split('T')[0]}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex-1">
        <VFlex
          className={
            'relative w-full overflow-hidden border-primary pt-16 max-lg:border-b lg:gap-60 lg:border-s lg:pt-48'
          }
        >
      {preview && (
        <div
          className={
            'absolute left-4 top-10 flex items-center gap-2 bg-daliaGray-200 p-2 max-md:flex-col'
          }
        >
          This page is for preview purpose only. <b>Your data is not saved yet.</b>{' '}
          <Button
            small
            className={'shrink-0'}
            onClick={() => {
              if (onPreviewClose) {
                onPreviewClose();
              } else {
                window.close();
              }
            }}
          >
            Back to resource form
          </Button>
        </div>
      )}
      <VFlex className={'overflow-hidden px-5 lg:gap-10 lg:pe-24 lg:ps-24'}>
        <Text
          variant={'h3'}
          className={'w-full break-words lg:break-normal'}
          property={'dcterms:title'}
        >
          {item.title}
        </Text>
        <div
          className={
            'mt-10 flex flex-col items-center lg:mt-0 lg:flex-row lg:gap-2 xl:gap-12'
          }
        >
          <Image
            className={
              'mb-4 h-[22.938rem] w-[30rem] object-contain lg:w-[15rem] 2xl:w-[40.5rem]'
            }
            src={item.image ?? getImage(item)}
            alt={item.title}
            height={356}
            width={650}
            priority
          />
          <VFlex
            className={
              'flex-1 flex-wrap gap-6 border border-primary lg:border-0 xl:gap-8'
            }
          >
            <VFlex className={'gap-2.5 border-primary px-3.5 py-2.5 lg:border'}>
              <Text className={'text-[0.875rem] text-daliaGray-300'}>
                Authors
              </Text>
              <ScrollArea
                className={'max-h-[15rem] overflow-auto'}
                type={'scroll'}
              >
                {item.authors.map((author, index) => (
                  <Fragment key={index}>
                    <Text
                      className={'mx-2 mb-2 inline-block font-semibold'}
                      property={'author'}
                    >
                      {parseAuthor(author)}
                    </Text>
                    {index < item.authors.length - 1 && (
                      <Text className={'font-semibold'}>|</Text>
                    )}
                  </Fragment>
                ))}
              </ScrollArea>
            </VFlex>
            <DetailsDescriptionAndStats
              item={item}
              className={'lg:hidden xl:flex'}
            />
          </VFlex>
        </div>
        <DetailsDescriptionAndStats
          item={item}
          className={'hidden lg:flex xl:hidden'}
        />
      </VFlex>
      <div className={'pt-16'} id={'description'}>
        <div className={'flex flex-col lg:flex-row'}>
          <VFlex
            className={'lg:flex-[3] lg:border-e lg:border-primary xl:flex-[2]'}
          >
            <Text
              variant={'h4'}
              className={
                'h-20 border-y border-primary px-10 py-7 max-lg:hidden lg:border-b'
              }
            >
              Description
            </Text>
            <DescriptionPart>
              {item.description || <i>No Description</i>}
            </DescriptionPart>

            <DetailsBodySpacer smallOnly />
            <Collapsible
              defaultOpen
              className={'lg:hidden'}
              contentClassName={'py-4 px-4'}
              title={
                <Text
                  variant={'h4'}
                  className={
                    'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'
                  }
                >
                  Description
                </Text>
              }
            >
              <Text
                className={'text-wrap break-words px-1 py-6 md:px-6'}
                property={'dcterms:description'}
              >
                {item.description || <i>No description</i>}
              </Text>
            </Collapsible>
          </VFlex>
          <DetailsBodySpacer smallOnly />
          <VFlex className={'lg:flex-[3] xl:flex-1'}>
            <Text
              variant={'h4'}
              className={
                'h-20 border-y border-primary px-6 py-7 text-xl md:px-10 md:text-h4 lg:border-b'
              }
            >
              Details
            </Text>
            <Collapsible
              defaultOpen
              title={
                <Text
                  variant={'h4'}
                  className={'h-20 px-1 py-7 text-start md:px-6 md:text-h4'}
                >
                  Info
                </Text>
              }
            >
              <VFlex className={'gap-7 py-8 pl-4 pr-4 2xl:pl-10'}>
                {item.url && (
                  <Text className={'block truncate lg:max-w-72'}>
                    <b>URL:</b>{' '}
                    <Link
                      href={item.url}
                      className={'text-[1rem]'}
                      target={'_blank'}
                      title={item.url}
                      property={'schema:url'}
                    >
                      {item.url}
                    </Link>
                  </Text>
                )}
                {item.links && item.links.length > 0 && (
                  <Text className={'block'}>
                    <b>Links:</b>
                    <ul className={'ml-4 list-inside list-disc'}>
                      {item.links.map((link) => (
                        <li key={link}>
                          <Link
                            href={link}
                            className={'block truncate lg:max-w-72'}
                            property={'schema:url'}
                          >
                            {link}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </Text>
                )}
                {/*{item.doi && (*/}
                {/*  <Text className={'block truncate lg:max-w-72'}>*/}
                {/*    <b>DOI:</b>{' '}*/}
                {/*    <Link*/}
                {/*      href={`https://doi.org/${item.doi}`}*/}
                {/*      className={'text-[1rem]'}*/}
                {/*      target={'_blank'}*/}
                {/*      title={item.doi}*/}
                {/*    >*/}
                {/*      {item.doi}*/}
                {/*    </Link>*/}
                {/*  </Text>*/}
                {/*)}*/}
                <Text className={'block'}>
                  <b>Communities:</b>
                  <ul className={'ml-4 list-inside list-disc'}>
                    {item.communities && item.communities.length > 0 ? (
                      item.communities.map((community) => {
                        const postfix =
                          community.is_supporting && community.is_recommending
                            ? '(Supporting and Recommending)'
                            : community.is_supporting
                              ? '(Supporting)'
                              : community.is_recommending
                                ? '(Recommending)'
                                : '';
                        return (
                          <li key={community.id}>
                            <Link
                              href={`/communities/${community.id}/${community.slug}`}
                              title={community.title}
                              className={'inline'}
                            >
                              <span property={'mo:belongsToCommunity'}>
                                {community.title}
                              </span>{' '}
                              {postfix}
                            </Link>
                          </li>
                        );
                      })
                    ) : (
                      <i>No communities</i>
                    )}
                  </ul>
                </Text>
                {item.disciplines && item.disciplines.length > 0 && (
                  <Text className={'block'}>
                    <b>Disciplines:</b>

                    <ul className={'ml-4 list-inside list-disc'}>
                      {item.disciplines.map((discipline) => (
                        <li key={discipline.value}>
                          <Link
                            href={`/search?query=${encodeURIComponent(discipline.label)}&offset=0&source=basic`}
                            property={'fabio:hasDiscipline'}
                          >
                            {toTitleCase(discipline.label)}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </Text>
                )}
                {item.target_groups && item.target_groups.length > 0 && (
                  <Text className={'block'}>
                    <b>Target Groups:</b>

                    <ul className={'ml-4 list-inside list-disc'}>
                      {item.target_groups.map((targetGroup) => (
                        <li
                          key={targetGroup.value}
                          property={'mo:hasTargetGroup'}
                        >
                          {toTitleCase(targetGroup.label)}
                        </li>
                      ))}
                    </ul>
                  </Text>
                )}
                {item.proficiency_levels &&
                  item.proficiency_levels.length > 0 && (
                    <Text className={'block'}>
                      <b>Proficiency Levels:</b>

                      <ul className={'ml-4 list-inside list-disc'}>
                        {item.proficiency_levels.map((proficiencyLevel) => (
                          <li
                            key={proficiencyLevel.value}
                            property={'mo:hasProficiencyLevel'}
                          >
                            {toTitleCase(proficiencyLevel.label)}
                          </li>
                        ))}
                      </ul>
                    </Text>
                  )}
                {item.version && item.version.length > 0 && (
                  <Text className={'block'}>
                    <b>Versions:</b>{' '}
                    <span property={'schema:version'}>{item.version}</span>
                  </Text>
                )}
              </VFlex>
            </Collapsible>
            <Collapsible
              title={
                <Text
                  variant={'h4'}
                  className={
                    'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'
                  }
                >
                  Keywords
                </Text>
              }
            >
              <HFlex
                className={'w-full flex-wrap gap-1 py-8 pl-4 pr-4 xl:pl-10'}
              >
                {item.tags && item.tags.length > 0 ? (
                  item.tags.map((tag) => (
                    <Link
                      href={`/search?query=${encodeURIComponent(tag)}&offset=0&source=basic`}
                      key={tag}
                    >
                      <Text>
                        #<span property={'schema:keywords'}>{tag}</span>
                      </Text>
                    </Link>
                  ))
                ) : (
                  <i>No keywords</i>
                )}
              </HFlex>
            </Collapsible>
            <Collapsible
              title={
                <Text
                  variant={'h4'}
                  className={
                    'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'
                  }
                >
                  Rights
                </Text>
              }
            >
              <HFlex
                className={
                  'items-center gap-4 pb-4 pl-10 pt-8 lg:pl-0 xl:pl-10 xl:pr-4'
                }
              >
                {'license' in item && item.license.id ? (
                  <>
                    {/*<div className={'flex-shrink-0'}>*/}
                    {/*  {licenseField.value(item)}*/}
                    {/*</div>*/}
                    <Text property={'dcterms:license'}>
                      {item.license.name}
                    </Text>
                  </>
                ) : (
                  <Text>No rights information.</Text>
                )}
              </HFlex>
            </Collapsible>
            {item.related_works && item.related_works.length > 0 && (
              <Collapsible
                title={
                  <Text
                    variant={'h4'}
                    className={
                      'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'
                    }
                  >
                    Related Works
                  </Text>
                }
              >
                <HFlex
                  className={
                    'items-center gap-4 pb-4 pl-10 pt-8 lg:pl-0 xl:pl-10 xl:pr-4'
                  }
                >
                  <Text className={'block'}>
                    <ul className={'ml-4 list-inside list-disc'}>
                      {item.related_works.map((work) => (
                        <li key={work.link}>
                          <span className={'text-sm italic'}>
                            {toTitleCase(work.type.label)}
                          </span>{' '}
                          <Link href={work.link} target={'_blank'}>
                            {work.link}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </Text>
                </HFlex>
              </Collapsible>
            )}
          </VFlex>
        </div>
        {/*<div id={'suggested'}>*/}
        {/*  <DetailsBodySpacer />*/}
        {/*</div>*/}

        {/*<div className={'border-t border-primary'}>*/}
        {/*  <Collapsible*/}
        {/*    value={suggestedContentOpen ? 'item' : ''}*/}
        {/*    onTitleClick={() => {*/}
        {/*      setSuggestedContentOpen(!suggestedContentOpen);*/}
        {/*    }}*/}
        {/*    title={*/}
        {/*      <Text*/}
        {/*        variant={'h4'}*/}
        {/*        className={*/}
        {/*          'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'*/}
        {/*        }*/}
        {/*      >*/}
        {/*        Suggested Content*/}
        {/*      </Text>*/}
        {/*    }*/}
        {/*  >*/}
        {/*    <HFlex className="w-full flex-wrap">*/}
        {/*      {suggestedItems.length > 0 ? (*/}
        {/*        suggestedItems.map((dItem) => (*/}
        {/*          <GridItem item={dItem} key={dItem.id} className={'flex-1'} />*/}
        {/*        ))*/}
        {/*      ) : (*/}
        {/*        <i className={'mt-4 pl-10'}>No suggested items.</i>*/}
        {/*      )}*/}
        {/*    </HFlex>*/}
        {/*  </Collapsible>*/}
        {/*</div>*/}
        <div className={'h-24 bg-daliaGray-100'} id={'recommended'} />

        <div className={'border-t border-primary'}>
          <Collapsible
            value={recommendedContentOpen ? 'item' : ''}
            onTitleClick={() => {
              setRecommendedContentOpen(!recommendedContentOpen);
            }}
            title={
              <Text
                variant={'h4'}
                className={
                  'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'
                }
              >
                Recommended Content
              </Text>
            }
          >
            {recommendedContent.length > 0 && (
              <DetailsBodySortBar
                onChangeView={setRecommendationView}
                view={recommendationView}
              />
            )}
            {recommendedContent.length > 0 ? (
              recommendationView === 'list' ? (
                <VFlex className={'mb-4 border-r border-primary'}>
                  {recommendedContent.map((item) => (
                    <Item
                      item={item}
                      key={item.id}
                      className={'border-b border-primary'}
                    />
                  ))}
                </VFlex>
              ) : (
                <HFlex
                  className={
                    'mb-4 grid w-full grid-cols-1 flex-wrap xl:grid-cols-2 2xl:grid-cols-3'
                  }
                >
                  {recommendedContent.map((dItem) => (
                    <GridItem
                      item={dItem}
                      key={dItem.id}
                      noBorder
                      className={'w-full border-b border-r border-primary'}
                    />
                  ))}
                </HFlex>
              )
            ) : (
              <i className={'my-4 block pl-10'}>No recommended items.</i>
            )}
          </Collapsible>
        </div>
        <div className={'h-24 bg-daliaGray-100'} />

        <div className={'border-t border-primary'}>
          <Collapsible
            title={
              <Text
                variant={'h4'}
                className={
                  'h-20 px-1 py-7 text-start text-xl md:px-6 md:text-h4'
                }
              >
                Reviews
              </Text>
            }
          >
            <VFlex
              className={'gap-12 px-1 py-6 text-start md:px-6 lg:px-[6.5rem]'}
            >
              <HFlex className={'w-full items-start gap-5'}>
                <Icon
                  source={'user'}
                  className={'bg-primary p-4 text-white max-lg:hidden'}
                  size={80}
                />
                <VFlex className={'flex-grow gap-5'}>
                  <Textbox
                    label={'Comment'}
                    numberOfLines={3}
                    className={'h-[7rem] w-full'}
                    disabled
                  />
                  <Button dark className={'w-fit'} disabled>
                    Post
                  </Button>
                </VFlex>
              </HFlex>
            </VFlex>
          </Collapsible>
        </div>
        <div className={'h-24 bg-daliaGray-100'} />
      </div>
    </VFlex>
      </div>
    </div>
  );
};

const DetailsBodySpacer: FC<{ smallOnly?: boolean }> = ({ smallOnly }) => (
  <div className={cn('h-24 bg-daliaGray-100', smallOnly && 'lg:hidden')} />
);

export default DetailsBody;
