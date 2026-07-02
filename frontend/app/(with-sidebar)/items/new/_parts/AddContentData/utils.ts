import {
  OrganizationAuthor,
  PersonAuthor,
  ResourceItem,
} from '@/lib/types/ItemTypes';
import { LabelValueChild, LabelValuePair } from '@/lib/types/Common';
import { NewItemData } from '@/app/(with-sidebar)/items/new/_parts/schema';
import {
  NEXT_PUBLIC_BACKEND_ROOT,
  SupportingCommunityRelationId,
} from '@/lib/settings.mjs';
import { apiFetch } from '@/lib/auth/apiFetch';
import { FieldValues, Path, UseFormReturn } from 'react-hook-form';

export function findDisciplinesFromString(
  data: LabelValueChild[],
  selected: string
): LabelValuePair | undefined {
  const found = data.find((d) => d.value === selected);
  if (found) {
    return found;
  }
  for (let i = 0; i < data.length; i++) {
    if (data[i].children.length > 0) {
      const foundInside = findDisciplinesFromString(data[i].children, selected);
      if (foundInside) {
        return foundInside;
      }
    }
  }
  return undefined;
}

/**
 * Given a discipline leaf value (slug or id string) and the loaded discipline
 * tree, returns the full path from root to that node as an array of `value`
 * strings — i.e. [rootValue, ..., leafValue]. This is the format expected by
 * the form schema (`disciplines: z.array(z.array(z.string()))`).
 *
 * Returns [] when the value is not found anywhere in the tree so that callers
 * can filter out unresolved disciplines instead of creating blank rows.
 */
export function findDisciplinePathInTree(
  value: string,
  tree: LabelValueChild[]
): string[] {
  for (const node of tree) {
    if (node.value === value) {
      return [node.value];
    }
    if (node.children.length > 0) {
      const childPath = findDisciplinePathInTree(value, node.children);
      if (childPath.length > 0) {
        return [node.value, ...childPath];
      }
    }
  }
  return [];
}

type formData = {
  title: string;
  authors: {
    people: PersonAuthor[];
    organizations: OrganizationAuthor[];
  };
  publicationDate: Date | undefined;
  types: LabelValuePair[];
  communities: ((LabelValuePair | Record<string, never>) & {
    is_supporting?: boolean;
    is_recommending?: boolean;
  })[];
  disciplines: LabelValuePair[];
  licenses: LabelValuePair[];
  languages: LabelValuePair[];
  links: string[];
  description: string;
  proficiencies: LabelValuePair[];
  targetGroups: LabelValuePair[];
  fileFormats: LabelValuePair[];
  mediaTypes: LabelValuePair[];
  version: string;
  size: string;
  keywords: string[];
  url: string;
  relations: {
    type?: LabelValuePair;
    link?: string;
  }[];
};

type FairScoreData = Omit<formData, 'title' | 'url' | 'licenses' | 'links'>;
export function createTempResourceItem({
  title,
  authors,
  relations,
  fileFormats,
  size,
  languages,
  publicationDate,
  proficiencies,
  mediaTypes,
  types,
  keywords,
  licenses,
  targetGroups,
  links,
  communities,
  description,
  disciplines,
  url,
}: formData): ResourceItem {
  return {
    authors: [...authors.people, ...authors.organizations],
    comments: 0,
    url,
    communities: communities.map((c) => ({
      id: c.value,
      slug: '',
      title: c.label,
      image: '',
      url: '',
      about: '',
      likes: 0,
      views: 0,
      followers: 0,
      is_recommending: !!c.is_recommending,
      is_supporting: !!c.is_supporting,
    })),
    description,
    disciplines,
    languages: languages.map((l) => l.label),
    doi: '',
    file_size: size,
    format: fileFormats.map((f) => f.label).join(', '),
    id: '',
    learning_resource_types: types,
    learning_time: 0,
    license: {
      id: licenses[0].value,
      name: licenses[0].label,
      link: '',
    },
    likes: 0,
    links: links,
    media_types: mediaTypes,
    proficiency_levels: proficiencies,
    publication_date: publicationDate?.toISOString().split('T')[0] ?? '',
    publisher: '',
    slug: '',
    tags: keywords.map((k) => k.trim()).filter((k) => k),
    target_groups: targetGroups,
    title: title,
    version: '',
    views: 0,
    related_works: relations.filter(
      (rel) => rel.type && rel.link
    ) as ResourceItem['related_works'],
  };
}

