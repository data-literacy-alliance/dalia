'use client';
import React, { FC } from 'react';
import Button from '@/components/Button';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import { ItemObject } from '@/lib/types/ItemTypes';
import Icon from '@/components/Icon';
import { useRouter } from 'nextjs-toploader/app';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { useMainContext } from '@/app/Providers';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SidebarFields } from '@/components/Item/Fields';
import ResourceButton from '@/components/ResourceButton';
import CiteDialog from '@/components/CiteDialog';
import { useUserInfo } from '@/lib/auth/authApi';
import ShareDialog from '@/components/ShareDialog';

const DetailsSide: FC<DetailsSideProps> = ({ item, preview }) => {
  const fields = SidebarFields;
  const router = useRouter();
  const { setSidebarOpen } = useMainContext();
  const { userInfo } = useUserInfo();

  return (
    <div
      className={
        'sticky top-[4.5rem] mx-5 mb-1 h-[calc(100dvh-4.5rem)] overflow-auto border border-b-0 border-primary lg:mx-auto lg:border-0'
      }
    >
      <ScrollArea className={'h-full'}>
        <Button
          leadIcon={'arrow-left'}
          leftAligned
          borderless
          className={
            'min-h-12 w-full justify-start border-b border-primary lg:border-l lg:border-r'
          }
          onClick={() => router.back()}
        >
          Go back
        </Button>
        <Accordion type={'multiple'} defaultValue={['info', 'interact']}>
          <AccordionItem
            value={'info'}
            className={
              'mt-px overflow-hidden border-primary first:mt-0 lg:border-l'
            }
          >
            <AccordionTrigger
              className={
                'flex h-12 flex-1 cursor-default items-center justify-between px-5 leading-none outline-none'
              }
            >
              Info
            </AccordionTrigger>
            <AccordionContent>
              <VFlex className={'gap-2.5 px-4 pt-4'}>
                {fields.map((field) => {
                  // option is set to true = it is sidebar
                  const value = field.value(item);
                  const icon = field.icon ? field.icon(item) : undefined;

                  return (
                    <VFlex className={'gap-1'} key={field.label}>
                      <Text className={'text-[0.875rem] text-daliaGray-300'}>
                        {field.label}
                      </Text>
                      <HFlex className={'items-center gap-1'}>
                        {icon && <Icon source={icon} size={12} />}
                        {!!value ? (
                          <Text
                            suppressHydrationWarning
                            property={field.property}
                          >
                            {value}
                          </Text>
                        ) : (
                          '-'
                        )}
                      </HFlex>
                    </VFlex>
                  );
                })}
              </VFlex>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem
            value={'interact'}
            className={
              'mt-px overflow-hidden border-primary first:mt-0 lg:border-l'
            }
          >
            <AccordionTrigger
              className={
                'flex h-12 flex-1 cursor-default items-center justify-between px-5 leading-none outline-none'
              }
            >
              Interact
            </AccordionTrigger>
            <AccordionContent>
              {!preview && userInfo && (
                <Button
                  borderless
                  leftAligned
                  small
                  link={{ href: `/items/${item.id}/${item.slug}/edit` }}
                  leadIcon={'document'}
                  className={'w-full'}
                >
                  Suggest Edit
                </Button>
              )}
              {/*<Button*/}
              {/*  borderless*/}
              {/*  leftAligned*/}
              {/*  disabled*/}
              {/*  small*/}
              {/*  leadIcon={'bookmark-outline'}*/}
              {/*>*/}
              {/*  Bookmark*/}
              {/*</Button>*/}
              <ShareDialog item={item}>
                <Button
                  borderless
                  leftAligned
                  small
                  leadIcon={'share'}
                  className={'w-full'}
                  disabled={preview}
                >
                  Share
                </Button>
              </ShareDialog>

              <CiteDialog item={item}>
                <Button
                  borderless
                  leftAligned
                  small
                  leadIcon={'cite'}
                  className={'w-full'}
                  disabled={preview}
                >
                  Cite
                </Button>
              </CiteDialog>

              <Button
                borderless
                leftAligned
                small
                leadIcon={'download'}
                className={'w-full'}
                disabled={preview}
                onClick={() => {
                  // Create JSON blob with item data
                  const jsonData = JSON.stringify(item, null, 2);
                  const blob = new Blob([jsonData], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);

                  // Create download link and trigger download
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `${item.slug || item.id}_metadata.json`;
                  document.body.appendChild(link);
                  link.click();

                  // Cleanup
                  document.body.removeChild(link);
                  URL.revokeObjectURL(url);
                }}
              >
                Download JSON
              </Button>
              {/*<Button*/}
              {/*  borderless*/}
              {/*  leftAligned*/}
              {/*  disabled*/}
              {/*  small*/}
              {/*  leadIcon={'heart-outline'}*/}
              {/*>*/}
              {/*  Like*/}
              {/*</Button>*/}
            </AccordionContent>
          </AccordionItem>
          <AccordionItem
            value={'more'}
            className={
              'mt-px overflow-hidden border-primary first:mt-0 lg:border-l'
            }
          >
            <AccordionTrigger
              className={
                'flex h-12 flex-1 cursor-default items-center justify-between px-5 leading-none outline-none'
              }
            >
              More
            </AccordionTrigger>
            <AccordionContent>
              {/*<Button*/}
              {/*  leftAligned*/}
              {/*  borderless*/}
              {/*  className={'w-full border-primary lg:border-r'}*/}
              {/*  leadIcon={'suggestion'}*/}
              {/*  onClick={(e) => {*/}
              {/*    e.preventDefault();*/}
              {/*    setSidebarOpen(false);*/}
              {/*    router.replace('#suggested', { scroll: true });*/}
              {/*  }}*/}
              {/*  small*/}
              {/*>*/}
              {/*  Suggested Content*/}
              {/*</Button>*/}
              <Button
                leftAligned
                borderless
                className={'w-full border-primary lg:border-r'}
                leadIcon={'cite'}
                onClick={(e) => {
                  e.preventDefault();
                  setSidebarOpen(false);
                  router.replace('#recommended', { scroll: true });
                }}
                disabled={preview}
                small
              >
                Recommended Content
              </Button>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className={'flex-1'} />
        <div className={'p-5'}>
          <ResourceButton
            mainLink={item.url}
            links={item.links ?? []}
            className={'w-full'}
          />
        </div>
      </ScrollArea>
    </div>
  );
};

type DetailsSideProps = {
  item: ItemObject;
  preview?: boolean;
};

export default DetailsSide;
