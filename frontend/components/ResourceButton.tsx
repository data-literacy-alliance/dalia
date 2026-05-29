import React, { ComponentProps, FC } from 'react';
import Button from '@/components/Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import Link from 'next/link';

const ResourceButton: FC<ResourceButtonProps> = ({
  mainLink,
  links: initLinks,
  ...props
}) => {
  // Defensive handling for null/undefined links (e.g., from cached responses)
  const links = Array.isArray(initLinks) ? [...initLinks] : [];

  return links.length === 0 ? (
    <Button
      trailIcon={'arrow-top-right'}
      trailIconSize={10}
      dark
      link={{
        href: mainLink,
        target: '_blank',
      }}
      {...props}
    >
      Go to Resource
    </Button>
  ) : (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          trailIcon={'arrow-top-right'}
          trailIconSize={10}
          dark
          {...props}
        >
          Go to Resource
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Resource Links</DialogTitle>
          <DialogDescription>
            This resource has more than one link
          </DialogDescription>
        </DialogHeader>
        <div>
          <ol className={'ml-4 list-inside list-decimal'}>
            <li>
              <Link href={mainLink} target={'_blank'}>
                {mainLink}
              </Link>
            </li>
            {links.map((link) => (
              <li key={link}>
                <Link href={link} target={'_blank'}>
                  {link}
                </Link>
              </li>
            ))}
          </ol>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export type ResourceButtonProps = Omit<
  ComponentProps<typeof Button>,
  'children'
> & {
  mainLink: string;
  links: string[];
};

export default ResourceButton;
