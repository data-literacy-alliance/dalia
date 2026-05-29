import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'DALIA - Imprint',
};

export default async function ImprintPage() {
  redirect('/en/imprint');
}
