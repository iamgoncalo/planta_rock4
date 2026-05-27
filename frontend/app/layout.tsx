import type { Metadata } from 'next';
import './globals.css';
import BottomNav from '../components/BottomNav';

export const metadata: Metadata = {
  title: 'PlantaOS — Rock in Rio Lisboa 2026',
  description: 'Gestão em tempo real de WC — Parque Tejo, Lisboa',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body style={{ paddingBottom: 'var(--nav-h)' }}>
        {children}
        <BottomNav />
      </body>
    </html>
  );
}
