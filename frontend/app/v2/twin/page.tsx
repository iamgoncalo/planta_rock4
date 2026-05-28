'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useLive, type LiveSnapshot } from '@/components/v2/LiveContext';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const VB = 1000;
const PAD = 0.1 * VB;

/* ════════════════════════════════════════════════════════════════════
   FONTE DE VERDADE (/api/v1/clusters/geo) + fallback idêntico
   ════════════════════════════════════════════════════════════════════ */

interface GeoCluster {
  id: string; e_m: number; n_m: number; gps_lat: number; gps_lon: number;
  type: 'MF' | 'UNI'; unisex: boolean; desc: string;
  cap_m: number | null; cap_f: number | null; cap: number | null; capacity_total: number;
}
interface GeoLandmark { id: string; label: string; e_m: number; n_m: number; kind: string; }
interface GeoPayload {
  anchor_gps: { lat: number; lon: number }; span_e_m: number; span_n_m: number;
  clusters: GeoCluster[]; landmarks: GeoLandmark[]; total_clusters: number;
}

const FALLBACK_GEO: GeoPayload = {
  anchor_gps: { lat: 38.78145, lon: -9.0943 }, span_e_m: 298.5, span_n_m: 327.3,
  clusters: [
    { id: 'WC-01', e_m: 215.2, n_m: 327.3, gps_lat: 38.78439, gps_lon: -9.09182, type: 'MF', unisex: false, desc: 'V34 · junto ao Parque P1', cap_m: 72, cap_f: 63, cap: null, capacity_total: 135 },
    { id: 'WC-02', e_m: 256.9, n_m: 286.1, gps_lat: 38.78402, gps_lon: -9.09134, type: 'MF', unisex: false, desc: 'V35 · feminino dominante', cap_m: 54, cap_f: 72, cap: null, capacity_total: 126 },
    { id: 'WC-03', e_m: 268.2, n_m: 194.8, gps_lat: 38.7832, gps_lon: -9.091209, type: 'MF', unisex: false, desc: 'S36 · entrada principal', cap_m: 54, cap_f: 48, cap: null, capacity_total: 102 },
    { id: 'WC-04', e_m: 298.5, n_m: 288.3, gps_lat: 38.78404, gps_lon: -9.09086, type: 'MF', unisex: false, desc: 'S37 · cota +20 m', cap_m: 84, cap_f: 66, cap: null, capacity_total: 150 },
    { id: 'WC-05', e_m: 274.2, n_m: 238.2, gps_lat: 38.78359, gps_lon: -9.09114, type: 'UNI', unisex: true, desc: 'M38 · só entrada', cap_m: null, cap_f: null, cap: 133, capacity_total: 133 },
    { id: 'WC-06', e_m: 60.7, n_m: 82.4, gps_lat: 38.78219, gps_lon: -9.093601, type: 'UNI', unisex: true, desc: 'W39/S39 · maior cluster', cap_m: null, cap_f: null, cap: 208, capacity_total: 208 },
    { id: 'WC-07', e_m: 228.2, n_m: 148.1, gps_lat: 38.78278, gps_lon: -9.09167, type: 'MF', unisex: false, desc: 'M40 · cacifos', cap_m: 84, cap_f: 54, cap: null, capacity_total: 138 },
    { id: 'WC-08', e_m: 0.0, n_m: 0.0, gps_lat: 38.78145, gps_lon: -9.0943, type: 'MF', unisex: false, desc: 'V41 · produção', cap_m: 84, cap_f: 61, cap: null, capacity_total: 145 },
  ],
  landmarks: [
    { id: 'ENTRADA', label: 'Entrada Principal', e_m: 290, n_m: 175, kind: 'entrance' },
    { id: 'PALCO_MUNDO', label: 'Palco Mundo', e_m: 70, n_m: 120, kind: 'stage' },
    { id: 'MUSIC_VALLEY', label: 'Music Valley', e_m: 30, n_m: 60, kind: 'stage' },
    { id: 'SUPER_BOCK', label: 'Super Bock', e_m: 120, n_m: 70, kind: 'stage' },
  ],
  total_clusters: 8,
};

/* Metadados fixos por cluster (nome + elemento) — sotaque editorial, sem coords */
const META: Record<string, { name: string; element: string; color: string }> = {
  'WC-01': { name: 'Aroeira', element: 'Normal', color: '#9CA590' },
  'WC-02': { name: 'Camélia', element: 'Psíquico', color: '#C25A8F' },
  'WC-03': { name: 'Olaia', element: 'Eléctrico', color: '#D4A338' },
  'WC-04': { name: 'Sobreiro', element: 'Terra', color: '#8A6308' },
  'WC-05': { name: 'Magnólia', element: 'Fogo', color: '#C25A1A' },
  'WC-06': { name: 'Glicínia', element: 'Água', color: '#5A8FB0' },
  'WC-07': { name: 'Jacarandá', element: 'Voador', color: '#8FB8CC' },
  'WC-08': { name: 'Tília', element: 'Planta', color: '#4A7C59' },
};
function meta(id: string) { return META[id.toUpperCase()] ?? { name: id, element: 'Normal', color: '#9CA590' }; }
function dexNum(id: string) { const m = id.match(/(\d+)/); return m ? '#' + m[1].padStart(3, '0') : id; }

/* ════════════════════════════════════════════════════════════════════
   MOTOR DE COORDENADAS metros→ecrã
   ════════════════════════════════════════════════════════════════════ */

function makeEngine(geo: GeoPayload) {
  const S = (VB - 2 * PAD) / Math.max(geo.span_e_m, geo.span_n_m);
  const offX = (VB - 2 * PAD - geo.span_e_m * S) / 2;
  const offY = (VB - 2 * PAD - geo.span_n_m * S) / 2;
  const x = (e: number) => PAD + offX + e * S;
  const y = (n: number) => VB - PAD - offY - n * S;
  return { S, x, y };
}
type Engine = ReturnType<typeof makeEngine>;

/* ════════════════════════════════════════════════════════════════════
   ESTADO / OCUPAÇÃO
   ════════════════════════════════════════════════════════════════════ */

type St = 'ok' | 'warn' | 'crit';
function occSt(o: number): St { return o >= 85 ? 'crit' : o >= 65 ? 'warn' : 'ok'; }
const STc: Record<St, string> = { ok: '#6FAF82', warn: '#D48B3A', crit: '#C25A1A' };
const STlabel: Record<St, string> = { ok: 'Livre', warn: 'Moderado', crit: 'Cheio' };

