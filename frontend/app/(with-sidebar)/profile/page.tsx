import { redirect } from 'next/navigation';

export default async function ProfilePage() {
  return redirect('/profile/contributions');
}
