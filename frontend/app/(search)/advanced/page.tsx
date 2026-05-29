import AdvancedSearchBox from '@/app/(search)/advanced/_parts/AdvancedSearchBox';
import { getBasicSearchFilters } from '@/lib/api/filters';

export const dynamic = 'force-dynamic';

export default async function AdvancedSearchPage({
  searchParams,
}: {
  searchParams: { query?: string };
}) {
  const filters = await getBasicSearchFilters();
  const query = searchParams.query || '';

  return <AdvancedSearchBox filters={filters} initQuery={query} />;
  // return (
  //   <HFlex className="items-center justify-center h-full pt-10">
  //     <div className={'bg-daliaGray-100 p-10'}>
  //       Sorry, this page has been disabled. We will adapt the advanced search to
  //       more specific metadata based on community feedback. The improved variant
  //       of the advanced search will be available in December 2024.
  //     </div>
  //   </HFlex>
  // );
}