function occOf(snap: LiveSnapshot | null, id: string): number {
  const c = snap?.clusters?.find((x) => x.cluster_id.toLowerCase() === id.toLowerCase());
  return Math.round(c?.params?.ocupacao_instantanea ?? 0);
}
function distM(a: GeoCluster, b: GeoCluster) { return Math.hypot(a.e_m - b.e_m, a.n_m - b.n_m); }

/* ════════════════════════════════════════════════════════════════════
   VISTAS
   ════════════════════════════════════════════════════════════════════ */

interface VProps {
  geo: GeoPayload; eng: Engine; occById: Map<string, number>;
  origin: string | null; setOrigin: (id: string | null) => void;
  reco: { from: GeoCluster; to: GeoCluster } | null;
}

function field(eng: Engine, geo: GeoPayload, fill: string, edge: string, rx = 28) {
  return (
    <rect x={eng.x(0) - 34} y={eng.y(geo.span_n_m) - 34}
      width={geo.span_e_m * eng.S + 68} height={geo.span_n_m * eng.S + 68}
      rx={rx} fill={fill} stroke={edge} strokeWidth="2" />
  );
}
function scaleBar(eng: Engine) {
  const px = 100 * eng.S;
  return (
    <g transform={`translate(${PAD}, ${VB - PAD * 0.5})`}>
      <line x1="0" y1="0" x2={px} y2="0" stroke="#1B3A21" strokeWidth="3" />
      <line x1="0" y1="-5" x2="0" y2="5" stroke="#1B3A21" strokeWidth="3" />
      <line x1={px} y1="-5" x2={px} y2="5" stroke="#1B3A21" strokeWidth="3" />
      <text x={px / 2} y="-8" fontSize="13" textAnchor="middle" fontWeight="600" fill="#1B3A21">100 m</text>
    </g>
  );
}
function northArrow(eng: Engine) {
  return (
    <g transform={`translate(${VB - PAD * 0.6}, ${PAD * 0.6})`}>
      <line x1="0" y1="14" x2="0" y2="-12" stroke="#1B3A21" strokeWidth="2.5" />
      <polygon points="0,-16 -5,-7 5,-7" fill="#1B3A21" />
      <text x="0" y="28" fontSize="13" textAnchor="middle" fontWeight="700" fill="#1B3A21">N</text>
    </g>
  );
}
function landmarks(eng: Engine, geo: GeoPayload) {
  return geo.landmarks.map((l) => (
    <g key={l.id} transform={`translate(${eng.x(l.e_m)}, ${eng.y(l.n_m)})`}>
      <rect x="-46" y="-12" width="92" height="24" rx="12"
        fill={l.kind === 'entrance' ? '#1B3A21' : 'rgba(27,58,33,0.07)'}
        stroke={l.kind === 'entrance' ? 'none' : '#C9DDB6'} />
      <text x="0" y="4" fontSize="12" textAnchor="middle"
        fill={l.kind === 'entrance' ? '#fff' : '#1B3A21'} fontWeight="600">{l.label}</text>
    </g>
  ));
}
function route(eng: Engine, reco: VProps['reco']) {
  if (!reco) return null;
  return (
    <line x1={eng.x(reco.from.e_m)} y1={eng.y(reco.from.n_m)}
      x2={eng.x(reco.to.e_m)} y2={eng.y(reco.to.n_m)}
      stroke="#4A7C59" strokeWidth="4" strokeDasharray="10 8" strokeLinecap="round" className="tw-dash" />
  );
}
function youHere(eng: Engine, geo: GeoPayload, origin: string | null, r = 30) {
  if (!origin) return null;
  const c = geo.clusters.find((x) => x.id === origin);
  if (!c) return null;
  return (
    <g transform={`translate(${eng.x(c.e_m)}, ${eng.y(c.n_m)})`} className="tw-you">
      <circle r={r + 16} fill="none" stroke="#1B3A21" strokeWidth="3" />
      <rect x="-44" y={-(r + 40)} width="88" height="22" rx="11" fill="#1B3A21" />
      <text x="0" y={-(r + 25)} fontSize="11" textAnchor="middle" fill="#fff" fontWeight="700">ESTÁS AQUI</text>
    </g>
  );
}

/* 1 · Mapa */
function MapView({ geo, eng, occById, origin, setOrigin, reco }: VProps) {
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg">
      {field(eng, geo, '#F4F8EC', '#C9DDB6')}
      <rect x="0" y={VB - PAD * 0.5} width={VB} height={PAD * 0.5} fill="#BFE0E8" opacity="0.55" />
      <text x={PAD} y={VB - 12} fontSize="14" fill="#1B3A21" opacity="0.5" fontStyle="italic">Rio Tejo</text>
      {landmarks(eng, geo)}
      {route(eng, reco)}
      {geo.clusters.map((c, i) => {
        const o = occById.get(c.id) ?? 0; const st = occSt(o); const r = c.unisex ? 32 : 26;
        const isReco = reco?.to.id === c.id;
        return (
          <g key={c.id} transform={`translate(${eng.x(c.e_m)}, ${eng.y(c.n_m)})`} className="tw-node"
            style={{ ['--d' as any]: `${i * 60}ms`, cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            {isReco && <circle r={r + 10} fill="none" stroke="#4A7C59" strokeWidth="2.5" opacity="0.7" className="tw-pulse" />}
            <circle r={r} fill="#fff" stroke={STc[st]} strokeWidth="4" className={st === 'crit' ? 'tw-critpulse' : ''} />
            <text x="0" y="-1" fontSize={c.unisex ? 15 : 13} textAnchor="middle" fontWeight="700" fill="#1B3A21">{c.id.replace('WC-', '')}</text>
            <text x="0" y="14" fontSize="10" textAnchor="middle" fontWeight="600" fill={STc[st]}>{o}%</text>
            <text x="0" y={r + 15} fontSize="9.5" textAnchor="middle" fill="#1B3A21" opacity="0.5">{c.unisex ? 'unissexo' : 'M/F'}</text>
          </g>
        );
      })}
      {youHere(eng, geo, origin)}
      {northArrow(eng)}
      {scaleBar(eng)}
    </svg>
  );
}

/* 2 · Calor */
function HeatView({ geo, eng, occById, origin, setOrigin }: VProps) {
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg">
      <defs>
        {geo.clusters.map((c) => {
          const o = occById.get(c.id) ?? 0; const col = STc[occSt(o)];
          return (
            <radialGradient key={c.id} id={`heat-${c.id}`}>
              <stop offset="0%" stopColor={col} stopOpacity={0.55} />
              <stop offset="60%" stopColor={col} stopOpacity={0.18} />
              <stop offset="100%" stopColor={col} stopOpacity={0} />
            </radialGradient>
          );
        })}
      </defs>
      {field(eng, geo, '#FAFBF6', '#E5E8E0')}
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0; const rad = 70 + o * 1.6;
        return <circle key={c.id} cx={eng.x(c.e_m)} cy={eng.y(c.n_m)} r={rad} fill={`url(#heat-${c.id})`} />;
      })}
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0;
        return (
          <g key={c.id} transform={`translate(${eng.x(c.e_m)}, ${eng.y(c.n_m)})`} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            <circle r="5" fill="#1B3A21" />
            <text x="0" y="-12" fontSize="12" textAnchor="middle" fontWeight="700" fill="#1B3A21">{c.id.replace('WC-', '')} · {o}%</text>
          </g>
        );
      })}
      {youHere(eng, geo, origin, 14)}
      {northArrow(eng)}
      {scaleBar(eng)}
    </svg>
  );
}

