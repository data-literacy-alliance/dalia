'use client';

import React, { FC, useState } from 'react';
import { ItemObject } from '@/lib/types/ItemTypes';
import { HFlex, VFlex } from '@/components/Flex';
import Image from 'next/image';
import Text from '@/components/Text';
import Icon from '@/components/Icon';
import IconButton from '@/components/IconButton';
import Button from '@/components/Button';
import Link from 'next/link';
import getImage from '@/lib/getImage';
import AlertDialog from '../AlertDialog';
import { cn } from '@/lib/utils';
import { ItemFields } from '@/components/Item/Fields';
import { parseAuthors } from '@/lib/parseAuthor';
import { ItemActions } from '@/components/Item/Actions';
import { DeleteIcon, EditIcon } from 'lucide-react';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import ResourceButton from '@/components/ResourceButton';
import { useRouter } from 'next/navigation';
import { softDeleteResource } from '@/lib/api/item';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import { getCsrfTokenClient } from '@/lib/auth/csrfToken';

const Item: FC<ItemProps> = ({ className, item, editable, deletable = true, ...props }) => {
  const router = useRouter();
  const { access } = useAuthLogin();
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const csrfToken = getCsrfTokenClient();

      if (!access || !csrfToken) {
        alert('Authentication required. Please log in again.');
        setIsDeleting(false);
        setDeleteDialogOpen(false);
        return;
      }

      const result = await softDeleteResource(item.id, access, csrfToken);

      if (result.success) {
        setDeleteDialogOpen(false);
        router.refresh(); // Refresh the page to update the list
      } else {
        alert(result.error || 'Failed to delete resource');
        setIsDeleting(false);
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('An error occurred while deleting the resource');
      setIsDeleting(false);
    }
  };
  return (
    <VFlex
      {...props}
      className={cn(
        'flex gap-7 overflow-hidden border-primary px-10 py-12 transition hover:bg-gray-50 focus:bg-gray-50',
        className
      )}
    >
      <HFlex className={'gap-10'}>
        <Image
          src={item.image ?? getImage(item)}
          className={'h-36 w-28'}
          alt={item.title}
          width={112}
          height={144}
        />
        <VFlex className={'min-w-0 grow content-between gap-5'}>
          <Text variant={'h3'} className={'text-[1.5rem]'}>
            <Link href={`/items/${item.id}/${item.slug}`}>{item.title}</Link>
            {editable && (
              <HFlex className={'gap-4'}>
                <Link
                  href={`/items/new?id=${item.id}`}
                  className={'flex items-center gap-1 text-sm'}
                >
                  <EditIcon size={18} /> Edit
                </Link>
                {deletable && (
                  <AlertDialog
                    open={deleteDialogOpen}
                    onOpenChange={setDeleteDialogOpen}
                    title={'Delete Resource'}
                    content={
                      'Are you sure you want to delete this resource? This action cannot be undone.'
                    }
                    onConfirm={() => {
                      void handleDelete();
                    }}
                    confirmText={isDeleting ? 'Deleting...' : 'Delete'}
                    confirmDisabled={isDeleting}
                  >
                    <button className={'flex items-center gap-1 text-sm hover:underline'}>
                      <DeleteIcon size={18} /> Delete
                    </button>
                  </AlertDialog>
                )}
              </HFlex>
            )}
          </Text>
          <Text className={'line-clamp-3'}>{item.description}</Text>
        </VFlex>
        <HFlex className={'shrink-0 gap-2.5'}>
          <HFlex className={'gap-1.5'}>
            <Icon source={'eye'} size={24} />
            {item.views}
          </HFlex>
          <HFlex className={'gap-1.5'}>
            <Icon source={'heart'} size={24} />
            {item.likes}
          </HFlex>
          <HFlex className={'gap-1.5'}>
            <Icon source={'comment'} size={24} />
            {item.comments}
          </HFlex>
        </HFlex>
      </HFlex>

      <VFlex>
        <HFlex
          className={
            'min-h-[3.625rem] overflow-hidden border-l border-t border-primary ps-3.5'
          }
        >
          <ScrollArea className={'min-w-0 flex-grow'}>
            <HFlex className={'min-w-0 flex-grow gap-3.5'}>
              {ItemFields.map((field) => {
                const value = field.value(item);
                const icon = field.icon ? field.icon(item) : undefined;
                return !value ? null : (
                  <VFlex
                    key={field.label}
                    className={
                      'min-w-0 flex-shrink-0 flex-grow border-r border-primary py-1 pr-3.5 last:border-0'
                    }
                  >
                    <Text
                      className={'text-[0.875rem] text-daliaGray-300'}
                      title={field.label}
                    >
                      {field.label}
                    </Text>
                    <HFlex className={'items-center gap-1'}>
                      {icon && <Icon source={icon} size={12} />}
                      <Text className={'w-full items-center gap-1 truncate'}>
                        {value}
                      </Text>
                    </HFlex>
                  </VFlex>
                );
              })}
            </HFlex>
            <ScrollBar
              orientation={'horizontal'}
              className={'h-2 bg-daliaGray-200'}
            />
          </ScrollArea>
          <HFlex
            className={'w-[12.5rem] items-center justify-center bg-primary'}
          >
            {/*<AlertDialog*/}
            {/*  title={'Not implemented'}*/}
            {/*  content={*/}
            {/*    'This feature is not implement yet in the prototype version.'*/}
            {/*  }*/}
            {/*>*/}
            {/*  <IconButton*/}
            {/*    dark={true}*/}
            {/*    iconProps={{ size: 14 }}*/}
            {/*    source={'bookmark'}*/}
            {/*    disabled*/}
            {/*    title={'This functionality is not implemented yet.'}*/}
            {/*  />*/}
            {/*</AlertDialog>*/}
            {/*<ShareDialog item={item}>*/}
            {/*  <IconButton*/}
            {/*    dark={true}*/}
            {/*    iconProps={{ size: 14 }}*/}
            {/*    source={'share'}*/}
            {/*    disabled*/}
            {/*  />*/}
            {/*</ShareDialog>*/}
            {/*<CiteDialog item={item}>*/}
            {/*  <IconButton*/}
            {/*    dark={true}*/}
            {/*    iconProps={{ size: 14 }}*/}
            {/*    source={'cite'}*/}
            {/*    disabled*/}
            {/*  />*/}
            {/*</CiteDialog>*/}
            {/*<IconButton*/}
            {/*  dark={true}*/}
            {/*  iconProps={{ size: 14 }}*/}
            {/*  source={'cite'}*/}
            {/*  disabled*/}
            {/*/>*/}
            {ItemActions.map(({ Parent, disabled, ...action }, index) =>
              Parent ? (
                <Parent key={index} item={item}>
                  <IconButton
                    key={index}
                    {...action}
                  />
                </Parent>
              ) : (
                <AlertDialog
                  title={'Not implemented'}
                  key={index}
                  content={
                    'This feature is not implement yet in the prototype version.'
                  }
                >
                  <IconButton
                    {...action}
                    title={'This functionality is not implemented yet.'}
                  />
                </AlertDialog>
              )
            )}
          </HFlex>
        </HFlex>
        <HFlex className={'min-h-[3.625rem] border-l border-t border-primary'}>
          <VFlex className={'min-w-0 flex-grow pl-3.5 pt-1'}>
            <Text className={'text-[0.875rem] text-daliaGray-300'}>
              Authors
            </Text>
            {parseAuthors(item.authors)}
          </VFlex>
          <ResourceButton
            mainLink={item.url}
            links={item.links ?? []}
            className={
              'h-auto w-[12.5rem] shrink-0 grow-0 basis-[12.5rem] border-b-0'
            }
          />
        </HFlex>
        <HFlex className={'border-b border-l border-t border-primary ps-3.5'}>
          <VFlex className={'min-w-0 flex-grow py-1 pr-3.5'}>
            <Text className={'text-[0.875rem] text-daliaGray-300'}>
              Keywords
            </Text>
            <div className={'truncate [&>a]:mx-1'}>
              {item.tags && item.tags.length > 0 ? (
                item.tags.map((tag) => (
                  <Link
                    key={tag}
                    href={`/search?query=${encodeURIComponent(tag)}&offset=0&source=basic`}
                  >
                    <Text>#{tag}</Text>
                  </Link>
                ))
              ) : (
                <i>No keywords</i>
              )}
            </div>
          </VFlex>
          <Button
            dark
            trailIcon={'arrow-right'}
            className={
              'h-auto w-[12.5rem] shrink-0 grow-0 basis-[12.5rem] border-b-0'
            }
            link={{
              href: `/items/${item.id}/${item.slug}/`,
            }}
          >
            See Details
          </Button>
        </HFlex>
      </VFlex>
    </VFlex>
  );
};

export type ItemProps = Omit<
  React.DetailedHTMLProps<React.HTMLAttributes<HTMLDivElement>, HTMLDivElement>,
  'children' | 'ref'
> & {
  item: ItemObject;
  noBorder?: boolean;
  editable?: boolean;
  deletable?: boolean;
};

export default Item;