export function calculateFairScore(data: FairScoreData) {
  const allValues = Object.values(data);
  const hasValue = allValues.filter((value) => {
    if (value === null || value === undefined || value === '') {
      return;
    }
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return false;
      }
      if (typeof value[0] === 'object' && 'is_supporting' in value[0]) {
        return !!value[0].label;
      } else if (typeof value[0] === 'string') {
        return (value as string[]).findIndex((v) => !!v) > -1;
      } else if (typeof value[0] === 'object') {
        return value.findIndex((v) => Object.keys(v).length > 0) > -1;
      }
      return true;
    }
    if (typeof value === 'object') {
      if ('people' in value) {
        // people and organizations
        const hasOrcid = value.people.some((p) => !!p.orcid?.trim());
        const hasRor = value.organizations.some((o) => !!o.ror?.trim());
        return hasOrcid || hasRor;
      }
    }
    return !!value;
  });

  return Math.round((hasValue.length * 100) / allValues.length);
}

export async function submitData(
  data: NewItemData,
  accessKey: string,
  userId: number,
  disciplines: LabelValueChild[],
  resourceUuid?: string,
  idempotencyKey?: string
) {
  try {
    const result = await apiFetch('/api/curation/resource-contents/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessKey}`,
        ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
      },
      body: JSON.stringify({
        ...(resourceUuid ? { resource: resourceUuid } : {}),
        languages: data.languages.map((l) => l.value),
        title: data.title,
        main_url: data.url,
        publication_date: data.publicationDate
          ? new Date(data.publicationDate).toISOString().split('T')[0]
          : undefined,
        description: data.description,
        size_mb: data.size,
        submitted_for_review: true,
        // Server always overwrites created_by with request.user.pk before validation (views_curation.py:459),
        // so the {id} wrapper is ignored. Intentionally not fixed to avoid touching unrelated code;
        // the bare-integer form at submitUpdateData() (below) is the correct DRF format.
        created_by: { id: userId },
        people: data.people.filter((p) => p.id !== undefined).map((p) => p.id),
        organizations: data.organizations
          .filter((o) => o.id !== undefined)
          .map((o) => o.id),
        learning_resource_types: data.learningResourceTypes?.map(
          (lrt) => lrt.value
        ),
        disciplines: data.disciplines
          .map((disc) =>
            disc
              .map((s) => findDisciplinesFromString(disciplines, s))
              .filter((s) => s !== undefined)
          )
          .flat()
          .map((s) => Number(s.value)),
        licenses: data.licenses.map((l) => l.value),
        proficiency_levels: data.proficiencies.map((pl) => pl.value),
        target_groups: data.targetGroups.map((tg) => tg.value),
        file_formats: data.fileFormats.map((ff) => ff.value),
        media_types: data.mediaTypes.map((mt) => mt.value),
        keywords: data.keywords
          .split(',')
          .map((k) => k.trim())
          .filter(Boolean),
      }),
    });

    // Handle HTTP errors
    if (!result.ok) {
      const errorData = (await result.json().catch(() => ({}))) as Record<string, string[]> & { detail?: string };

      if (result.status === 403) {
        // Permission denied
        return {
          detail: [errorData.detail || 'You do not have permission to create this resource content.'],
        };
      } else if (result.status === 404) {
        // Not found
        return {
          detail: [errorData.detail || 'Resource not found.'],
        };
      } else {
        // Other errors - return validation errors or generic message
        if (errorData.detail) {
          return { detail: [errorData.detail] };
        }
        return errorData;
      }
    }

    const resultObject = (await result.json()) as
      | ResourceItem
      | null
      | Record<Exclude<string, 'id'>, string[]>;

    const relations: Promise<Response>[] = [];

    if (resultObject && 'id' in resultObject) {
      // handle related items
      let index = 0;
      for (const rw of data.relations) {
        if (!rw.type || !rw.link) {
          continue;
        }
        relations.push(
          apiFetch('/api/curation/related-items/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessKey}`,
            },
            body: JSON.stringify({
              order: index,
              target_url: rw.link,
              content: resultObject.id,
              relation_type: Number(rw.type.value),
            }),
          })
        );
        index += 1;
      }

      // handle communities
      index = 0;
      for (const c of data.communities) {
        if (!c.value) {
          continue;
        }
        relations.push(
          apiFetch('/api/curation/community-relations/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessKey}`,
            },
            body: JSON.stringify({
              order: index,
              content: resultObject.id,
              community: Number(c.value),
              relation_type: SupportingCommunityRelationId,
            }),
          })
        );
        index += 1;
      }
    }

    const relationResponses = await Promise.all(relations);

    // Check if any related items operations failed
    const failedRelations = relationResponses.filter((r) => !r.ok);
    if (failedRelations.length > 0) {
      console.error('[submitData] Failed to save some related items:', failedRelations);
      throw new Error('Failed to save some related items');
    }

    return resultObject;
  } catch {
    return null;
  }
}