/* 3 · Isométrico */
function IsoView({ geo, eng, occById, origin, setOrigin }: VProps) {
  const iso = (e: number, n: number) => {
    const px = eng.x(e); const py = eng.y(n);
    return { x: (px - py) * 0.7 + VB / 2, y: (px + py) * 0.32 };
  };
  const corners = [iso(0, 0), iso(geo.span_e_m, 0), iso(geo.span_e_m, geo.span_n_m), iso(0, geo.span_n_m)];
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg">
      <polygon points={corners.map((p) => `${p.x},${p.y + 120}`).join(' ')} fill="#EAF3DF" stroke="#C9DDB6" strokeWidth="2" />
      {[...geo.clusters].sort((a, b) => (a.e_m + a.n_m) - (b.e_m + b.n_m)).map((c) => {
        const o = occById.get(c.id) ?? 0; const st = occSt(o);
        const b = iso(c.e_m, c.n_m); const bx = b.x; const by = b.y + 120;
        const h = 30 + o * 0.9; const w = c.unisex ? 40 : 30;
        return (
          <g key={c.id} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            <polygon points={`${bx - w},${by} ${bx},${by + w * 0.5} ${bx},${by + w * 0.5 - h} ${bx - w},${by - h}`} fill={STc[st]} opacity="0.85" />
            <polygon points={`${bx + w},${by} ${bx},${by + w * 0.5} ${bx},${by + w * 0.5 - h} ${bx + w},${by - h}`} fill={STc[st]} opacity="0.62" />
            <polygon points={`${bx - w},${by - h} ${bx},${by + w * 0.5 - h} ${bx + w},${by - h} ${bx},${by - w * 0.5 - h}`} fill={STc[st]} />
            <text x={bx} y={by - h - 8} fontSize="13" textAnchor="middle" fontWeight="700" fill="#1B3A21">{c.id.replace('WC-', '')} · {o}%</text>
            {origin === c.id && <text x={bx} y={by - h - 26} fontSize="11" textAnchor="middle" fontWeight="700" fill="#1B3A21">ESTÁS AQUI</text>}
          </g>
        );
      })}
      {northArrow(eng)}
    </svg>
  );
}

/* 4 · Planta técnica */
function BlueprintView({ geo, eng, origin, setOrigin, occById }: VProps) {
  const grid = [];
  for (let m = 0; m <= geo.span_e_m; m += 50) grid.push(<line key={`v${m}`} x1={eng.x(m)} y1={eng.y(0)} x2={eng.x(m)} y2={eng.y(geo.span_n_m)} stroke="#E5E8E0" strokeWidth="1" />);
  for (let m = 0; m <= geo.span_n_m; m += 50) grid.push(<line key={`h${m}`} x1={eng.x(0)} y1={eng.y(m)} x2={eng.x(geo.span_e_m)} y2={eng.y(m)} stroke="#E5E8E0" strokeWidth="1" />);
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg" style={{ background: '#fff' }}>
      {grid}
      <rect x={eng.x(0)} y={eng.y(geo.span_n_m)} width={geo.span_e_m * eng.S} height={geo.span_n_m * eng.S} fill="none" stroke="#0D1A0F" strokeWidth="2" />
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0; const w = c.unisex ? 30 : 24;
        return (
          <g key={c.id} transform={`translate(${eng.x(c.e_m)}, ${eng.y(c.n_m)})`} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            <rect x={-w} y={-w} width={w * 2} height={w * 2} fill="none" stroke="#0D1A0F" strokeWidth="1.5" />
            <line x1={-w} y1={-w} x2={w} y2={w} stroke="#E5E8E0" strokeWidth="1" />
            <line x1={-w} y1={w} x2={w} y2={-w} stroke="#E5E8E0" strokeWidth="1" />
            <text x="0" y="-2" fontSize="12" textAnchor="middle" fontWeight="700" fill="#0D1A0F">{c.id}</text>
            <text x="0" y="12" fontSize="9" textAnchor="middle" fill="#3A4A3F">{c.capacity_total} lug · {o}%</text>
          </g>
        );
      })}
      <g transform={`translate(${VB - 200}, ${VB - 70})`}>
        <rect x="0" y="0" width="180" height="52" fill="none" stroke="#0D1A0F" strokeWidth="1.5" />
        <text x="10" y="20" fontSize="12" fontWeight="700" fill="#0D1A0F">PARQUE TEJO · 1:2500</text>
        <text x="10" y="38" fontSize="10" fill="#3A4A3F">Planta · 8 núcleos · {Math.round(geo.span_e_m)}×{Math.round(geo.span_n_m)} m</text>
      </g>
      {scaleBar(eng)}
      {northArrow(eng)}
    </svg>
  );
}

