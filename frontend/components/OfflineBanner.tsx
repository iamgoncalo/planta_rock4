'use client';

interface OfflineBannerProps {
  isOffline: boolean;
}

export default function OfflineBanner({ isOffline }: OfflineBannerProps) {
  if (!isOffline) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        backgroundColor: '#C25A1A',
        color: '#fff',
        width: '100%',
        padding: '14px 20px',
        textAlign: 'center',
        fontFamily: 'var(--font-ui)',
        fontWeight: 600,
        fontSize: '18px',
        lineHeight: '1.4',
        letterSpacing: '0.01em',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      Sem dados ao vivo — sistema offline
    </div>
  );
}