export async function submitEditData(
  data: Partial<NewItemData>,
  itemUuid: string,
  accessKey: string,
  userId: number,
  disciplines: LabelValueChild[]
) {
  try {
    const rawEditData = {
      languages: data.languages?.map((l) => l.value),
      title: data.title,
      main_url: data.url,
      publication_date: data.publicationDate
        ? new Date(data.publicationDate).toISOString().split('T')[0]
        : undefined,
      description: data.description,
      size_mb: data.size,
      submitted_for_review: true,
      created_by: userId,
      people: data.people?.filter((p) => p.id !== undefined).map((p) => p.id),
      organizations: data.organizations
        ?.filter((o) => o.id !== undefined)
        .map((o) => o.id),
      learning_resource_types: data.learningResourceTypes?.map(
        (lrt) => lrt.value
      ),
      disciplines: data.disciplines
        ?.map((disc) =>
          disc
            .map((s) => findDisciplinesFromString(disciplines, s))
            .filter((s) => s !== undefined)
        )
        .flat()
        .map((s) => Number(s.value)),
      licenses: data.licenses?.map((l) => l.value),
      proficiency_levels: data.proficiencies?.map((pl) => pl.value),
      target_groups: data.targetGroups?.map((tg) => tg.value),
      file_formats: data.fileFormats?.map((ff) => ff.value).filter((v) => v !== 'unknown'),
      media_types: data.mediaTypes?.map((mt) => mt.value),
      keywords: data.keywords !== undefined
        ? data.keywords.split(',').map((k) => k.trim()).filter(Boolean)
        : undefined,
    };

    const editData = Object.fromEntries(
      Object.entries(rawEditData).filter(([_, v]) => v !== undefined)
    );

    console.log('[submitEditData] Sending data to backend:', JSON.stringify(editData, null, 2));

    const result = await apiFetch(
      `/api/curation/resource-contents/${itemUuid}/`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessKey}`,
        },
        body: JSON.stringify(editData),
      }
    );

    // Handle HTTP errors
    if (!result.ok) {
      const errorData = (await result.json().catch(() => ({}))) as Record<string, string[]> & { detail?: string };

      if (result.status === 403) {
        // Permission denied
        return {
          detail: [errorData.detail || 'You do not have permission to edit this resource content.'],
        };
      } else if (result.status === 404) {
        // Not found
        return {
          detail: [errorData.detail || 'Resource content not found.'],
        };
      } else {
        // Other errors - return validation errors or generic message
        if (errorData.detail) {
          return { detail: [errorData.detail] };
        }
        return errorData;
      }
    }

    const resultObject = (await result.json()) as
      | ResourceItem
      | null
      | Record<Exclude<string, 'id'>, string[]>;

    if (resultObject && 'id' in resultObject) {
      // Handle related items with smart merge (UPDATE existing by target_url, POST new, DELETE removed)
      if (data.relations !== undefined) {
        // Fetch existing related items
        const existingRelationsResponse = await fetch(
          NEXT_PUBLIC_BACKEND_ROOT + `/api/curation/related-items/?content=${itemUuid}`,
          {
            credentials: 'include',
            headers: {
              Authorization: `Bearer ${accessKey}`,
            },
          }
        );

        let existingRelations: Array<{ uuid: string; target_url: string; relation_type: number; order: number }> = [];
        if (existingRelationsResponse.ok) {
          const existingData = (await existingRelationsResponse.json()) as
            | { results: Array<{ uuid: string; target_url: string; relation_type: number; order: number }> }
            | Array<{ uuid: string; target_url: string; relation_type: number; order: number }>;
          existingRelations = ('results' in existingData ? existingData.results : existingData) || [];
        }

        // Build map of existing relations by target_url
        const existingByUrl = new Map(
          existingRelations.map((rel) => [rel.target_url, rel])
        );

        // Build map of new relations by target_url (filter out incomplete ones)
        const newRelations = data.relations
          .filter((rw) => rw.type && rw.link)
          .map((rw, index) => ({
            target_url: rw.link,
            relation_type: Number(rw.type!.value),
            order: index,
          }));

        const newByUrl = new Map(newRelations.map((rel) => [rel.target_url, rel]));

        const relationPromises: Promise<Response>[] = [];

        // UPDATE existing relations that are still present
        for (const newRel of newRelations) {
          const existing = existingByUrl.get(newRel.target_url);
          if (existing) {
            // Update if relation_type or order changed
            if (
              existing.relation_type !== newRel.relation_type ||
              existing.order !== newRel.order
            ) {
              relationPromises.push(
                apiFetch(`/api/curation/related-items/${existing.uuid}/`, {
                  method: 'PATCH',
                  headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${accessKey}`,
                  },
                  body: JSON.stringify({
                    relation_type: newRel.relation_type,
                    order: newRel.order,
                  }),
                })
              );
            }
          } else {
            // POST new relation
            relationPromises.push(
              apiFetch('/api/curation/related-items/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  Authorization: `Bearer ${accessKey}`,
                },
                body: JSON.stringify({
                  content: resultObject.id,
                  relation_type: newRel.relation_type,
                  target_url: newRel.target_url,
                  order: newRel.order,
                }),
              })
            );
          }
        }

        // DELETE relations that are no longer present
        for (const existing of existingRelations) {
          if (!newByUrl.has(existing.target_url)) {
            relationPromises.push(
              apiFetch(`/api/curation/related-items/${existing.uuid}/`, {
                method: 'DELETE',
                headers: {
                  Authorization: `Bearer ${accessKey}`,
                },
              })
            );
          }
        }

        const relationResponses = await Promise.all(relationPromises);

        // Check if any related items operations failed
        const failedRelations = relationResponses.filter((r) => !r.ok);
        if (failedRelations.length > 0) {
          console.error('[submitEditData] Failed to save some related items:', failedRelations);
          throw new Error('Failed to save some related items');
        }
      }

      // Handle communities with smart merge
      if (data.communities !== undefined) {
        // Fetch existing community relations
        const existingCommunitiesResponse = await fetch(
          NEXT_PUBLIC_BACKEND_ROOT + `/api/curation/community-relations/?content=${itemUuid}`,
          {
            credentials: 'include',
            headers: {
              Authorization: `Bearer ${accessKey}`,
            },
          }
        );

        let existingCommunities: Array<{ uuid: string; community: number; order: number }> = [];
        if (existingCommunitiesResponse.ok) {
          const existingData = (await existingCommunitiesResponse.json()) as
            | { results: Array<{ uuid: string; community: number; order: number }> }
            | Array<{ uuid: string; community: number; order: number }>;
          existingCommunities = ('results' in existingData ? existingData.results : existingData) || [];
        }

        // Build map of existing communities by community ID
        const existingByCommunity = new Map(
          existingCommunities.map((rel) => [rel.community, rel])
        );

        // Build map of new communities (filter out incomplete ones)
        const newCommunities = data.communities
          .filter((c) => c.value)
          .map((c, index) => ({
            community: Number(c.value),
            order: index,
          }));

        const newByCommunity = new Map(
          newCommunities.map((rel) => [rel.community, rel])
        );

        const communityPromises: Promise<Response>[] = [];

        // UPDATE existing community relations that are still present
        for (const newComm of newCommunities) {
          const existing = existingByCommunity.get(newComm.community);
          if (existing) {
            // Update if order changed
            if (existing.order !== newComm.order) {
              communityPromises.push(
                apiFetch(
                  `/api/curation/community-relations/${existing.uuid}/`,
                  {
                    method: 'PATCH',
                    headers: {
                      'Content-Type': 'application/json',
                      Authorization: `Bearer ${accessKey}`,
                    },
                    body: JSON.stringify({
                      order: newComm.order,
                    }),
                  }
                )
              );
            }
          } else {
            // POST new community relation
            communityPromises.push(
              apiFetch('/api/curation/community-relations/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  Authorization: `Bearer ${accessKey}`,
                },
                body: JSON.stringify({
                  content: (resultObject as unknown as {id: number}).id,
                  community: newComm.community,
                  relation_type: SupportingCommunityRelationId,
                  order: newComm.order,
                }),
              })
            );
          }
        }

        // DELETE community relations that are no longer present
        for (const existing of existingCommunities) {
          if (!newByCommunity.has(existing.community)) {
            communityPromises.push(
              apiFetch(
                `/api/curation/community-relations/${existing.uuid}/`,
                {
                  method: 'DELETE',
                  headers: {
                    Authorization: `Bearer ${accessKey}`,
                  },
                }
              )
            );
          }
        }

        await Promise.all(communityPromises);
      }
    }

    return resultObject;
  } catch {
    return null;
  }
}