/* 5 · Fluxos */
function FlowView({ geo, eng, occById, origin, setOrigin }: VProps) {
  const entrance = geo.landmarks.find((l) => l.kind === 'entrance') ?? { e_m: 290, n_m: 175 };
  const ex = eng.x(entrance.e_m); const ey = eng.y(entrance.n_m);
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg">
      {field(eng, geo, '#FAFBF6', '#E5E8E0')}
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0; const cx = eng.x(c.e_m); const cy = eng.y(c.n_m);
        const mx = (ex + cx) / 2; const my = (ey + cy) / 2 - 60;
        const w = 1.5 + (100 - o) / 25;
        return <path key={`f${c.id}`} d={`M ${ex} ${ey} Q ${mx} ${my} ${cx} ${cy}`} fill="none" stroke={STc[occSt(o)]} strokeWidth={w} opacity="0.5" strokeDasharray="8 10" className="tw-dash" />;
      })}
      <g transform={`translate(${ex}, ${ey})`}><circle r="9" fill="#1B3A21" /><text x="0" y="-16" fontSize="12" textAnchor="middle" fontWeight="700" fill="#1B3A21">Entrada</text></g>
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0;
        return (
          <g key={c.id} transform={`translate(${eng.x(c.e_m)}, ${eng.y(c.n_m)})`} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            <circle r="20" fill="#fff" stroke={STc[occSt(o)]} strokeWidth="3.5" />
            <text x="0" y="4" fontSize="12" textAnchor="middle" fontWeight="700" fill="#1B3A21">{c.id.replace('WC-', '')}</text>
          </g>
        );
      })}
      {northArrow(eng)}
    </svg>
  );
}

/* 6 · Satélite */
function SatView({ geo, eng, occById, origin, setOrigin, reco }: VProps) {
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg" style={{ background: '#3A4A3F' }}>
      {field(eng, geo, '#5C7049', '#46583a', 12)}
      <rect x="0" y={VB - PAD * 0.55} width={VB} height={PAD * 0.55} fill="#3E6B78" opacity="0.8" />
      {route(eng, reco)}
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0; const w = c.unisex ? 30 : 24;
        return (
          <g key={c.id} transform={`translate(${eng.x(c.e_m)}, ${eng.y(c.n_m)})`} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            <rect x={-w} y={-w * 0.7} width={w * 2} height={w * 1.4} rx="3" fill="#9AA0A6" stroke="#6B7280" strokeWidth="1.5" />
            <rect x={-w} y={-w * 0.7} width={w * 2} height="5" fill={STc[occSt(o)]} />
            <text x="0" y="3" fontSize="11" textAnchor="middle" fontWeight="700" fill="#0D1A0F" style={{ paintOrder: 'stroke', stroke: '#fff', strokeWidth: 2 }}>{c.id.replace('WC-', '')}</text>
          </g>
        );
      })}
      {youHere(eng, geo, origin, 26)}
      {northArrow(eng)}
    </svg>
  );
}

/* 7 · Mundo (overworld editorial) */
function WorldView({ geo, eng, occById, origin, setOrigin }: VProps) {
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg" shapeRendering="crispEdges">
      {field(eng, geo, '#CFE8B0', '#9FC97A', 8)}
      {/* tufos de erva */}
      {Array.from({ length: 36 }).map((_, i) => {
        const gx = PAD + 30 + (i % 9) * ((VB - 2 * PAD - 60) / 8);
        const gy = PAD + 30 + Math.floor(i / 9) * ((VB - 2 * PAD - 60) / 4);
        return <g key={i} opacity="0.5"><path d={`M ${gx} ${gy} l 4 -10 l 4 10`} stroke="#7CB342" strokeWidth="2" fill="none" /></g>;
      })}
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0; const m = meta(c.id); const w = c.unisex ? 30 : 24;
        const cx = eng.x(c.e_m); const cy = eng.y(c.n_m);
        return (
          <g key={c.id} transform={`translate(${cx}, ${cy})`} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            {/* casinha */}
            <rect x={-w} y={-w * 0.5} width={w * 2} height={w} fill="#F4ECD8" stroke="#5A743F" strokeWidth="2.5" />
            <polygon points={`${-w - 4},${-w * 0.5} 0,${-w * 1.1} ${w + 4},${-w * 0.5}`} fill={m.color} stroke="#5A743F" strokeWidth="2.5" />
            <rect x="-6" y={w * 0.1} width="12" height={w * 0.4} fill="#5A743F" />
            <text x="0" y={w + 16} fontSize="11" textAnchor="middle" fontWeight="700" fill="#2A3320">{c.id}</text>
            <g transform={`translate(0, ${w + 26})`}>
              <rect x="-26" y="-9" width="52" height="16" rx="8" fill={m.color} opacity="0.9" />
              <text x="0" y="3" fontSize="9" textAnchor="middle" fontWeight="700" fill="#fff">{m.element} · {o}%</text>
            </g>
            {o >= 85 && <text x="0" y={-w * 1.3} fontSize="18" textAnchor="middle" fontWeight="800" fill="#C25A1A" className="tw-critpulse">!</text>}
          </g>
        );
      })}
      {youHere(eng, geo, origin, 28)}
    </svg>
  );
}

