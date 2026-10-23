"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, subscribeRunEvents, TERMINAL_STAGES } from "@/lib/api";
import type { RunEvent, RunState } from "@/lib/types";

const REFRESH_EVENTS = new Set(["stage_started", "stage_completed", "hitl_required", "error", "done"]);
const MAX_LOG = 500;

export function useRun(runId: string) {
  const [run, setRun] = useState<RunState | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await api.getRun(runId);
      setRun(r);
      setError(null);
      return r;
    } catch (e) {
      setError((e as Error).message);
      return null;
    }
  }, [runId]);

  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) return;
    refreshTimer.current = setTimeout(() => {
      refreshTimer.current = null;
      void refresh();
    }, 300);
  }, [refresh]);

  // initial load
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // SSE subscription while the run is live
  const terminal = run ? TERMINAL_STAGES.has(run.stage) : false;
  useEffect(() => {
    if (!run || terminal) return;
    setConnected(true);
    const unsubscribe = subscribeRunEvents(
      runId,
      (ev) => {
        setEvents((prev) => {
          const next = [...prev, ev];
          return next.length > MAX_LOG ? next.slice(next.length - MAX_LOG) : next;
        });
        if (REFRESH_EVENTS.has(ev.type)) scheduleRefresh();
      },
      () => {
        setConnected(false);
        scheduleRefresh();
      },
      () => setConnected(false),
    );
    return () => {
      unsubscribe();
      setConnected(false);
    };
    // re-subscribe only when the run id changes or the run becomes live/terminal
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, terminal, run === null]);

  // polling fallback (SSE may be unavailable behind some proxies)
  useEffect(() => {
    if (!run || terminal) return;
    const id = setInterval(() => void refresh(), 6000);
    return () => clearInterval(id);
  }, [run, terminal, refresh]);

  return { run, setRun, events, error, connected, refresh };
}
