import { Author } from '@/lib/types/ItemTypes';
import Link from 'next/link';
import Image from 'next/image';
import { BASE_PATH } from '@/lib/settings.mjs';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Building2Icon } from 'lucide-react';
import { Fragment } from 'react';

export default function parseAuthor(author: Author) {
  if ('firstname' in author) {
    return (
      <span className={'inline-flex items-center'}>
        <Link
          title={`${author.firstname} ${author.lastname}`}
          className={
            'text-nowrap rounded bg-primary px-2 font-light text-white hover:text-white'
          }
          href={`/search?query=${encodeURIComponent(author.firstname + ' ' + author.lastname)}&offset=0&source=basic`}
        >
          {author.firstname} {author.lastname}
        </Link>

        {author.orcid && (
          <Link href={author.orcid} target={'_blank'}>
            <Image
              src={`${BASE_PATH}/images/ORCIDLogo.png`}
              alt={`${author.firstname} ${author.lastname}`}
              className={'h-6 w-6'}
              width={24}
              height={24}
            />
          </Link>
        )}
      </span>
    );
  }
  return (
    <Link
      title={author.name}
      className={
        'inline-flex items-center gap-2 text-nowrap rounded bg-primary px-2 font-light text-white hover:text-white'
      }
      href={`/search?query=${encodeURIComponent(author.name)}&offset=0&source=basic`}
    >
      {author.name} <Building2Icon size={16} />
    </Link>
  );
}

export function parseAuthors(authors: Author[]) {
  return (
    <ScrollArea className={'h-full w-full whitespace-nowrap'}>
      <div>
        {authors.length > 0 ? (
          authors.map((author, index, allAuthors) => (
            <Fragment key={index}>
              {parseAuthor(author)}
              {index < allAuthors.length - 1 && <span> | </span>}
            </Fragment>
          ))
        ) : (
          <i>No Authors</i>
        )}
      </div>
      <ScrollBar
        orientation={'horizontal'}
        className={'h-2 bg-daliaGray-200'}
      />
    </ScrollArea>
  );
}
