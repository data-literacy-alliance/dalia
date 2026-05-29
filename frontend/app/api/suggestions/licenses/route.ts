import { NextRequest, NextResponse } from 'next/server';
import { getLicenseSuggestions } from '@/lib/api/suggestions';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get('q') ?? '';
  const limit = searchParams.has('limit')
    ? Number(searchParams.get('limit'))
    : undefined;
  const offset = searchParams.has('offset')
    ? Number(searchParams.get('offset'))
    : undefined;

  return NextResponse.json(await getLicenseSuggestions(query, limit, offset));
}
