import {
  FieldKey,
  formatField,
  languagesField,
  learningResourceTypesField,
  licenseField,
  mediaTypesField,
  publicationField,
  sizeField,
} from '@/components/Item/Fields/common';

/**
 * A dictionary of the fields required for each type of item in SmallItem and Sidebars
 */
export const GridItemFields: FieldKey[] = [
  learningResourceTypesField,
  formatField,
  languagesField,
  mediaTypesField,
  publicationField,
  licenseField,
  sizeField,
];
