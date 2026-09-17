import { auth } from '@/auth';
import { Studio } from '@/components/studio';
export const dynamic = 'force-dynamic';
export default async function Home() {
  const authEnabled = Boolean(process.env.AUTH_GITHUB_ID && process.env.AUTH_GITHUB_SECRET);
  const session = authEnabled ? await auth() : null;
  return <Studio authEnabled={authEnabled} signedIn={Boolean(session?.user)} userName={session?.user?.name ?? ''} />;
}
