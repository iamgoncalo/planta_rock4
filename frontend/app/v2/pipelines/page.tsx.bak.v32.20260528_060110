'use client';

import { useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface PipelineNode {
  id: string;
  label: string;
  role: 'ingestion' | 'processing' | 'output' | 'ai';
  status: 'live' | 'pre_install' | 'idle' | 'error';
  rate_per_minute: number;
  last_event_iso: string | null;
  details: Record<string, unknown>;
}

interface PipelinesOverview {
  nodes: PipelineNode[];
  generated_at: string;
  hardware_install_date: string;
}

const ROLE_META: Record<string, { color: string; icon: string; label: string; x: number }> = {
  ingestion:  { color: '#1B5A8B', icon: '📡', label: 'INGESTÃO',    x: 0.10 },
  processing: { color: '#4A7C59', icon: '⚙',  label: 'PROCESSAMENTO', x: 0.37 },
  output:     { color: '#7A4A8E', icon: '📤', label: 'SAÍDA',         x: 0.65 },
  ai:         { color: '#A85D00', icon: '✦',  label: 'IA',            x: 0.92 },
};

const STATUS_META: Record<string, { bg: string; ink: string; label: string }> = {
  live:        { bg: '#E8F1EA', ink: '#1B3A21', label: 'LIVE' },
  pre_install: { bg: '#FFF2E0', ink: '#7A5A00', label: 'PRÉ-INSTALAÇÃO' },
  idle:        { bg: '#F0F0F0', ink: '#6B7280', label: 'INACTIVO' },
  error:       { bg: '#F8D9C4', ink: '#8B3D0A', label: 'ERRO' },
};

interface Particle {
  fromX: number;
  toX: number;
  y: number;
  progress: number;
  speed: number;
  color: string;
}

export default function PipelinesPage() {
  const [data, setData] = useState<PipelinesOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number | null>(null);

  // Fetch overview a cada 5s
  useEffect(() => {
    let mounted = true;
    const fetchAll = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/pipelines/overview`);
        const j = await r.json() as PipelinesOverview;
        if (mounted) {
          setData(j);
          setError(null);
        }
      } catch (e) {
        if (mounted) setError(e instanceof Error ? e.message : 'erro');
      }
    };
    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  // Particle generation — sempre que data muda, gerar partículas baseadas em rate
  useEffect(() => {
    if (!data) return;
    const interval = setInterval(() => {
      const c = canvasRef.current;
      if (!c) return;
      const w = c.width;
      data.nodes.forEach((node, idx) => {
        if (node.status !== 'live') return;
        // Próximo nó (se este for ingestion → processing → output)
        const order: PipelineNode['role'][] = ['ingestion', 'processing', 'output'];
        const myIdx = order.indexOf(node.role);
        if (myIdx === -1 || myIdx === order.length - 1) return;
        const nextRole = order[myIdx + 1];
        const fromX = (ROLE_META[node.role]?.x || 0) * w;
        const toX = (ROLE_META[nextRole]?.x || 0) * w;
        // Quantas partículas? proporcional à rate
        const count = Math.min(3, Math.ceil(node.rate_per_minute / 30));
        for (let i = 0; i < count; i++) {
          particlesRef.current.push({
            fromX,
            toX,
            y: 80 + Math.random() * 30,
            progress: 0,
            speed: 0.008 + Math.random() * 0.005,
            color: ROLE_META[node.role]?.color || '#4A7C59',
          });
        }
      });
    }, 800);
    return () => clearInterval(interval);
  }, [data]);

  // Canvas animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      const w = canvas.width / (window.devicePixelRatio || 1);
      const h = canvas.height / (window.devicePixelRatio || 1);
      ctx.clearRect(0, 0, w, h);

      // Linhas guia entre nós
      ctx.strokeStyle = 'rgba(0,0,0,0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0.10 * w, 95);
      ctx.lineTo(0.92 * w, 95);
      ctx.stroke();

      // Partículas
      particlesRef.current = particlesRef.current.filter(p => p.progress < 1);
      particlesRef.current.forEach(p => {
        p.progress += p.speed;
        const x = p.fromX + (p.toX - p.fromX) * p.progress;
        const alpha = p.progress < 0.5
          ? p.progress * 2
          : (1 - p.progress) * 2;
        ctx.fillStyle = p.color;
        ctx.globalAlpha = Math.min(1, alpha);
        ctx.beginPath();
        ctx.arc(x, p.y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      animationRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  return (
    <div style={{ padding: '32px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 18 }}>
        <div className="section-label">Sistema · Pipelines · Fluxo de dados</div>
        <h1 className="serif" style={{
          fontSize: 'clamp(26px, 4vw, 40px)',
          fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.1, marginBottom: 6,
        }}>
          Fluxo de dados
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13, lineHeight: 1.55 }}>
          De onde os dados vêm, como são processados, para onde vão · animação em tempo real
        </p>
      </div>

      {error && (
        <div style={{ padding: 10, marginBottom: 12, background: '#FDECDC', color: '#8B3D0A', borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* CANVAS — animação de partículas */}
      <div style={{
        position: 'relative',
        background: 'white',
        border: '1px solid var(--color-border)',
        borderRadius: 12,
        padding: 24,
        marginBottom: 20,
        minHeight: 200,
      }}>
        <canvas ref={canvasRef} style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'relative',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
          alignItems: 'center',
        }}>
          {(['ingestion', 'processing', 'output', 'ai'] as const).map(role => {
            const node = data?.nodes.find(n => n.role === role);
            const meta = ROLE_META[role];
            return (
              <div key={role} style={{
                background: 'white',
                border: `2px solid ${node?.status === 'live' ? meta.color : 'var(--color-border)'}`,
                borderRadius: 10,
                padding: 14,
                textAlign: 'center',
                opacity: node?.status === 'pre_install' ? 0.55 : 1,
                position: 'relative',
                zIndex: 2,
              }}>
                <div style={{ fontSize: 28, marginBottom: 4 }}>{meta.icon}</div>
                <div className="mono" style={{
                  fontSize: 9, letterSpacing: '0.12em',
                  textTransform: 'uppercase', color: meta.color, fontWeight: 700, marginBottom: 2,
                }}>{meta.label}</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-ink)' }}>
                  {node?.label || '—'}
                </div>
                {node && (
                  <div style={{
                    marginTop: 8,
                    fontSize: 11, color: 'var(--color-muted)',
                    paddingTop: 6, borderTop: '1px dashed var(--color-border)',
                  }}>
                    {node.rate_per_minute > 0
                      ? <><strong style={{ color: 'var(--color-ink)' }}>{node.rate_per_minute.toFixed(1)}</strong> ev/min</>
                      : <span className="mono">—</span>
                    }
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* CARDS detalhados */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 14,
      }}>
        {data?.nodes.map(node => {
          const role = ROLE_META[node.role] || ROLE_META.processing;
          const status = STATUS_META[node.status] || STATUS_META.idle;
          return (
            <div key={node.id} style={{
              background: 'white',
              border: '1px solid var(--color-border)',
              borderTop: `3px solid ${role.color}`,
              borderRadius: 10,
              padding: 16,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div className="mono" style={{ fontSize: 9, color: role.color, letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 700 }}>
                    {role.icon} {role.label}
                  </div>
                  <div className="serif" style={{ fontSize: 16, fontWeight: 500, color: 'var(--color-ink)', marginTop: 2 }}>
                    {node.label}
                  </div>
                </div>
                <span style={{
                  background: status.bg, color: status.ink,
                  padding: '3px 8px', borderRadius: 999,
                  fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                }}>{status.label}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, paddingTop: 6, borderTop: '1px dashed var(--color-border)' }}>
                <span className="serif" style={{ fontSize: 22, fontWeight: 600, color: 'var(--color-ink)' }}>
                  {node.rate_per_minute > 0 ? node.rate_per_minute.toFixed(1) : '—'}
                </span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--color-muted)' }}>eventos/min</span>
              </div>
              {node.details && (
                <div style={{
                  background: '#FAFAF7', borderRadius: 6,
                  padding: 8, fontSize: 10, color: 'var(--color-muted)',
                  marginTop: 8, maxHeight: 100, overflow: 'auto',
                }}>
                  {Object.entries(node.details).slice(0, 6).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 1 }}>
                      <span className="mono" style={{ color: 'var(--color-ink)' }}>{k}:</span>{' '}
                      {typeof v === 'object' ? JSON.stringify(v).slice(0, 60) : String(v)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
