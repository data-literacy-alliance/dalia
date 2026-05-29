import { z } from 'zod';
import { OrcidIdSchema } from '@/lib/types/ItemTypes';

export const preferencesForm = z.object({
  first_name: z.string().min(1, 'Given name is required'),
  last_name: z.string().min(1, 'Family name is required'),
  homepage: z.string().url().or(z.literal('')),
  orcid: OrcidIdSchema.or(z.literal('')),
  privacy_level: z.literal('public').or(z.literal('internal')).or(z.literal('private')),
});

export type preferencesForm = z.infer<typeof preferencesForm>;
