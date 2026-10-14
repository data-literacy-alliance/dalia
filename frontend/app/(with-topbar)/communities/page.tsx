import CommunityListBody from '@/app/(with-topbar)/communities/_parts/CommunityListBody';
import appFetch from '@/lib/api/fetch';

export const dynamic = 'force-dynamic';

type SuggestResult = {
  count: number;
  results: Array<{ label: string; value: string }>;
};

export default async function CommunityListPage() {
  // /v1/curation/suggest/communities/ merges Fuseki + PostgreSQL and returns UUIDs
  const res = await appFetch('/curation/suggest/communities/?limit=2000');
  const data: SuggestResult = res?.ok
    ? (await res.json() as SuggestResult)
    : { count: 0, results: [] };

  const communities = data.results.map((item) => ({
    uuid: item.value.split('/').pop() ?? item.value,
    title: item.label,
  }));

  return <CommunityListBody communities={communities} />;
}
