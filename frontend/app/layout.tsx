import type { Metadata, Viewport } from 'next';
import './globals.css';
import BottomNav from '../components/BottomNav';

export const viewport: Viewport = {
  themeColor: '#ffffff',
  width: 'device-width',
  initialScale: 1,
};

export const metadata: Metadata = {
  title: 'PlantaOS — Rock in Rio Lisboa 2026',
  description: 'Gestão em tempo real de WC — Parque Tejo, Lisboa',
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
    ],
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
  openGraph: {
    title: 'PlantaOS — Rock in Rio Lisboa 2026',
    description: 'Gestão em tempo real de WC — Parque Tejo, Lisboa',
    type: 'website',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'PlantaOS',
  },
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
