/**
 * Client-side utility to get CSRF token from cookies
 */
export function getCsrfTokenClient(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const name = 'csrftoken';
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);

  if (parts.length === 2) {
    const token = parts.pop()?.split(';').shift();
    return token || null;
  }

  return null;
}
