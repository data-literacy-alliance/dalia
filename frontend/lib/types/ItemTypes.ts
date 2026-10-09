import { Community } from '@/lib/types/Community';
import { LabelValuePair } from '@/lib/types/Common';
import { z } from 'zod';

export const OrcidIdSchema = z.string().regex(/^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$/);

export const PersonAuthorSchema = z.object({
  firstname: z.string().min(1),
  lastname: z.string().min(1),
  orcid: z
    .string()
    .regex(
      /^$|^https:\/\/orcid\.org\/\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$/,
      'Invalid ORCID link.'
    )
    .optional(),
  authorType: z.literal('PersonAuthor'),
  id: z.number().optional(),
  uuid: z.string().optional(),
});
export type PersonAuthor = z.infer<typeof PersonAuthorSchema>;

export const OrganizationAuthorSchema = z.object({
  name: z.string().min(1),
  ror: z
    .string()
    .regex(
      /^$|^https:\/\/ror\.org\/[0-9a-z]{9}$/,
      'Must be empty or a valid ROR link'
    )
    .optional(),
  authorType: z.literal('OrganizationAuthor'),
  id: z.number().optional(),
  uuid: z.string().optional(),
});
export type OrganizationAuthor = z.infer<typeof OrganizationAuthorSchema>;

export type Author = PersonAuthor | OrganizationAuthor;

export type ItemLicense = {
  id: string; // based on https://github.com/spdx/license-list-data/blob/main/rdfturtle/CC-BY-4.0.ttl
  name: string;
  link: string;
};

export type BaseItem = {
  id: string;
  slug: string;
  title: string;
  communities:
    | (Community & {
        is_supporting: boolean;
        is_recommending: boolean;
      })[]
    | null;
  description: string;
  authors: Author[];
  url: string;
  image?: string;
  likes: number;
  views: number;
  comments: number;
  is_bookmarked?: boolean;
  is_liked?: boolean;
  is_active?: boolean;
  tags?: string[];
  related_works?: {
    type: LabelValuePair;
    link: string;
  }[];
};

export type ResourceItem = BaseItem & {
  // type: string; //  'lesson' | 'poster' | 'presentation';
  learning_resource_types: LabelValuePair[];
  media_types: LabelValuePair[];
  disciplines: LabelValuePair[];
  target_groups: LabelValuePair[];
  proficiency_levels: LabelValuePair[];
  format: string | Array<{ id: number; label: string; slug: string }>; // 'pdf' | 'powerpoint' or file format objects
  license: ItemLicense;
  publication_date: string;
  links: string[];
  languages: (string | { id: number; label: string; code: string })[];
  file_size?: string;
  publisher?: string;
  doi?: string;
  learning_time?: number;
  version?: string;
  resource_uuid?: string;
  submitted_for_review?: boolean;
};

export type ItemObject = ResourceItem;
