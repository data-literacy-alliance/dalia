import React from 'react';
import PublicProfileBody from '@/app/(with-topbar)/profiles/[uuid]/_parts/PublicProfileBody';
import { notFound } from 'next/navigation';

export default async function Page({ params }: Props) {
  const uuid = params.uuid;

  if (!uuid) {
    notFound();
  }

  return (
    <div className="flex min-h-[40rem] flex-1 flex-col items-center justify-center p-6">
      <PublicProfileBody uuid={uuid} />
    </div>
  );
}

type Props = {
  params: { uuid: string };
};
