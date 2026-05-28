import type { Metadata } from 'next';
import { Cormorant_Garamond, DM_Sans, DM_Mono } from 'next/font/google';
import TopBar from '@/components/v2/TopBar';
import PlantaSearchBar from '@/components/v2/PlantaSearchBar';
import { LiveProvider } from '@/components/v2/LiveContext';
import './v2.css';

// Mantemos as fontes carregadas (DM_Mono ainda é usada como --font-dm-mono)
// mas a tipografia visível é Inter (carregada via @import em v2.css).
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
  variable: '--font-dm-mono',
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
      <LiveProvider>
        <TopBar />
        <main className="v2-content">
          {children}
          <PlantaSearchBar />
        </main>
      </LiveProvider>
    </div>
  );
}
