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
 * A dictionary of the fields required for each type of item in normal Item
 */
export const ItemFields: FieldKey[] = [
  learningResourceTypesField,
  formatField,
  languagesField,
  mediaTypesField,
  publicationField,
  licenseField,
  sizeField,
];
