'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  api,
  type IncidentEntry,
  type IncidentSeverity,
  type IncidentCategory,
} from '@/lib/v2-api';

const REFRESH_MS = 20_000;

const SEVERITY_COLORS: Record<IncidentSeverity, { bg: string; ink: string }> = {
  info: { bg: '#E8F1EA', ink: '#1B3A21' },
  warning: { bg: '#FFF7E0', ink: '#7A5A00' },
  critical: { bg: '#F8D9C4', ink: '#C25A1A' },
};

const SEVERITY_LABEL: Record<IncidentSeverity, string> = {
  info: 'Info',
  warning: 'Aviso',
  critical: 'Crítico',
};

const CATEGORY_LABEL: Record<IncidentCategory, string> = {
  medical: 'Médico',
  crowd: 'Multidão',
  safety: 'Segurança',
  hygiene: 'Higiene',
  technical: 'Técnico',
  other: 'Outro',
};

const CLUSTERS = ['WC-01', 'WC-02', 'WC-03', 'WC-04', 'WC-05', 'WC-06', 'WC-07', 'WC-08'];

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentEntry[]>([]);
  const [open_count, setOpenCount] = useState(0);
  const [critical_count, setCriticalCount] = useState(0);
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterOpenOnly, setFilterOpenOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resolving, setResolving] = useState<number | null>(null);

  const [form, setForm] = useState<{
    cluster_id: string;
    severity: IncidentSeverity;
    category: IncidentCategory;
    note: string;
    reported_by: string;
  }>({
    cluster_id: 'WC-01',
    severity: 'warning',
    category: 'hygiene',
    note: '',
    reported_by: '',
  });

  const fetchList = async () => {
    try {
      const data = await api.incidentsList({
        severity: filterSeverity || undefined,
        open_only: filterOpenOnly,
        limit: 100,
      });
      setIncidents(data.incidents);
      setOpenCount(data.open_count);
      setCriticalCount(data.critical_count);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'erro');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
    const iv = setInterval(fetchList, REFRESH_MS);
    return () => clearInterval(iv);
  }, [filterSeverity, filterOpenOnly]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.note.trim()) return;
    setSubmitting(true);
    try {
      await api.incidentCreate({
        cluster_id: form.cluster_id || null,
        severity: form.severity,
        category: form.category,
        note: form.note,
        reported_by: form.reported_by || null,
      });
      setForm({
        cluster_id: 'WC-01',
        severity: 'warning',
        category: 'hygiene',
        note: '',
        reported_by: '',
      });
      setShowForm(false);
      await fetchList();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'erro');
    } finally {
      setSubmitting(false);
    }
  };

  const resolve = async (id: number) => {
    setResolving(id);
    try {
      await api.incidentResolve(id, {
        resolved_by: 'Operações',
        resolution_note: null,
      });
      await fetchList();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'erro');
    } finally {
      setResolving(null);
    }
  };

  return (
    <div style={{ padding: '40px 32px 48px', maxWidth: 1280, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <div className="section-label">Operações · registo de incidentes</div>
        <h1
          className="serif"
          style={{
            fontSize: 'clamp(28px, 4vw, 44px)',
            fontWeight: 500,
            color: 'var(--color-ink)',
            lineHeight: 1.1,
            marginBottom: 8,
          }}
        >
          Incidentes
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 14, lineHeight: 1.6 }}>
          Registo de tudo o que acontece no terreno · 6 categorias · 3 níveis de severidade
        </p>
      </div>

      {/* KPIs + acções */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr)) auto',
          gap: 12,
          marginBottom: 24,
          alignItems: 'stretch',
        }}
      >
        <Kpi label="Total" value={incidents.length} color="#1A1A1A" />
        <Kpi label="Abertos" value={open_count} color="#A85D00" />
        <Kpi label="Críticos" value={critical_count} color="#C25A1A" />
        <button
          onClick={() => setShowForm((v) => !v)}
          style={{
            background: showForm ? 'var(--color-border)' : 'var(--color-success, #1B3A21)',
            color: showForm ? 'var(--color-muted)' : 'white',
            border: 'none',
            borderRadius: 10,
            padding: '0 24px',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {showForm ? 'Cancelar' : '+ Reportar'}
        </button>
      </div>

      {/* Formulário */}
      {showForm && (
        <form
          onSubmit={submit}
          style={{
            background: 'var(--card, white)',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
            padding: 20,
            marginBottom: 24,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 12,
          }}
        >
          <Field label="Cluster">
            <select
              value={form.cluster_id}
              onChange={(e) => setForm({ ...form, cluster_id: e.target.value })}
              style={inputStyle}
            >
              {CLUSTERS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Severidade">
            <select
              value={form.severity}
              onChange={(e) =>
                setForm({ ...form, severity: e.target.value as IncidentSeverity })
              }
              style={inputStyle}
            >
              {(['info', 'warning', 'critical'] as IncidentSeverity[]).map((s) => (
                <option key={s} value={s}>
                  {SEVERITY_LABEL[s]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Categoria">
            <select
              value={form.category}
              onChange={(e) =>
                setForm({ ...form, category: e.target.value as IncidentCategory })
              }
              style={inputStyle}
            >
              {(Object.keys(CATEGORY_LABEL) as IncidentCategory[]).map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABEL[c]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quem reporta">
            <input
              type="text"
              value={form.reported_by}
              onChange={(e) => setForm({ ...form, reported_by: e.target.value })}
              placeholder="nome / função"
              style={inputStyle}
            />
          </Field>
          <Field label="Descrição" full>
            <textarea
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
              rows={2}
              required
              placeholder="O que aconteceu, onde, quando…"
              style={{ ...inputStyle, fontFamily: 'inherit', resize: 'vertical' }}
            />
          </Field>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="submit"
              disabled={submitting || !form.note.trim()}
              style={{
                background: 'var(--color-success, #1B3A21)',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                padding: '10px 24px',
                fontSize: 13,
                fontWeight: 600,
                cursor: submitting ? 'wait' : 'pointer',
                opacity: submitting || !form.note.trim() ? 0.5 : 1,
              }}
            >
              {submitting ? 'A registar…' : 'Registar incidente'}
            </button>
          </div>
        </form>
      )}

      {/* Filtros */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>Filtros:</span>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          style={{ ...inputStyle, width: 'auto' }}
        >
          <option value="">Toda a severidade</option>
          <option value="critical">Apenas críticos</option>
          <option value="warning">Apenas avisos</option>
          <option value="info">Apenas info</option>
        </select>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input
            type="checkbox"
            checked={filterOpenOnly}
            onChange={(e) => setFilterOpenOnly(e.target.checked)}
          />
          só abertos
        </label>
      </div>

      {error && (
        <div
          style={{
            padding: 12,
            background: '#FDECDC',
            color: '#C25A1A',
            borderRadius: 8,
            marginBottom: 16,
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {/* Lista */}
      {loading && incidents.length === 0 && (
        <div style={{ color: 'var(--color-muted)', padding: 24 }}>A carregar…</div>
      )}

      {!loading && incidents.length === 0 && (
        <div
          style={{
            padding: 32,
            textAlign: 'center',
            color: 'var(--color-muted)',
            background: 'var(--card, white)',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
          }}
        >
          Sem incidentes registados.
        </div>
      )}

      <div style={{ display: 'grid', gap: 10 }}>
        {incidents.map((i) => {
          const sev = SEVERITY_COLORS[i.severity];
          return (
            <div
              key={i.id}
              style={{
                background: 'var(--card, white)',
                border: '1px solid var(--color-border)',
                borderLeft: `4px solid ${sev.ink}`,
                borderRadius: 10,
                padding: 16,
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                gap: 12,
                opacity: i.resolved ? 0.55 : 1,
              }}
            >
              <div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                  <span
                    style={{
                      background: sev.bg,
                      color: sev.ink,
                      padding: '2px 8px',
                      borderRadius: 999,
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                    }}
                  >
                    {SEVERITY_LABEL[i.severity]}
                  </span>
                  <span
                    className="mono"
                    style={{ fontSize: 11, color: 'var(--color-muted)' }}
                  >
                    {i.cluster_id || '—'} · {CATEGORY_LABEL[i.category]}
                  </span>
                  {i.resolved && (
                    <span
                      style={{
                        fontSize: 10,
                        color: '#1B3A21',
                        background: '#E8F1EA',
                        padding: '2px 8px',
                        borderRadius: 999,
                        fontWeight: 600,
                      }}
                    >
                      RESOLVIDO
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 14, color: 'var(--color-ink)', lineHeight: 1.5 }}>
                  {i.note}
                </div>
                <div
                  className="mono"
                  style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 6 }}
                >
                  {new Date(i.occurred_at).toLocaleString('pt-PT', {
                    day: '2-digit',
                    month: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  {i.reported_by ? ` · ${i.reported_by}` : ''}
                </div>
              </div>
              {!i.resolved && (
                <button
                  onClick={() => resolve(i.id)}
                  disabled={resolving === i.id}
                  style={{
                    background: 'transparent',
                    color: 'var(--color-success, #1B3A21)',
                    border: '1px solid var(--color-success, #1B3A21)',
                    borderRadius: 8,
                    padding: '6px 14px',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    alignSelf: 'flex-start',
                  }}
                >
                  {resolving === i.id ? '…' : 'Resolver'}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  fontSize: 13,
  border: '1px solid var(--color-border)',
  borderRadius: 6,
  background: 'white',
  color: 'var(--color-ink)',
};

function Field({
  label,
  children,
  full,
}: {
  label: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <div style={{ gridColumn: full ? '1 / -1' : undefined }}>
      <label
        style={{
          display: 'block',
          fontSize: 11,
          color: 'var(--color-muted)',
          marginBottom: 4,
          fontWeight: 500,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

function Kpi({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div
      style={{
        background: 'var(--card, white)',
        border: '1px solid var(--color-border)',
        borderRadius: 10,
        padding: 14,
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: 'var(--color-muted)',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div className="serif" style={{ fontSize: 26, fontWeight: 500, color, lineHeight: 1 }}>
        {value}
      </div>
    </div>
  );
}
