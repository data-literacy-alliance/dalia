import SearchBox from '@/app/(search)/basic/_parts/SearchBox';

export default async function BasicSearch({
  searchParams,
}: {
  searchParams: { query?: string };
}) {
  const query = searchParams.query || '';

  return <SearchBox initQuery={query} />;
}
