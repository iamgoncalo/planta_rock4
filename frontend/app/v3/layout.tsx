import type { Metadata } from 'next';
import { DM_Mono } from 'next/font/google';
import { LiveProviderV3 } from '@/components/v3/LiveContextV3';
import TopBarV3Wrapper from '@/components/v3/TopBarV3Wrapper';
import SearchBarV3 from '@/components/v3/SearchBarV3';
import './v3.css';

const dmMono = DM_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--v3-font-dm-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'PlantaOS v3 · Rock in Rio Lisboa 2026',
  description: 'Inteligência de fluxos em tempo real · Parque Tejo · Junho 2026',
};

export default function V3Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${dmMono.variable} v3-root`}>
      <LiveProviderV3>
        <TopBarV3Wrapper />
        <main className="v3-content">{children}</main>
        <SearchBarV3 />
      </LiveProviderV3>
    </div>
  );
}
