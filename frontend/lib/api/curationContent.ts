import { ResourceItem } from '@/lib/types/ItemTypes';

export type ResourceContentResponse = {
  id: number;
  uuid: string;
  title: string;
  main_url: string;
  description: string;
  publication_date: string | null;
  people: Array<{
    id: number;
    uuid: string;
    first_name: string;
    last_name: string;
    orcid: string;
  }>;
  organizations: Array<{
    id: number;
    uuid: string;
    name?: string;
    ror?: string;
  }>;
  languages: Array<{
    id: number;
    code: string;
    label: string;
    native_name: string;
  }>;
  learning_resource_types: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  disciplines: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  licenses: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
    spdx_id: string;
  }>;
  proficiency_levels: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  target_groups: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  file_formats: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  media_types: Array<{
    id: number;
    uuid: string;
    label: string;
    slug: string;
  }>;
  size_mb: string | null;
  version_label?: string;
  resource_uuid?: string;
  submitted_for_review?: boolean;
  is_active?: boolean;
  keywords?: string[];
};

export function transformResourceContentToItem(content: ResourceContentResponse): ResourceItem {
  const authors = [
    ...(Array.isArray(content.people) ? content.people : []).map((p) => ({
      firstname: p.first_name || '',
      lastname: p.last_name || '',
      orcid: p.orcid || '',
      authorType: 'PersonAuthor' as const,
      id: p.id,
      uuid: p.uuid,
    })),
    ...(Array.isArray(content.organizations) ? content.organizations : []).map((o) => ({
      name: o.name || '',
      ror: o.ror || '',
      authorType: 'OrganizationAuthor' as const,
      id: o.id,
      uuid: o.uuid,
    })),
  ];

  return {
    id: content.uuid || String(content.id),
    slug: content.uuid || String(content.id),
    title: content.title || 'Untitled',
    url: content.main_url || '',
    description: content.description || '',
    authors,
    communities: null,
    likes: 0,
    views: 0,
    comments: 0,
    tags: Array.isArray(content.keywords) ? content.keywords : [],
    related_works: [],
    learning_resource_types: Array.isArray(content.learning_resource_types)
      ? content.learning_resource_types.map((t) => ({
          label: t.label || '',
          value: String(t.id),
        }))
      : [],
    media_types: Array.isArray(content.media_types)
      ? content.media_types.map((t) => ({
          label: t.label || '',
          value: String(t.id),
        }))
      : [],
    disciplines: Array.isArray(content.disciplines)
      ? content.disciplines.map((d) => ({
          label: d.label || '',
          value: String(d.id),
        }))
      : [],
    target_groups: Array.isArray(content.target_groups)
      ? content.target_groups.map((t) => ({
          label: t.label || '',
          value: String(t.id),
        }))
      : [],
    proficiency_levels: Array.isArray(content.proficiency_levels)
      ? content.proficiency_levels.map((p) => ({
          label: p.label || '',
          value: String(p.id),
        }))
      : [],
    format: Array.isArray(content.file_formats) ? content.file_formats : [],
    license:
      Array.isArray(content.licenses) && content.licenses[0]
        ? {
            id: String(content.licenses[0].id),
            name: content.licenses[0].label || '',
            link: '',
          }
        : { id: '', name: '', link: '' },
    publication_date: content.publication_date || '',
    links: [],
    languages: Array.isArray(content.languages)
      ? content.languages.map((l) => ({
          id: l.id,
          label: l.label || l.code || '',
          code: l.code,
        }))
      : [],
    file_size: content.size_mb ? `${content.size_mb} MB` : undefined,
    version: content.version_label || undefined,
    resource_uuid: content.resource_uuid,
    submitted_for_review: content.submitted_for_review,
  };
}
