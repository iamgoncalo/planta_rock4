import type { Metadata } from 'next';
import './wc.css';

export const metadata: Metadata = {
  title: 'PlantaOS · Casas de Banho',
};

export default function WcLayout({ children }: { children: React.ReactNode }) {
  return children;
}
