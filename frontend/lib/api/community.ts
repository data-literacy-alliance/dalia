import appFetch from '@/lib/api/fetch';
import { Community } from '@/lib/types/Community';
import { ItemObject } from '@/lib/types/ItemTypes';

export async function getCommunity(id: string) {
  const data = await appFetch(`/communities/${id}/`);

  if (!data?.ok) {
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return data.json() as Promise<Community>;
}

export async function getCommunityItems(id: string) {
  const data = await appFetch(`/communities/${id}/items/`);

  if (!data?.ok) {
    if (data?.status === 404) {
      return [] as ItemObject[];
    }
    throw new Error(`${data.status}: ${data.statusText}`);
  }

  return data.json() as Promise<ItemObject[]>;
}
