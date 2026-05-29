import { ItemObject } from '@/lib/types/ItemTypes';
import { ReactNode } from 'react';
import { IconSource } from '@/components/Icon';
import Link from 'next/link';
import { getLicenseIcons } from '@/lib/licenseUtils';
import { getLanguageName } from '@/lib/languageUtils';
import { formatFileSize } from '@/lib/utils';

export type FieldKey = {
  label: string;
  value: (item: ItemObject) => ReactNode;
  icon?: (item: ItemObject) => IconSource | undefined;
  property?: string;
};

export const formatField: FieldKey = {
  label: 'File Format',
  value: (i) => {
    if (typeof i.format === 'string') {
      return i.format;
    }
    if (Array.isArray(i.format)) {
      return i.format.map((f) => f.label).join(', ') || 'Unknown';
    }
    return 'Unknown';
  },
  icon: (i) => {
    const format = typeof i.format === 'string' ? i.format : '';
    switch (format) {
      case 'Powerpoint':
        return 'slide';
      case 'PDF':
        return 'data';
      case 'Image':
        return 'image';
      case 'Website':
        return 'document';
      default:
        return undefined;
    }
  },
  property: 'dcterms:format',
};

export const sizeField: FieldKey = {
  label: 'Size',
  value: (i) => i.file_size ? formatFileSize(i.file_size) : '',
  property: 'dcterms:extent',
};

export const publicationField: FieldKey = {
  label: 'Publication Date',
  value: (i) => i.publication_date,
  property: 'dcterms:issued',
};

export const languagesField: FieldKey = {
  label: 'Languages',
  value: (i) =>
    i.languages.length === 0
      ? ''
      : i.languages.map((l) => (typeof l === 'string' ? getLanguageName(l) : l.label)).join(', '),
  property: 'dcterms:language',
};

export const learningResourceTypesField: FieldKey = {
  label: 'Learning Resource Type',
  value: (i) => i.learning_resource_types.map((lrs) => lrs.label).join(', '),
  property: 'mo:hasLearningType',
};

export const mediaTypesField: FieldKey = {
  label: 'Media Type',
  value: (i) => i.media_types.map((lrs) => lrs.label).join(', '),
  property: 'mo:hasMediaType',
};

export const disciplinesField: FieldKey = {
  label: 'Discipline',
  value: (i) => i.disciplines.map((lrs) => lrs.label).join(', '),
};

export const targetGroupsField: FieldKey = {
  label: 'Target Group',
  value: (i) => i.target_groups.map((lrs) => lrs.label).join(', '),
};

export const proficiencyLevelsField: FieldKey = {
  label: 'Proficiency level',
  value: (i) => i.proficiency_levels.map((lrs) => lrs.label).join(', '),
};

export const licenseField: FieldKey = {
  label: 'License',
  value: (i) =>
    i.license &&
    (i.license.link ? (
      <Link href={i.license.link} target={'_blank'}>
        {getLicenseIcons(i.license.id)}
      </Link>
    ) : (
      getLicenseIcons(i.license.id)
    )),
  property: 'dcterms:license',
};

// May be used in the future
// const typeFiled: FieldKey = {
//   label: 'Type',
//   value: (i) => i.type,
//   icon: (i) => {
//     switch (i.type) {
//       case 'Poster':
//         return 'image';
//       case 'Lesson':
//         return 'hat';
//       case 'Event':
//         return 'binary';
//       case 'Presentation':
//         return 'graph';
//       default:
//         return undefined;
//     }
//   },
// };
