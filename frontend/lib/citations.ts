import { Author, ResourceItem } from '@/lib/types/ItemTypes';

export type CitationProvider = {
  title: string;
  multiline: boolean;
  generator: (item: ResourceItem) => string;
};

const nameFn = (author: Author) => {
  if ('firstname' in author) {
    return `${author.lastname}, ${author.firstname}`;
  }
  return author.name;
};

export const citationProviders: CitationProvider[] = [
  {
    title: 'APA Citation',
    multiline: false,
    generator: (item) => {
      // get first 20 authors
      const authorsArray = item.authors.slice(0, 20).map((author) => {
        if ('firstname' in author) {
          const firstInitial = author.firstname ? author.firstname[0] : '';
          return `${author.lastname}, ${firstInitial}`;
        }
        return author.name;
      });

      const formattedAuthors =
        authorsArray.length <= 20
          ? authorsArray.length > 1
            ? `${authorsArray.slice(0, -1).join(', ')}, & ${authorsArray[authorsArray.length - 1]}`
            : authorsArray[0]
          : // more than 20 authors;
            authorsArray.slice(0, 19).join(', ') +
            ' ... ' +
            authorsArray[authorsArray.length - 1];

      return `${formattedAuthors}.${item.publication_date ? `(${item.publication_date}).` : ''} ${item.title}. DALIA. https://bioregistry.io/dalia.oer:${item.id}`;
    },
  },
  {
    title: 'MLA Citation',
    multiline: false,
    generator: (item) => {
      const formattedAuthors =
        item.authors.length > 2
          ? (item.authors[0] ? nameFn(item.authors[0]) + ' et al' : '')
          : item.authors.slice(0, 2).map(nameFn).join(', and ');

      return `${formattedAuthors}. *${item.title}*. DALIA${item.publication_date ? `, ${item.publication_date}` : ''}. Web. <https://bioregistry.io/dalia.oer:${item.id}>`;
    },
  },
  {
    title: 'BibTex',
    multiline: true,
    generator: (item) => {
      const formattedAuthors = item.authors.map(nameFn).join(' and ');
      return (
        `@misc{dalia_oer_${item.id.slice(0, 8)},\n` +
        `  author       = {${formattedAuthors}},\n` +
        `  title        = {${item.title}},\n` +
        `${item.publication_date ? `  year         = {${item.publication_date}},\n` : ''}` +
        `  howpublished = {\\url{https://bioregistry.io/dalia.oer:${item.id}}, \\url{${item.url}}},\n` +
        `  url          = {\\url{https://bioregistry.io/dalia.oer:${item.id}}},\n` +
        `  url          = {\\url{${item.url}}},\n` +
        `  note         = {Accessed via DALIA using Bioregistry prefix dalia.oer}\n}`
      );
    },
  },
];
