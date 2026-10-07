'use client';
import React, { FC, useState } from 'react';
import { type ItemProps } from './Item';
import { HFlex, VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import Image from 'next/image';
import Icon from '@/components/Icon';
import Link from 'next/link';
import IconButton from '@/components/IconButton';
import Button from '@/components/Button';
import getImage from '@/lib/getImage';
import AlertDialog from '../AlertDialog';
import { cn } from '@/lib/utils';
import { parseAuthors } from '@/lib/parseAuthor';
import { ItemActions } from '@/components/Item/Actions';
import { GridItemFields } from '@/components/Item/Fields';
import { useWidth } from '@/lib/useWidth';
import { DeleteIcon, EditIcon } from 'lucide-react';
import ResourceButton from '@/components/ResourceButton';
import { useRouter } from 'next/navigation';
import { softDeleteResource } from '@/lib/api/item';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import { getCsrfTokenClient } from '@/lib/auth/csrfToken';
import InteractionButtons from '@/components/Item/InteractionButtons';

const GridItem: FC<ItemProps> = ({
  item,
  className,
  noBorder,
  editable,
  deletable = true,
  onRemove,
  isContribution,
  ...props
}) => {
  const [rootRef, width] = useWidth<HTMLDivElement>();
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

  const inactive = isContribution && item.is_active === false && !item.submitted_for_review;

  return (
    <VFlex
      {...props}
      className={cn(
        'justify-between p-7 transition hover:bg-gray-50 lg:gap-7',
        !noBorder && 'border border-primary',
        inactive && 'opacity-60 bg-gray-50',
        className
      )}
      ref={rootRef}
    >
      <VFlex className={'gap-7 pt-5 lg:pt-0'}>
        <HFlex className={'items-start justify-between'}>
          <Image
            src={item.image ?? getImage(item)}
            alt={item.title}
            width={105}
            height={135}
            className={'h-[8.43rem] w-[6.53rem]'}
            priority
          />
          <VFlex className={'items-end gap-1'}>
            <HFlex className={'gap-2.5'}>
              {editable && (
                <>
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
                </>
              )}
              <HFlex className={'gap-1.5'} key={'views'}>
                <Icon source={'eye'} size={24} />
                {item.views}
              </HFlex>
              <HFlex className={'gap-1.5'} key={'likes'}>
                <Icon source={'heart'} size={24} />
                {item.likes}
              </HFlex>
              <HFlex className={'gap-1.5'} key={'comments'}>
                <Icon source={'comment'} size={24} />
                {item.comments}
              </HFlex>
            </HFlex>
            {isContribution && (item.version ?? item.is_active !== undefined) && (
              <HFlex className={'gap-2'}>
                {item.version && (
                  <span className={'group/tip relative cursor-default rounded bg-daliaGray-200 px-1.5 py-0.5 text-xs font-medium text-white'}>
                    {item.version}
                    <span className={'pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs font-normal text-white shadow-md group-hover/tip:block'}>
                      DALIA version of this resource
                    </span>
                  </span>
                )}
                {item.is_active !== undefined && (
                  <span className={cn(
                    'group/tip relative cursor-default rounded px-1.5 py-0.5 text-xs font-medium',
                    item.submitted_for_review
                      ? 'bg-blue-100 text-blue-800'
                      : item.is_active
                      ? 'bg-green-100 text-green-800'
                      : item.submitted_for_review === false
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-gray-200 text-gray-600'
                  )}>
                    {item.submitted_for_review ? 'Submitted for review' : item.is_active ? 'Active' : item.submitted_for_review === false ? 'Draft' : 'Inactive'}
                    <span className={'pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs font-normal text-white shadow-md group-hover/tip:block'}>
                      {item.submitted_for_review
                        ? 'Waiting for curator review'
                        : item.is_active
                        ? 'Published and visible to others'
                        : item.submitted_for_review === false
                        ? 'Saved but not yet submitted for review'
                        : 'Not currently published'}
                    </span>
                  </span>
                )}
              </HFlex>
            )}
          </VFlex>
        </HFlex>
        <Text
          className={'line-clamp-3 text-[1.5rem] font-semibold'}
          title={item.title}
        >
          <Link href={`/items/${item.resource_uuid ?? item.id}/${item.slug}`}>{item.title}</Link>
        </Text>
        <Text className={'line-clamp-4'}>
          {item.description || <i>No description.</i>}
        </Text>
      </VFlex>
      <VFlex className={'gap-7 pt-5 lg:pt-0'}>
        <div className={'border-l border-t border-primary'}>
          <HFlex className={'flex-wrap'}>
            {GridItemFields.map((field) => {
              const value = field.value(item);
              const icon = field.icon ? field.icon(item) : undefined;
              return !value ? null : (
                <VFlex
                  key={field.label}
                  className={cn(
                    'h-[3.75rem] flex-grow overflow-hidden border-b border-r border-primary px-3.5 py-1'
                  )}
                >
                  <Text
                    className={'text-nowrap text-[0.875rem] text-daliaGray-300'}
                    title={field.label}
                  >
                    {field.label}
                  </Text>
                  <HFlex className={'items-center gap-1'}>
                    {icon && <Icon source={icon} size={12} />}
                    <Text className={'truncate'}>{value}</Text>
                  </HFlex>
                </VFlex>
              );
            })}
          </HFlex>
          <VFlex
            className={
              'grow-[6] basis-32 border-b border-r border-primary px-3.5 py-1'
            }
          >
            <Text className={'text-[0.875rem] text-daliaGray-300'}>
              Authors
            </Text>
            <div className={'w-full'}>{parseAuthors(item.authors)}</div>
          </VFlex>
          <VFlex
            className={
              'grow-[6] basis-32 overflow-hidden border-b border-r border-primary px-3.5 py-1'
            }
          >
            <Text className={'text-[0.875rem] text-daliaGray-300'}>
              Keywords
            </Text>
            <div className={'line-clamp-2 w-full break-all [&>a]:mx-1'}>
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
        </div>
        <div
          className={cn(
            'flex items-start justify-between overflow-hidden lg:flex-wrap',
            {
              'flex-row': width >= 640,
              'flex-col': width < 640,
            }
          )}
        >
          <HFlex>
            <InteractionButtons
              resourceId={item.resource_uuid ?? item.id}
              initialIsBookmarked={item.is_bookmarked}
              initialIsLiked={item.is_liked}
              initialLikes={item.likes}
              onRemove={onRemove}
            />
            {ItemActions.map(({ Parent, disabled, ...action }, index) =>
              Parent ? (
                <Parent key={index} item={item}>
                  <IconButton
                    key={index}
                    {...action}
                    className={cn(index > 1 && width < 640 && 'hidden')}
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
                    className={cn(index > 1 && width < 640 && 'hidden')}
                    title={'This functionality is not implemented yet.'}
                  />
                </AlertDialog>
              )
            )}
            {width < 640 && (
              <ResourceButton
                mainLink={item.url}
                links={item.links ?? []}
                className={'w-44 text-sm'}
              />
            )}
          </HFlex>
          <HFlex className={cn(width >= 640 && 'gap-2')}>
            {width < 640 &&
              ItemActions.map(({ Parent, disabled, ...action }, index) =>
                Parent ? (
                  <Parent key={index} item={item}>
                    <IconButton
                      key={index}
                      {...action}
                      className={cn(index <= 1 && 'hidden')}
                      title={'This functionality is not implemented yet.'}
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
                      className={cn(index <= 1 && 'hidden')}
                      title={'This functionality is not implemented yet.'}
                    />
                  </AlertDialog>
                )
              )}
            {width >= 640 && (
              <ResourceButton
                mainLink={item.url}
                links={item.links ?? []}
                className={'w-44 text-sm max-sm:hidden sm:w-auto'}
              />
            )}
            <Button
              className={cn('px-2 text-sm sm:ml-1 lg:ml-0 2xl:px-2', {
                'w-auto': width >= 640,
                'w-44': width < 640,
              })}
              dark
              link={{
                href: `/items/${item.resource_uuid ?? item.id}/${item.slug}/`,
              }}
            >
              See Details
              <Icon source={'arrow-right'} size={12} />
            </Button>
          </HFlex>
        </div>
      </VFlex>
    </VFlex>
  );
};

export default GridItem;
