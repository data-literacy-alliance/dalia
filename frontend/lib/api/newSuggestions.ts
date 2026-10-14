'use client';
import useSWR from 'swr';
import { useMemo } from 'react';
import { authFetcher } from '@/lib/auth/authApi';
import { LabelValueChild } from '@/lib/types/Common';

type NewSuggestionItem = {
  id: number;
  uuid: string;
  created: string;
  modified: string;
  is_active: boolean;
  label: string;
  title?: string;
  description: string;
  url: string;
};

type NewDisciplineItem = {
  id: number;
  uuid: string;
  children_count: number;
  level: number;
  is_root: boolean;
  ancestors: {
    id: number;
    label: string;
    uuid: string;
  }[];
  created: string;
  modified: string;
  is_active: boolean;
  label: string;
  slug: string;
  uri: string;
  parent_label: string;
  parent_id: number;
};

type PersonItem = {
  id: number;
  uuid: string;
  created: string;
  modified: string;
  is_active: boolean;
  first_name: string;
  last_name: string;
  orcid: string;
  homepage: string;
  privacy_level: string;
  user: number | null;
};

type OrganizationItem = {
  id: number;
  uuid: string;
  created: string;
  modified: string;
  is_active: boolean;
  name: string;
  ror_id: string;
  homepage: string;
  uri: string;
  parent_organization: number;
};

export function useNewSuggestions(
  key: string | null | undefined,
  params: URLSearchParams
) {
  const { data, isLoading } = useSWR<NewSuggestionItem[]>(
    !key ? null : `/api/curation/${key}/?${params}`,
    authFetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return useMemo(
    () => ({
      items:
        data
          ?.filter((item) => item.is_active)
          .map((item) =>
            item.title
              ? { ...item, value: item.id.toString(), label: item.title }
              : { ...item, value: item.id.toString() }
          ) ?? [],
      isLoading,
    }),
    [data, isLoading]
  );
}

function parseNewDisciplines(
  allDisciplines: NewDisciplineItem[]
): LabelValueChild[] {
  const idToNode = new Map<number, LabelValueChild>();
  const roots: LabelValueChild[] = [];

  // First pass: create all nodes
  for (const item of allDisciplines) {
    idToNode.set(item.id, {
      label: item.label,
      value: item.id.toString(),
      children: [],
    });
  }

  // Second pass: link children to parents; collect roots
  for (const item of allDisciplines) {
    const node = idToNode.get(item.id)!;
    const parentId = item.parent_id;

    // Consider root if parent_id is 0/null/undefined or parent not found
    if (parentId == null || parentId === 0 || !idToNode.has(parentId)) {
      roots.push(node);
    } else {
      idToNode.get(parentId)!.children.push(node);
    }
  }

  return roots;
}

export function useNewDisciplines(skip: boolean) {
  const { data, isLoading } = useSWR<NewDisciplineItem[]>(
    !skip ? '/api/curation/disciplines/' : null,
    authFetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return useMemo(
    () => ({
      items: data ? parseNewDisciplines(data) : [],
      isLoading,
    }),
    [data, isLoading]
  );
}

export function useSearchPersons(query: string) {
  const { data, isLoading } = useSWR<PersonItem[]>(
    query ? `/api/curation/persons/?search=${encodeURIComponent(query)}` : null,
    authFetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    persons: data,
    isLoading,
  };
}

export function useSearchOrganizations(query: string | null) {
  const { data, isLoading } = useSWR<OrganizationItem[]>(
    query
      ? `/api/curation/organizations/?search=${encodeURIComponent(query)}`
      : null,
    authFetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    organizations: data,
    isLoading,
  };
}
