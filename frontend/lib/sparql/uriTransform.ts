/**
 * Transforms DALIA URIs from internal RDF URIs to public web URLs
 *
 * @param uri - The URI to transform (e.g., https://id.dalia.education/learning-resource/UUID)
 * @returns The transformed URL (e.g., https://search.dalia.education/items/UUID)
 */
export function transformDaliaUri(uri: string): string {
  // Check if this is a DALIA learning resource URI
  if (uri.includes('id.dalia.education/learning-resource/')) {
    // Extract the UUID from the URI
    const uuidMatch = uri.match(/learning-resource\/([a-f0-9-]+)/);
    if (uuidMatch && uuidMatch[1]) {
      return `https://search.dalia.education/items/${uuidMatch[1]}`;
    }
  }

  // Return original URI if it doesn't match the pattern
  return uri;
}

/**
 * Extracts a display name from a URI
 *
 * @param uri - The URI to extract from
 * @returns A human-readable display name
 */
export function getUriDisplayName(uri: string): string {
  // For DALIA URIs, try to extract the UUID
  const uuidMatch = uri.match(/([a-f0-9-]+)$/);
  if (uuidMatch) {
    return uuidMatch[1];
  }

  // Fall back to the last segment of the URI
  const segments = uri.split('/');
  return segments[segments.length - 1] || uri;
}
