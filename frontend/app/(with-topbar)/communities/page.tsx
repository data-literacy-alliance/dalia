import CommunityListBody from '@/app/(with-topbar)/communities/_parts/CommunityListBody';
import { getSuggestionsWithPagination } from '@/lib/api/suggestions';

export const dynamic = 'force-dynamic';

export default async function CommunityListPage() {
  const communities = await getSuggestionsWithPagination(
    'communities',
    '',
    999,
    0
  );

  return <CommunityListBody communities={communities.results} />;
}
