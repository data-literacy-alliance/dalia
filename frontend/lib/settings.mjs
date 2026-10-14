//export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH;
//export const BACKEND_URL = process.env.BACKEND_URL;
// try to remove trailing slash
//export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH?.replace(/\/$/, '') ?? '';
//export const BACKEND_URL = process.env.BACKEND_URL?.replace(/\/$/, '') ?? '';

//Regular expressions should be avoided as much as possible
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH?.endsWith('/')
  ? process.env.NEXT_PUBLIC_BASE_PATH.slice(0, -1)
  : (process.env.NEXT_PUBLIC_BASE_PATH ?? '');
export const BACKEND_URL = process.env.BACKEND_URL?.endsWith('/')
  ? process.env.BACKEND_URL.slice(0, -1)
  : (process.env.BACKEND_URL ?? '');

export const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL?.endsWith(
  '/'
)
  ? process.env.NEXT_PUBLIC_API_URL.slice(0, -1)
  : (process.env.NEXT_PUBLIC_API_URL ?? '');

// Empty string: all client-side API calls use relative URLs (same-origin).
// nginx routes /api/... to Django regardless of the public hostname.
export const NEXT_PUBLIC_BACKEND_ROOT = '';

export const NEXT_PUBLIC_DALIA_NEWSLETTER_SUBSCRIBE_LINK =
  process.env.NEXT_PUBLIC_DALIA_NEWSLETTER_SUBSCRIBE_LINK?.endsWith('/')
    ? process.env.NEXT_PUBLIC_DALIA_NEWSLETTER_SUBSCRIBE_LINK.slice(0, -1)
    : (process.env.NEXT_PUBLIC_DALIA_NEWSLETTER_SUBSCRIBE_LINK ?? '');

export const NEXT_PUBLIC_DALIA_NEWSLETTER_LINK =
  process.env.NEXT_PUBLIC_DALIA_NEWSLETTER_LINK?.endsWith('/')
    ? process.env.NEXT_PUBLIC_DALIA_NEWSLETTER_LINK.slice(0, -1)
    : (process.env.NEXT_PUBLIC_DALIA_NEWSLETTER_LINK ?? '');

export const ResultsPageSize = 20;

export const PrototypeCookieName = '__openByDefault';
export const GDPRCookieName = 'gdpr_cookie_accepted';

export const FeedbackFormEndpoint =
  process.env.NEXT_PUBLIC_FEEDBACK_WEBHOOK_URL || '';

export const SupportingCommunityRelationId = 20;
export const LoginURL = '/accounts/login/';
export const DaliaDeletionRequestEmail = 'account@dalia.education';
