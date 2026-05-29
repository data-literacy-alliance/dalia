import { NextRequest, NextResponse } from 'next/server';

const FUSEKI_ENDPOINT = process.env.FUSEKI_ENDPOINT || 'http://prod-fuseki:3030/dalia/query';
const MAX_LIMIT = parseInt(process.env.NEXT_PUBLIC_SPARQL_MAX_LIMIT || '1000', 10);

// CORS headers for browser access
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400', // 24 hours
};

// Keywords that indicate write operations - these are forbidden
const FORBIDDEN_KEYWORDS = [
  'INSERT', 'DELETE', 'DROP', 'CLEAR',
  'CREATE', 'LOAD', 'ADD', 'MOVE', 'COPY'
];

/**
 * Validates that a SPARQL query is read-only
 * @param query - The SPARQL query string
 * @returns true if query is read-only, false otherwise
 */
function isReadOnlyQuery(query: string): boolean {
  const upperQuery = query.toUpperCase();
  return !FORBIDDEN_KEYWORDS.some(kw => upperQuery.includes(kw));
}

/**
 * Enforces maximum LIMIT clause in query
 * @param query - The SPARQL query string
 * @returns Modified query with enforced limit
 */
function enforceLimitClause(query: string): string {
  const limitRegex = /LIMIT\s+(\d+)/i;
  const match = query.match(limitRegex);

  if (match) {
    const requestedLimit = parseInt(match[1], 10);
    if (requestedLimit > MAX_LIMIT) {
      return query.replace(limitRegex, `LIMIT ${MAX_LIMIT}`);
    }
  } else {
    // If no LIMIT clause, add one
    return `${query.trim()}\nLIMIT ${MAX_LIMIT}`;
  }

  return query;
}

/**
 * OPTIONS /api/sparql
 * Handle CORS preflight requests
 */
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

/**
 * POST /api/sparql
 * Execute a SPARQL query against the Fuseki endpoint
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json() as { query?: unknown };
    const { query } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query parameter is required and must be a string' },
        { status: 400, headers: CORS_HEADERS }
      );
    }

    // Security: Validate read-only
    if (!isReadOnlyQuery(query)) {
      return NextResponse.json(
        {
          error: 'Only read queries (SELECT, ASK, DESCRIBE, CONSTRUCT) are allowed',
          details: 'Write operations (INSERT, DELETE, DROP, etc.) are forbidden'
        },
        { status: 403, headers: CORS_HEADERS }
      );
    }

    // Enforce limit
    const limitedQuery = enforceLimitClause(query);

    // Proxy to Fuseki
    const response = await fetch(FUSEKI_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/sparql-query',
        'Accept': 'application/sparql-results+json',
      },
      body: limitedQuery,
      // Set timeout to 30 seconds
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`SPARQL query failed. Status: ${response.status}, Endpoint: ${FUSEKI_ENDPOINT}`);
      console.error('Response:', errorText.substring(0, 500));
      return NextResponse.json(
        {
          error: 'SPARQL query failed',
          details: `Status ${response.status}: ${errorText.substring(0, 200)}`,
          endpoint: FUSEKI_ENDPOINT,
          status: response.status
        },
        { status: response.status, headers: CORS_HEADERS }
      );
    }

    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/sparql-results+json') && !contentType.includes('application/json')) {
      const textResponse = await response.text();
      console.error(`Invalid content-type from Fuseki: ${contentType}`);
      console.error('Response:', textResponse.substring(0, 500));
      return NextResponse.json(
        {
          error: 'Invalid response from SPARQL endpoint',
          details: `Expected JSON but got: ${contentType}`,
          endpoint: FUSEKI_ENDPOINT,
          preview: textResponse.substring(0, 200)
        },
        { status: 500, headers: CORS_HEADERS }
      );
    }

    const data = await response.json() as Record<string, unknown>;
    return NextResponse.json(data, { headers: CORS_HEADERS });

  } catch (error) {
    console.error('SPARQL proxy error:', error);

    const err = error as Error & { name?: string };

    if (err.name === 'TimeoutError' || err.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Query timeout exceeded (30 seconds)' },
        { status: 504, headers: CORS_HEADERS }
      );
    }

    return NextResponse.json(
      {
        error: 'Internal server error',
        details: err.message || 'Unknown error'
      },
      { status: 500, headers: CORS_HEADERS }
    );
  }
}

/**
 * GET /api/sparql?query=...
 * Execute a SPARQL query via URL parameter
 */
export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get('query');

  if (!query) {
    return NextResponse.json(
      { error: 'Query parameter is required' },
      { status: 400, headers: CORS_HEADERS }
    );
  }

  // Reuse POST logic
  return POST(
    new NextRequest(request.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: decodeURIComponent(query) }),
    })
  );
}
