/**
 * SPARQL Query Validation Utilities
 */

// Keywords that indicate write operations
const FORBIDDEN_KEYWORDS = [
  'INSERT', 'DELETE', 'DROP', 'CLEAR',
  'CREATE', 'LOAD', 'ADD', 'MOVE', 'COPY'
];

// Valid read-only query types
const VALID_QUERY_TYPES = [
  'SELECT', 'ASK', 'DESCRIBE', 'CONSTRUCT'
];

/**
 * Validates that a SPARQL query is read-only
 * @param query - The SPARQL query string
 * @returns Object with validation result and error message if invalid
 */
export function validateReadOnlyQuery(query: string): {
  valid: boolean;
  error?: string;
} {
  if (!query || typeof query !== 'string') {
    return { valid: false, error: 'Query must be a non-empty string' };
  }

  const trimmedQuery = query.trim();
  if (trimmedQuery.length === 0) {
    return { valid: false, error: 'Query cannot be empty' };
  }

  const upperQuery = trimmedQuery.toUpperCase();

  // Check for forbidden keywords
  for (const keyword of FORBIDDEN_KEYWORDS) {
    if (upperQuery.includes(keyword)) {
      return {
        valid: false,
        error: `Query contains forbidden keyword: ${keyword}. Only read operations are allowed.`
      };
    }
  }

  // Check if query starts with a valid query type
  const startsWithValidType = VALID_QUERY_TYPES.some(type =>
    upperQuery.replace(/\s+/g, ' ').startsWith(type) ||
    upperQuery.replace(/\s+/g, ' ').includes(`PREFIX`) && upperQuery.includes(type)
  );

  if (!startsWithValidType) {
    return {
      valid: false,
      error: `Query must be one of: ${VALID_QUERY_TYPES.join(', ')}`
    };
  }

  return { valid: true };
}

/**
 * Formats a SPARQL query with basic indentation
 * @param query - The SPARQL query string
 * @returns Formatted query string
 */
export function formatSparqlQuery(query: string): string {
  // First, protect URIs by temporarily replacing them with placeholders
  const uris: string[] = [];
  const queryWithPlaceholders = query.replace(/<[^>]+>/g, (match) => {
    uris.push(match);
    return `__URI_${uris.length - 1}__`;
  });

  // Now format the query
  let formatted = queryWithPlaceholders
    .replace(/\s+/g, ' ')
    .replace(/(PREFIX|SELECT|WHERE|OPTIONAL|FILTER|ORDER BY|GROUP BY|HAVING|LIMIT|OFFSET)/gi, '\n$1')
    .replace(/\{/g, '{\n  ')
    .replace(/\}/g, '\n}')
    .replace(/\s*\.\s*(?=\s*\?)/g, ' .\n  ') // Only break on dots before variables
    .trim()
    .split('\n')
    .map(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith('}')) return trimmed;
      if (trimmed.includes('{')) return trimmed;
      if (trimmed.match(/^(PREFIX|SELECT|WHERE|OPTIONAL|FILTER|ORDER BY|GROUP BY|HAVING|LIMIT|OFFSET)/i)) {
        return trimmed;
      }
      return '  ' + trimmed;
    })
    .join('\n');

  // Restore URIs
  uris.forEach((uri, index) => {
    formatted = formatted.replace(`__URI_${index}__`, uri);
  });

  return formatted;
}

/**
 * Extracts the LIMIT value from a SPARQL query
 * @param query - The SPARQL query string
 * @returns The LIMIT value or null if not found
 */
export function extractLimit(query: string): number | null {
  const limitMatch = query.match(/LIMIT\s+(\d+)/i);
  return limitMatch ? parseInt(limitMatch[1], 10) : null;
}

/**
 * Checks if a query has a LIMIT clause
 * @param query - The SPARQL query string
 * @returns True if query has LIMIT clause
 */
export function hasLimit(query: string): boolean {
  return /LIMIT\s+\d+/i.test(query);
}
