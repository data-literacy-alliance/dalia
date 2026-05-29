import React from 'react';
import { notFound } from 'next/navigation';
import PreviewDetailsBody from '@/app/(with-sidebar)/items/new/_parts/PreviewDetailsBody';

export default function PreviewPage({ searchParams }: PreviewPageProps) {
  const { item } = searchParams;

  if (!item) {
    notFound();
  }

  return <PreviewDetailsBody tempItemId={item} />;
}

export type PreviewPageProps = {
  searchParams: {
    item: string;
  };
};
