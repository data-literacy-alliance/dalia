import {
  FieldKey,
  formatField,
  languagesField,
  learningResourceTypesField,
  mediaTypesField,
  publicationField,
  sizeField,
} from './common';

/**
 * A dictionary of the fields required for each type of item in sidebar
 */
export const SidebarFields: FieldKey[] = [
  languagesField,
  learningResourceTypesField,
  mediaTypesField,
  formatField,
  sizeField,
  publicationField,
];
