import type { Metadata } from 'next';
import { Cormorant_Garamond, DM_Sans, DM_Mono } from 'next/font/google';
import TopBar from '@/components/v2/TopBar';
import LiveTerminal from '@/components/v2/LiveTerminal';
import './v2.css';

const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-serif',
  display: 'swap',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-ui',
  display: 'swap',
});

const dmMono = DM_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'PlantaOS · Rock in Rio Lisboa 2026',
  description:
    'Inteligência de fluxos em tempo real — 8 clusters WC, 1 137 lugares, Parque Tejo, 20–28 Junho 2026.',
};

export default function V2Layout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`${cormorant.variable} ${dmSans.variable} ${dmMono.variable} v2-root`}
    >
      <TopBar />
      <main className="v2-content">{children}</main>
      <LiveTerminal />
    </div>
  );
}
