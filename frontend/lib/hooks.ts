'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import type { LivePayload, GlobalKPIs, SensorHealth } from './types';

interface BackendStateResult {
  state: LivePayload | null;
  isOffline: boolean;
  isSimulated: boolean;
  lastUpdate: Date | null;
  error: string | null;
}

export function useBackendState(): BackendStateResult {
  const [state, setState] = useState<LivePayload | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [failCount, setFailCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const data = await api.state();
      setState(data);
      setIsOffline(false);
      setFailCount(0);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      const newCount = failCount + 1;
      setFailCount(newCount);
      if (newCount >= 2) {
        setIsOffline(true);
      }
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    }
  }, [failCount]);

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 10_000);
    return () => clearInterval(interval);
  }, []);

  return {
    state,
    isOffline,
    isSimulated: state?.any_simulated ?? false,
    lastUpdate,
    error,
  };
}

interface KPIsResult {
  kpis: GlobalKPIs | null;
  isOffline: boolean;
  lastUpdate: Date | null;
}

export function useKPIs(): KPIsResult {
  const [kpis, setKpis] = useState<GlobalKPIs | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [failCount, setFailCount] = useState(0);

  const fetchKPIs = useCallback(async () => {
    try {
      const data = await api.kpis();
      setKpis(data);
      setIsOffline(false);
      setFailCount(0);
      setLastUpdate(new Date());
    } catch {
      const newCount = failCount + 1;
      setFailCount(newCount);
      if (newCount >= 2) setIsOffline(true);
    }
  }, [failCount]);

  useEffect(() => {
    fetchKPIs();
    const interval = setInterval(fetchKPIs, 10_000);
    return () => clearInterval(interval);
  }, []);

  return { kpis, isOffline, lastUpdate };
}

interface SensorsResult {
  sensors: SensorHealth[];
  isOffline: boolean;
  lastUpdate: Date | null;
}

export function useSensors(): SensorsResult {
  const [sensors, setSensors] = useState<SensorHealth[]>([]);
  const [isOffline, setIsOffline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [failCount, setFailCount] = useState(0);

  const fetchSensors = useCallback(async () => {
    try {
      const data = await api.sensors();
      setSensors(data);
      setIsOffline(false);
      setFailCount(0);
      setLastUpdate(new Date());
    } catch {
      const newCount = failCount + 1;
      setFailCount(newCount);
      if (newCount >= 2) setIsOffline(true);
    }
  }, [failCount]);

  useEffect(() => {
    fetchSensors();
    const interval = setInterval(fetchSensors, 15_000);
    return () => clearInterval(interval);
  }, []);

  return { sensors, isOffline, lastUpdate };
}
