import { z } from 'zod';
import { LabelValuePairSchema } from '@/lib/types/Common';
import {
  OrganizationAuthorSchema,
  PersonAuthorSchema,
} from '@/lib/types/ItemTypes';

export const addNewItemSchema = z
  .object({
    title: z.string().min(1, 'Title is mandatory'),
    url: z.string().url(),
    publicationDate: z
      .string()
      .refine((val) => val === '' || !isNaN(Date.parse(val)), {
        message: 'Invalid date string',
      }),
    people: z.array(PersonAuthorSchema),
    organizations: z.array(OrganizationAuthorSchema),
    learningResourceTypes: z.array(LabelValuePairSchema),
    languages: z.array(LabelValuePairSchema),
    communities: z.array(LabelValuePairSchema),
    disciplines: z.array(z.array(z.string())),
    licenses: z
      .array(LabelValuePairSchema)
      .min(1, 'Select at least one license'),
    links: z.array(z.string().url()),
    description: z.string(),
    proficiencies: z.array(LabelValuePairSchema),
    targetGroups: z.array(LabelValuePairSchema),
    fileFormats: z.array(LabelValuePairSchema),
    mediaTypes: z.array(LabelValuePairSchema),
    version: z.string(),
    size: z
      .string()
      .trim()
      // digits (optionally with a leading +) and optional fractional part
      .regex(/^$|^\+?\d+(?:\.\d+)?$/, {
        message:
          "Use a positive number format like '3', '+3', '3.14', or '0.5'.",
      })
      .refine(
        (s) => {
          if (s === '') {
            return true;
          }
          // strip optional + and leading zeros, then remove the decimal point
          const digits = s.replace(/^\+?0+/, '').replace('.', '');
          // at least one non-zero digit must remain
          return /[1-9]/.test(digits);
        },
        { message: 'Must be greater than 0.' }
      ),
    keywords: z.string(),
    relations: z.array(
      z.object({
        type: LabelValuePairSchema.optional(),
        link: z.string().refine(
          (val: string) => {
            if (!val) return false;
            try {
              new URL(val);
              return true;
            } catch {
              return false;
            }
          },
          { message: 'Invalid URL' }
        ),
      })
    ),
  })
  .refine(
    ({ people, organizations }) =>
      people.length > 0 || organizations.length > 0,
    {
      message: 'Authors is required.',
      path: ['people'],
    }
  );

export type NewItemData = z.infer<typeof addNewItemSchema>;
