import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'Proof of Work | Resume Studio',
  description: 'Source-linked skill coverage, conservative improvements and text-verified PDF export.',
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
