import { z } from 'zod';
import { OrcidIdSchema } from '@/lib/types/ItemTypes';

export const preferencesForm = z.object({
  homepage: z.string().url().or(z.literal('')),
  orcid: OrcidIdSchema.or(z.literal('')),
  privacy_level: z.literal('public').or(z.literal('internal')).or(z.literal('private')),
  sync_name_from_provider: z.boolean(),
});

export type preferencesForm = z.infer<typeof preferencesForm>;
