import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'DALIA - Privacy Policy',
};

export default async function PrivacyPolicyPage() {
  redirect('/en/privacy-policy');
}
