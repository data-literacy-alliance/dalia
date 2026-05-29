import React from 'react';
import type { Metadata } from 'next';
import Button from '@/components/Button';
import ReactMarkdown from 'react-markdown';

export const metadata: Metadata = {
  title: 'Impressum',
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

export default async function ImprintDePage() {
  const content = (await fetchPageContent('imprint', 'de'))
    ?? '_Deutsche Version noch nicht verfügbar. Bitte lesen Sie die [englische Version](/en/imprint)._';

  return (
    <div className={'mx-auto w-full max-w-screen-lg text-left'}>
      <div className={'flex gap-2 mb-5'}>
        <Button small link={{ href: '/en/imprint' }}>
          English
        </Button>
        <Button small disabled>
          German
        </Button>
      </div>
      <div className={'prose prose-sm max-w-none'}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
