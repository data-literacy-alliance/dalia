'use client';
import React from 'react';
import { useRouter } from 'nextjs-toploader/app';
import { Loader2Icon } from 'lucide-react';
import { useUserPerson } from '@/lib/api/person';
import PreferencesForm from '@/app/(with-sidebar)/profile/preferences/form';

export default function ProfilePreferencesPage() {
  const { person, isLoading, error } = useUserPerson();

  const router = useRouter();

  if (error) {
    router.replace('/profile');
    return null;
  }

  // get user
  return isLoading ? (
    <Loader2Icon className={'animate-spin'} />
  ) : (
    person && <PreferencesForm person={person} />
  );
}