export async function savePerson(author: PersonAuthor, accessKey: string) {
  try {
    const isNew = author.id === undefined;
    const orcidId = author.orcid
      ? new URL(author.orcid).pathname.substring(1)
      : undefined;

    const result = await apiFetch(
      `/api/curation/persons/${!isNew ? author.uuid + '/' : ''}`,
      {
        method: isNew ? 'POST' : 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessKey}`,
        },
        body: JSON.stringify({
          first_name: author.firstname,
          last_name: author.lastname,
          orcid: orcidId,
        }),
      }
    );
    return (await result.json()) as OrganizationAuthor | null;
  } catch (e) {
    console.log(e);
    return null;
  }
}

export async function saveOrganization(
  author: OrganizationAuthor,
  accessKey: string
) {
  try {
    const isNew = author.id === undefined;
    const result = await apiFetch(
      `/api/curation/organizations/${!isNew ? author.uuid + '/' : ''}`,
      {
        method: isNew ? 'POST' : 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessKey}`,
        },
        body: JSON.stringify({
          name: author.name,
          ror_id: author.ror,
        }),
      }
    );
    return (await result.json()) as OrganizationAuthor | null;
  } catch {
    return null;
  }
}

export async function saveCommunity(
  title: string,
  description: string,
  accessKey: string
): Promise<{ id: number; title: string; slug: string; uuid: string } | null> {
  try {
    const result = await apiFetch('/api/curation/communities/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessKey}`,
      },
      body: JSON.stringify({ title, description }),
    });
    if (!result.ok) return null;
    return (await result.json()) as {
      id: number;
      title: string;
      slug: string;
      uuid: string;
    };
  } catch {
    return null;
  }
}

const errorFieldMapping: Record<string, string> = {
  main_url: 'url',
  publication_date: 'publicationDate',
  size_mb: 'size',
  learning_resource_types: 'learningResourceTypes',
  proficiency_levels: 'proficiencies',
  target_groups: 'targetGroups',
  file_formats: 'fileFormats',
  media_types: 'mediaTypes',
};

export function loadErrorsToForm<T extends FieldValues>(
  form: UseFormReturn<T>,
  errors: Record<string, string[]> & {
    detail?: string;
  }
) {
  if ('detail' in errors) {
    form.setError('root', { message: errors.detail });
  } else {
    Object.entries(errors).forEach(([key, errs]) => {
      form.setError((errorFieldMapping[key] ?? key) as Path<T>, {
        type: 'server',
        message: (errs as string[]).join('. '),
      });
    });
  }
}

export function randomString(length = 10) {
  const chars =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}