/* 8 · Coleção (dex) — não geográfica */
function DexView({ geo, occById, origin, setOrigin }: VProps) {
  return (
    <div className="tw-dex">
      {geo.clusters.map((c) => {
        const o = occById.get(c.id) ?? 0; const st = occSt(o); const m = meta(c.id);
        return (
          <button key={c.id} className={`tw-card ${origin === c.id ? 'is-on' : ''}`} onClick={() => setOrigin(origin === c.id ? null : c.id)} style={{ ['--tc' as any]: m.color }}>
            <div className="tw-card-top">
              <span className="tw-dex-num">{dexNum(c.id)}</span>
              <span className="tw-card-id">{c.id}</span>
            </div>
            <div className="tw-card-name">{m.name}</div>
            <div className="tw-card-badges">
              <span className="tw-elem" style={{ background: m.color }}>{m.element}</span>
              <span className="tw-gender">{c.unisex ? 'Unissexo' : 'M/F'}</span>
            </div>
            <div className="tw-card-bar"><div className="tw-card-fill" style={{ width: `${Math.min(100, o)}%`, background: STc[st] }} /></div>
            <div className="tw-card-foot">
              <span style={{ color: STc[st], fontWeight: 700 }}>{o}% · {STlabel[st]}</span>
              <span className="tw-card-cap">{c.capacity_total} lug</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

/* 9 · Radar (anéis) — não geográfica */
function RadarView({ geo, occById, origin, setOrigin }: VProps) {
  const cx = VB / 2, cy = VB / 2; const n = geo.clusters.length;
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg">
      {[0.25, 0.5, 0.75, 1].map((f) => <circle key={f} cx={cx} cy={cy} r={f * 360} fill="none" stroke="#E5E8E0" strokeWidth="1" />)}
      <text x={cx} y={cy - 360 - 10} fontSize="11" textAnchor="middle" fill="#3A4A3F">100%</text>
      {geo.clusters.map((c, i) => {
        const o = occById.get(c.id) ?? 0; const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
        const rr = (o / 100) * 360;
        const px = cx + Math.cos(ang) * rr; const py = cy + Math.sin(ang) * rr;
        const lx = cx + Math.cos(ang) * 400; const ly = cy + Math.sin(ang) * 400;
        return (
          <g key={c.id} style={{ cursor: 'pointer' }} onClick={() => setOrigin(origin === c.id ? null : c.id)}>
            <line x1={cx} y1={cy} x2={lx} y2={ly} stroke="#E5E8E0" strokeWidth="1" />
            <line x1={cx} y1={cy} x2={px} y2={py} stroke={STc[occSt(o)]} strokeWidth="4" strokeLinecap="round" />
            <circle cx={px} cy={py} r="7" fill={STc[occSt(o)]} stroke="#fff" strokeWidth="2" />
            <text x={lx} y={ly} fontSize="12" textAnchor={Math.cos(ang) < -0.3 ? 'end' : Math.cos(ang) > 0.3 ? 'start' : 'middle'} fontWeight="700" fill="#1B3A21">{c.id.replace('WC-', '')} {o}%</text>
          </g>
        );
      })}
    </svg>
  );
}

/* 10 · Arena (cheio vs livre) — não geográfica */
function ArenaView({ geo, occById }: VProps) {
  const sorted = [...geo.clusters].map((c) => ({ c, o: occById.get(c.id) ?? 0 })).sort((a, b) => b.o - a.o);
  const villain = sorted[0]; const hero = sorted[sorted.length - 1];
  const card = (x: number, y: number, c: GeoCluster, o: number, label: string) => {
    const m = meta(c.id);
    return (
      <g transform={`translate(${x}, ${y})`}>
        <rect x="-150" y="-50" width="300" height="100" rx="14" fill="#FFFCEC" stroke="#1B3A21" strokeWidth="3" />
        <text x="-135" y="-22" fontSize="12" fontWeight="700" fill="#1B3A21">{c.id} · {m.name}</text>
        <text x="-135" y="-4" fontSize="11" fill="#3A4A3F">{label} · {m.element}</text>
        <rect x="-135" y="10" width="270" height="12" rx="6" fill="#E5E8E0" />
        <rect x="-135" y="10" width={2.7 * Math.min(100, o)} height="12" rx="6" fill={STc[occSt(o)]} />
        <text x="135" y="38" fontSize="13" textAnchor="end" fontWeight="700" fill={STc[occSt(o)]}>{o}%</text>
      </g>
    );
  };
  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="tw-svg">
      <defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#BFE0E8" /><stop offset="100%" stopColor="#CFE8B0" /></linearGradient></defs>
      <rect x="0" y="0" width={VB} height={VB} fill="url(#sky)" rx="20" />
      <ellipse cx="700" cy="340" rx="180" ry="48" fill="#9FC97A" opacity="0.7" />
      <ellipse cx="320" cy="680" rx="200" ry="54" fill="#9FC97A" opacity="0.7" />
      {villain && card(700, 270, villain.c, villain.o, 'Mais cheio')}
      {hero && card(320, 610, hero.c, hero.o, 'Mais livre · vai aqui')}
      <text x={VB / 2} y="90" fontSize="20" textAnchor="middle" fontWeight="800" fill="#1B3A21">
        {villain ? `${villain.c.id} está no limite — desvia para ${hero?.c.id}` : ''}
      </text>
    </svg>
  );
}

const VIEWS: { id: string; label: string; comp: (p: VProps) => JSX.Element; geographic: boolean }[] = [
  { id: 'mapa', label: 'Mapa', comp: MapView, geographic: true },
  { id: 'mundo', label: 'Mundo', comp: WorldView, geographic: true },
  { id: 'calor', label: 'Calor', comp: HeatView, geographic: true },
  { id: 'iso', label: 'Isométrico', comp: IsoView, geographic: true },
  { id: 'fluxos', label: 'Fluxos', comp: FlowView, geographic: true },
  { id: 'satelite', label: 'Satélite', comp: SatView, geographic: true },
  { id: 'planta', label: 'Planta', comp: BlueprintView, geographic: true },
  { id: 'radar', label: 'Radar', comp: RadarView, geographic: false },
  { id: 'colecao', label: 'Coleção', comp: DexView, geographic: false },
  { id: 'arena', label: 'Arena', comp: ArenaView, geographic: false },
];

/* ════════════════════════════════════════════════════════════════════
   HISTÓRICO / TENDÊNCIA / FLUXO (observado nesta sessão)
   ════════════════════════════════════════════════════════════════════ */

function paramOf(snap: LiveSnapshot | null, id: string, key: string): number {
  const c = snap?.clusters?.find((x) => x.cluster_id.toLowerCase() === id.toLowerCase());
  const p: any = c?.params ?? {};
  return Number(p[key] ?? 0);
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return <div className="tw-spark-empty">a recolher dados…</div>;
  const w = 280, h = 56, pad = 4;
  const max = 100, min = 0;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - 2 * pad);
    const y = h - pad - ((v - min) / (max - min)) * (h - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const area = `M ${pad},${h - pad} L ${pts.join(' L ')} L ${w - pad},${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="tw-spark" preserveAspectRatio="none">
      <line x1={pad} y1={h - pad - (0.85 * (h - 2 * pad))} x2={w - pad} y2={h - pad - (0.85 * (h - 2 * pad))} stroke="#C25A1A" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
      <path d={area} fill={color} opacity="0.12" />
      <polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={pts[pts.length - 1].split(',')[0]} cy={pts[pts.length - 1].split(',')[1]} r="3.5" fill={color} />
    </svg>
  );
}

function project(data: number[]): number | null {
  if (data.length < 3) return null;
  const recent = data.slice(-5);
  const slope = (recent[recent.length - 1] - recent[0]) / (recent.length - 1);
  return Math.max(0, Math.min(100, Math.round(recent[recent.length - 1] + slope * 2)));
}

/* ════════════════════════════════════════════════════════════════════
   PAINEL DE DETALHE — capacidade · agora · tendência · projeção · fluxo
   ════════════════════════════════════════════════════════════════════ */

interface DetailProps {
  cluster: GeoCluster; occ: number; hist: number[];
  snap: LiveSnapshot | null;
  reco: { to: GeoCluster; dist: number; walk: number; occ: number; allFull: boolean } | null;
  onClose: () => void;
}

function DetailPanel({ cluster, occ, hist, snap, reco, onClose }: DetailProps) {
  const m = meta(cluster.id);
  const st = occSt(occ);
  const fila = Math.round(paramOf(snap, cluster.id, 'fila_atual'));
  const espera = paramOf(snap, cluster.id, 'tempo_espera_min');
  const fluxo = Math.round(paramOf(snap, cluster.id, 'fluxo_entrada_pmin'));
  const pessoas = Math.round((occ / 100) * cluster.capacity_total);
  const proj = project(hist);
  const livres = Math.max(0, cluster.capacity_total - pessoas);

  return (
    <aside className="tw-detail-inner">
      <div className="tw-d-head" style={{ ['--tc' as any]: m.color }}>
        <div>
          <div className="tw-d-dex">{dexNum(cluster.id)} · {m.name}</div>
          <div className="tw-d-id">{cluster.id}</div>
        </div>
        <button className="tw-d-close" onClick={onClose} aria-label="Fechar">✕</button>
      </div>

      <div className="tw-d-badges">
        <span className="tw-d-elem" style={{ background: m.color }}>{m.element}</span>
        <span className="tw-d-gen">{cluster.unisex ? 'Unissexo' : 'M / F'}</span>
        <span className="tw-d-state" style={{ color: STc[st] }}>● {STlabel[st]}</span>
      </div>

      {/* AGORA */}
      <section className="tw-d-sec">
        <h3 className="tw-d-h3">Agora</h3>
        <div className="tw-d-big" style={{ color: STc[st] }}>{occ}<span>%</span></div>
        <div className="tw-d-grid">
          <div className="tw-d-cell"><span className="tw-d-k">Pessoas</span><span className="tw-d-v">{pessoas}</span></div>
          <div className="tw-d-cell"><span className="tw-d-k">Lugares livres</span><span className="tw-d-v">{livres}</span></div>
          <div className="tw-d-cell"><span className="tw-d-k">Fila</span><span className="tw-d-v">{fila}</span></div>
          <div className="tw-d-cell"><span className="tw-d-k">Espera</span><span className="tw-d-v">{espera.toFixed(0)} min</span></div>
        </div>
      </section>

      {/* TENDÊNCIA + PROJEÇÃO */}
      <section className="tw-d-sec">
        <h3 className="tw-d-h3">Tendência <span className="tw-d-sub">observado · projeção</span></h3>
        <Sparkline data={hist} color={m.color} />
        <div className="tw-d-proj">
          {proj !== null
            ? <>Projeção a ~20 min: <strong style={{ color: STc[occSt(proj)] }}>{proj}%</strong> · {proj > occ ? 'a subir' : proj < occ ? 'a descer' : 'estável'}</>
            : <>a recolher dados para projeção…</>}
        </div>
      </section>

      {/* FLUXO */}
      <section className="tw-d-sec">
        <h3 className="tw-d-h3">Fluxo</h3>
        <div className="tw-d-grid">
          <div className="tw-d-cell"><span className="tw-d-k">Entrada</span><span className="tw-d-v">{fluxo}/min</span></div>
          <div className="tw-d-cell"><span className="tw-d-k">Distância à entrada</span><span className="tw-d-v">{Math.round(Math.hypot(cluster.e_m - 290, cluster.n_m - 175))} m</span></div>
        </div>
      </section>

      {/* CAPACIDADE */}
      <section className="tw-d-sec">
        <h3 className="tw-d-h3">Capacidade</h3>
        <div className="tw-d-cap">
          <div className="tw-d-cap-row"><span>Total</span><strong>{cluster.capacity_total} lugares</strong></div>
          {!cluster.unisex && cluster.cap_m !== null && (
            <div className="tw-d-cap-bar">
              <div className="tw-d-cap-m" style={{ width: `${(cluster.cap_m / cluster.capacity_total) * 100}%` }}>M {cluster.cap_m}</div>
              <div className="tw-d-cap-f" style={{ width: `${((cluster.cap_f ?? 0) / cluster.capacity_total) * 100}%` }}>F {cluster.cap_f}</div>
            </div>
          )}
          {cluster.unisex && <div className="tw-d-cap-row"><span>Unissexo</span><strong>{cluster.cap ?? cluster.capacity_total} lugares</strong></div>}
        </div>
        <div className="tw-d-desc">{cluster.desc}</div>
      </section>

      {/* RECOMENDAÇÃO */}
      {reco && (
        <section className="tw-d-sec tw-d-reco">
          <h3 className="tw-d-h3">{occ >= 85 ? 'Está cheio — desvia para' : 'Alternativa mais perto'}</h3>
          <div className="tw-d-reco-box">
            <span className="tw-d-reco-wc">{reco.to.id}</span>
            <span className="tw-d-reco-m">{reco.dist} m · {reco.walk} min · <span style={{ color: STc[occSt(reco.occ)] }}>{STlabel[occSt(reco.occ)]}</span></span>
          </div>
        </section>
      )}
    </aside>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PÁGINA
   ════════════════════════════════════════════════════════════════════ */

export default function TwinPage() {
  const { snapshot, connection } = useLive();
  const [geo, setGeo] = useState<GeoPayload>(FALLBACK_GEO);
  const [viewId, setViewId] = useState('mapa');
  const [selected, setSelected] = useState<string | null>(null);

  const histRef = useRef<Map<string, number[]>>(new Map());
  const lastTsRef = useRef<number>(0);
  const [, setHistTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/clusters/geo`, { cache: 'no-store' });
        if (r.ok) { const j = await r.json(); if (!cancelled && j?.clusters?.length) setGeo(j); }
      } catch { /* fallback */ }
    })();
    return () => { cancelled = true; };
  }, []);

  // buffer de histórico (um ponto a cada ~8s por cluster)
  useEffect(() => {
    const now = Date.now();
    if (now - lastTsRef.current < 7000 && lastTsRef.current !== 0) return;
    lastTsRef.current = now;
    for (const c of geo.clusters) {
      const arr = histRef.current.get(c.id) ?? [];
      arr.push(occOf(snapshot, c.id));
      if (arr.length > 40) arr.shift();
      histRef.current.set(c.id, arr);
    }
    setHistTick((x) => x + 1);
  }, [snapshot, geo]);

  const eng = useMemo(() => makeEngine(geo), [geo]);
  const occById = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of geo.clusters) m.set(c.id, occOf(snapshot, c.id));
    return m;
  }, [geo, snapshot]);

  const reco = useMemo(() => {
    if (!selected) return null;
    const from = geo.clusters.find((c) => c.id === selected);
    if (!from) return null;
    const cand = geo.clusters.filter((c) => c.id !== selected).map((c) => ({ c, d: distM(from, c), o: occById.get(c.id) ?? 0 }));
    const free = cand.filter((r) => r.o < 85).sort((a, b) => a.d - b.d);
    const pick = free[0] ?? cand.sort((a, b) => a.o - b.o)[0];
    return pick ? { from, to: pick.c, dist: Math.round(pick.d), walk: Math.max(1, Math.round(pick.d / (1.35 * 60))), occ: pick.o, allFull: free.length === 0 } : null;
  }, [selected, geo, occById]);

  const View = VIEWS.find((v) => v.id === viewId) ?? VIEWS[0];
  const live = connection === 'sse' || connection === 'polling';
  const selCluster = selected ? geo.clusters.find((c) => c.id === selected) ?? null : null;
  const vprops: VProps = { geo, eng, occById, origin: selected, setOrigin: setSelected, reco: reco ? { from: reco.from, to: reco.to } : null };

  return (
    <div className="tw-root">
      <div className="tw-hud">
        <div>
          <div className="tw-eyebrow">PlantaOS · Digital Twin · Parque Tejo</div>
          <h1 className="tw-title">{View.label}</h1>
        </div>
        <div className="tw-conn"><span className="tw-cd" style={{ background: live ? '#6FAF82' : '#6B7280' }} />{live ? 'ao vivo' : 'a ligar…'}</div>
      </div>

      <div className="tw-tabs">
        {VIEWS.map((v) => (
          <button key={v.id} className={`tw-tab ${v.id === viewId ? 'is-on' : ''}`} onClick={() => setViewId(v.id)}>{v.label}</button>
        ))}
      </div>

      <div className={`tw-split ${selCluster ? 'is-open' : ''}`}>
        <div className="tw-viz"><View.comp {...vprops} /></div>
        <div className={`tw-detail ${selCluster ? 'is-open' : ''}`}>
          {selCluster && (
            <DetailPanel
              cluster={selCluster}
              occ={occById.get(selCluster.id) ?? 0}
              hist={histRef.current.get(selCluster.id) ?? []}
              snap={snapshot}
              reco={reco}
              onClose={() => setSelected(null)}
            />
          )}
        </div>
      </div>

      {!selCluster && <div className="tw-bar"><div className="tw-hint">Toca num WC para abrir tudo sobre ele · capacidade, fluxo, tendência e para onde desviar.</div></div>}

      <style jsx>{`
        .tw-root { position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; overflow: hidden; background: var(--paper, #FAFAF7); color: #0D1A0F; }
        .tw-hud { flex-shrink: 0; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: clamp(10px,1.4vw,16px) clamp(14px,2.6vw,32px) 0; }
        .tw-eyebrow { font-size: 10px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; opacity: 0.45; }
        .tw-title { font-size: clamp(22px,3vw,40px); font-weight: 200; letter-spacing: -0.04em; line-height: 1; margin-top: 4px; }
        .tw-conn { display: flex; align-items: center; gap: 7px; font-size: 12px; font-weight: 600; opacity: 0.65; flex-shrink: 0; }
        .tw-cd { width: 8px; height: 8px; border-radius: 50%; animation: tw-blink 1.8s ease-in-out infinite; }

        .tw-tabs { flex-shrink: 0; display: flex; gap: 6px; overflow-x: auto; padding: 12px clamp(14px,2.6vw,32px); scrollbar-width: none; }
        .tw-tabs::-webkit-scrollbar { display: none; }
        .tw-tab { white-space: nowrap; background: #fff; border: 1px solid #E5E8E0; border-radius: 999px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; color: #0D1A0F; font-family: inherit; flex-shrink: 0; transition: all 0.14s; }
        .tw-tab:hover { border-color: #4A7C59; }
        .tw-tab.is-on { background: #1B3A21; border-color: #1B3A21; color: #fff; font-weight: 600; }

        .tw-split { flex: 1; min-height: 0; display: flex; gap: 0; }
        .tw-viz { flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center; padding: 4px clamp(8px,2vw,24px); transition: padding 0.32s cubic-bezier(0.2,0.8,0.2,1); }
        .tw-detail { width: 0; flex-shrink: 0; overflow: hidden; transition: width 0.32s cubic-bezier(0.2,0.8,0.2,1); }
        .tw-detail.is-open { width: clamp(320px, 32%, 420px); }

        .tw-bar { flex-shrink: 0; padding: clamp(8px,1.2vw,14px) clamp(14px,2.6vw,32px) max(14px, env(safe-area-inset-bottom)); }
        .tw-hint { text-align: center; font-size: 14px; opacity: 0.55; }

        @media (max-width: 860px) {
          .tw-split { position: relative; }
          .tw-detail { position: fixed; left: 0; right: 0; bottom: 0; width: auto !important; max-height: 72vh; background: #fff; border-top-left-radius: 22px; border-top-right-radius: 22px; box-shadow: 0 -8px 30px rgba(13,26,15,0.16); transform: translateY(100%); transition: transform 0.32s cubic-bezier(0.2,0.8,0.2,1); z-index: 40; overflow-y: auto; }
          .tw-detail.is-open { transform: translateY(0); width: auto; }
        }
        @media (prefers-reduced-motion: reduce) {
          .tw-viz, .tw-detail, .tw-cd { transition: none; animation: none; }
        }
      `}</style>

      <style jsx global>{`
        .tw-svg { width: 100%; height: 100%; max-width: min(90vh, 100%); display: block; }
        .tw-node { animation: tw-pop 0.5s cubic-bezier(0.2,0.7,0.2,1) backwards; animation-delay: var(--d); }
        .tw-dash { animation: tw-dashmove 0.8s linear infinite; }
        .tw-pulse { animation: tw-blink 1.6s ease-in-out infinite; }
        .tw-critpulse { animation: tw-blink 1.4s ease-in-out infinite; }
        .tw-you { animation: tw-pop 0.4s cubic-bezier(0.2,0.7,0.2,1); }
        @keyframes tw-pop { from { opacity: 0; transform: translateY(8px) scale(0.85); } to { opacity: 1; transform: scale(1); } }
        @keyframes tw-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes tw-dashmove { to { stroke-dashoffset: -18; } }

        .tw-dex { width: 100%; max-width: 1100px; height: 100%; display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr); gap: clamp(8px,1vw,14px); padding: 4px; }
        .tw-card { display: flex; flex-direction: column; gap: 6px; background: #fff; border: 1px solid #E5E8E0; border-left: 4px solid var(--tc); border-radius: 14px; padding: clamp(10px,1.2vw,16px); cursor: pointer; font-family: inherit; text-align: left; transition: all 0.14s; min-height: 0; }
        .tw-card:hover { border-color: #4A7C59; transform: translateY(-2px); }
        .tw-card.is-on { box-shadow: 0 0 0 2px #1B3A21; }
        .tw-card-top { display: flex; justify-content: space-between; align-items: center; }
        .tw-dex-num { font-size: 11px; font-weight: 700; color: var(--tc); font-variant-numeric: tabular-nums; font-family: monospace; }
        .tw-card-id { font-size: 13px; font-weight: 700; }
        .tw-card-name { font-size: clamp(16px,1.8vw,22px); font-weight: 600; letter-spacing: -0.02em; color: #1B3A21; }
        .tw-card-badges { display: flex; gap: 6px; align-items: center; }
        .tw-elem { font-size: 10px; font-weight: 700; color: #fff; padding: 3px 9px; border-radius: 999px; }
        .tw-gender { font-size: 10px; font-weight: 600; color: #3A4A3F; opacity: 0.7; }
        .tw-card-bar { height: 8px; background: #F0EEE6; border-radius: 4px; overflow: hidden; margin-top: auto; }
        .tw-card-fill { height: 100%; border-radius: 4px; transition: width 0.6s; }
        .tw-card-foot { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
        .tw-card-cap { color: #3A4A3F; opacity: 0.6; font-variant-numeric: tabular-nums; }

        /* PAINEL DE DETALHE */
        .tw-detail-inner { height: 100%; overflow-y: auto; padding: clamp(16px,1.6vw,22px); display: flex; flex-direction: column; gap: 16px; background: #fff; border-left: 1px solid #E5E8E0; }
        .tw-d-head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid var(--tc); padding-bottom: 12px; }
        .tw-d-dex { font-size: 12px; font-weight: 700; color: var(--tc); font-family: monospace; }
        .tw-d-id { font-size: clamp(22px,2.4vw,30px); font-weight: 700; letter-spacing: -0.03em; }
        .tw-d-close { background: #F0EEE6; border: none; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 14px; color: #0D1A0F; flex-shrink: 0; }
        .tw-d-close:hover { background: #E5E8E0; }
        .tw-d-badges { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .tw-d-elem { font-size: 11px; font-weight: 700; color: #fff; padding: 4px 11px; border-radius: 999px; }
        .tw-d-gen { font-size: 11px; font-weight: 600; color: #3A4A3F; }
        .tw-d-state { font-size: 12px; font-weight: 700; margin-left: auto; }
        .tw-d-sec { display: flex; flex-direction: column; gap: 8px; }
        .tw-d-h3 { font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #3A4A3F; opacity: 0.6; margin: 0; }
        .tw-d-sub { opacity: 0.6; font-weight: 600; letter-spacing: 0.04em; }
        .tw-d-big { font-size: clamp(40px,5vw,60px); font-weight: 200; letter-spacing: -0.04em; line-height: 0.9; }
        .tw-d-big span { font-size: 0.4em; font-weight: 500; opacity: 0.6; }
        .tw-d-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .tw-d-cell { background: #FAFBF6; border: 1px solid #E5E8E0; border-radius: 10px; padding: 9px 11px; display: flex; flex-direction: column; gap: 2px; }
        .tw-d-k { font-size: 10px; font-weight: 600; color: #3A4A3F; opacity: 0.65; }
        .tw-d-v { font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; }
        .tw-spark { width: 100%; height: 56px; display: block; }
        .tw-spark-empty { font-size: 12px; opacity: 0.5; padding: 18px 0; text-align: center; }
        .tw-d-proj { font-size: 13px; color: #3A4A3F; }
        .tw-d-proj strong { font-weight: 800; }
        .tw-d-cap { display: flex; flex-direction: column; gap: 8px; }
        .tw-d-cap-row { display: flex; justify-content: space-between; font-size: 14px; }
        .tw-d-cap-bar { display: flex; height: 30px; border-radius: 8px; overflow: hidden; }
        .tw-d-cap-m { background: #4A7C59; color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; padding-left: 10px; }
        .tw-d-cap-f { background: #6FAF82; color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; padding-left: 10px; }
        .tw-d-desc { font-size: 12px; color: #3A4A3F; opacity: 0.7; }
        .tw-d-reco-box { background: #FAFBF6; border: 1px solid #C9DDB6; border-radius: 12px; padding: 12px 14px; display: flex; flex-direction: column; gap: 3px; }
        .tw-d-reco-wc { font-size: 22px; font-weight: 700; color: #4A7C59; letter-spacing: -0.02em; }
        .tw-d-reco-m { font-size: 13px; color: #3A4A3F; font-variant-numeric: tabular-nums; }

        @media (max-width: 760px) {
          .tw-dex { grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(4, 1fr); }
        }
        @media (prefers-reduced-motion: reduce) {
          .tw-node, .tw-you, .tw-dash, .tw-pulse, .tw-critpulse { animation: none; }
        }
      `}</style>
    </div>
  );
}
