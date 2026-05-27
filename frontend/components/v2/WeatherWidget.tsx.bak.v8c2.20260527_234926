'use client';

import { useEffect, useState } from 'react';
import { api, type WeatherNow } from '@/lib/v2-api';

const REFRESH_MS = 10 * 60 * 1000; // 10 min — alinhado com cache do backend

function iconFor(code: number): string {
  if (code === 0 || code === 1) return '☀';
  if (code === 2) return '⛅';
  if (code === 3) return '☁';
  if (code >= 45 && code <= 48) return '🌫';
  if (code >= 51 && code <= 67) return '🌧';
  if (code >= 71 && code <= 77) return '❄';
  if (code >= 80 && code <= 82) return '🌦';
  if (code >= 95) return '⛈';
  return '·';
}

export default function WeatherWidget() {
  const [w, setW] = useState<WeatherNow | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.weatherNow();
        setW(data);
      } catch {
        // silencioso — meteo é nice-to-have
      }
    };
    fetch();
    const iv = setInterval(fetch, REFRESH_MS);
    return () => clearInterval(iv);
  }, []);

  if (!w) return null;

  return (
    <span
      title={`${w.weather_label} · vento ${w.wind_kmh.toFixed(0)} km/h · humidade ${w.humidity_pct.toFixed(0)}% · ${w.location}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 12,
        color: 'var(--color-muted)',
        padding: '4px 10px',
        background: 'var(--color-surface, #FAFAF7)',
        border: '1px solid var(--color-border)',
        borderRadius: 999,
      }}
    >
      <span style={{ fontSize: 14 }}>{iconFor(w.weather_code)}</span>
      <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
        {w.temperature_c.toFixed(0)}°C
      </span>
      <span style={{ fontSize: 10, opacity: 0.7 }}>{w.weather_label}</span>
    </span>
  );
}
