'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

const CLUSTERS = ['WC-01','WC-02','WC-03','WC-04','WC-05','WC-06','WC-07','WC-08'];

interface ClusterStatus {
  data_source: string;
  age_s: number | null;
  ts_device: number | null;
}

interface IngestStatus {
  data_ttl_s: number;
  clusters: Record<string, ClusterStatus>;
}

function SourceDot({ online }: { online: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: online ? '#22C55E' : 'var(--v3-line-strong)',
        flexShrink: 0,
        ...(online ? { animation: 'v3-dot-pulse 2s ease-in-out infinite' } : {}),
      }}
    />
  );
}

export default function InstallPage() {
  const [status, setStatus] = useState<IngestStatus | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/ingest/status`, { cache: 'no-store' });
        if (r.ok) setStatus(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const ttl = status?.data_ttl_s ?? 90;

  return (
    <div className="v3-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
        <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Estado de ingestão · 8 clusters
        </div>
        <span className="v3-badge v3-badge-muted">TTL {ttl}s</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
        {CLUSTERS.map((cid) => {
          const key = cid.toLowerCase().replace('-', '-');
          const cl: ClusterStatus = status?.clusters[key] ?? { data_source: 'none', age_s: null, ts_device: null };
          const online = cl.data_source !== 'none' && cl.data_source !== 'offline' && cl.age_s != null && cl.age_s < ttl;
          const ageLabel = cl.age_s != null ? `${cl.age_s.toFixed(0)}s atrás` : '—';

          return (
            <div key={cid} className="v3-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--v3-font-mono)', fontWeight: 600, fontSize: 13 }}>{cid}</span>
                <SourceDot online={online} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 11.5, color: 'var(--v3-muted)' }}>Fonte</span>
                  <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 11.5, color: cl.data_source === 'none' ? 'var(--v3-faint)' : 'var(--v3-ink)', fontWeight: 500 }}>
                    {cl.data_source === 'none' ? 'sem dados' : cl.data_source}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 11.5, color: 'var(--v3-muted)' }}>Última recepção</span>
                  <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 11.5, color: online ? 'var(--v3-ink)' : 'var(--v3-faint)' }}>
                    {ageLabel}
                  </span>
                </div>
              </div>

              <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--v3-line)' }}>
                <span className={`v3-badge ${online ? 'v3-badge-blue' : 'v3-badge-muted'}`}>
                  {online ? 'ONLINE' : 'SEM SINAL'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 24, padding: '14px 16px', background: 'var(--v3-bg-soft)', borderRadius: 'var(--v3-r)', border: '1px solid var(--v3-line)' }}>
        <p style={{ margin: 0, fontSize: 12, color: 'var(--v3-muted)', lineHeight: 1.6 }}>
          Para detalhe completo de instalação (firmware .ino, GPIO, etiquetas), acede a{' '}
          <a href="/v2/install" style={{ color: 'var(--v3-blue)', textDecoration: 'underline' }}>/v2/install</a>.
        </p>
      </div>
    </div>
  );
}
