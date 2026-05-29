import React from 'react';
import type { Metadata } from 'next';
import Button from '@/components/Button';
import ReactMarkdown from 'react-markdown';

export const metadata: Metadata = {
  title: 'Terms of Use',
};

async function fetchPageContent(slug: string, lang: string): Promise<string | null> {
  const origin = process.env.BACKEND_URL
    ? new URL(process.env.BACKEND_URL).origin
    : 'http://web:8000';
  try {
    const res = await fetch(`${origin}/api/v1/pages/${slug}/${lang}/`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = (await res.json()) as { content_md?: string };
    return data.content_md ?? null;
  } catch {
    return null;
  }
}

export default async function TermsEnPage() {
  const content = (await fetchPageContent('terms', 'en'))
    ?? '_English version not yet available. Please refer to the [German version](/de/terms)._';

  return (
    <div className={'mx-auto w-full max-w-screen-lg text-left'}>
      <div className={'flex gap-2 mb-5'}>
        <Button small disabled>
          English
        </Button>
        <Button small link={{ href: '/de/terms' }}>
          German
        </Button>
      </div>
      <div className={'prose prose-sm max-w-none'}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
