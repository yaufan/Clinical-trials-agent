"use client";

import { Activity, AlertTriangle, CheckCircle2, Hand, Play, Wrench } from "lucide-react";
import { useEffect, useRef } from "react";
import { stageLabel } from "@/lib/labels";
import type { RunEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

function icon(type: string) {
  switch (type) {
    case "stage_started":
      return <Play size={13} className="text-info" />;
    case "stage_completed":
    case "done":
      return <CheckCircle2 size={13} className="text-success" />;
    case "tool_call":
      return <Wrench size={13} className="text-accent" />;
    case "hitl_required":
      return <Hand size={13} className="text-warning" />;
    case "error":
      return <AlertTriangle size={13} className="text-danger" />;
    default:
      return <Activity size={13} className="text-muted" />;
  }
}

export function EventLog({ events, connected, className }: { events: RunEvent[]; connected: boolean; className?: string }) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [events.length]);
  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="flex items-center justify-between pb-2 text-xs text-muted">
        <span>即時事件 Live events ({events.length})</span>
        <span className={cn("inline-flex items-center gap-1", connected ? "text-success" : "")}>
          <span className={cn("h-2 w-2 rounded-full", connected ? "bg-success" : "bg-border")} />
          {connected ? "SSE connected" : "idle"}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto rounded-md border border-border bg-surface-2 p-2 font-mono text-xs">
        {events.length === 0 ? <div className="p-2 text-muted">尚無事件 / no events yet</div> : null}
        {events.map((ev, i) => (
          <div key={i} className="flex gap-2 border-b border-border/60 py-1 last:border-0">
            <span className="mt-0.5 shrink-0">{icon(ev.type)}</span>
            <span className="shrink-0 text-muted">{new Date(ev.ts).toLocaleTimeString("zh-TW", { hour12: false })}</span>
            <span className="min-w-0 break-words">
              <span className="text-muted">[{ev.type}{ev.stage ? ` · ${stageLabel(ev.stage).split(" / ")[0]}` : ""}] </span>
              {ev.message}
              {ev.data && Object.keys(ev.data).length > 0 ? (
                <details className="mt-0.5">
                  <summary className="cursor-pointer text-muted">data</summary>
                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap">{JSON.stringify(ev.data, null, 1)}</pre>
                </details>
              ) : null}
            </span>
          </div>
        ))}
        <div ref={bottom} />
      </div>
    </div>
  );
}
