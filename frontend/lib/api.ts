import type {
  EvidenceConfirmation,
  MetaConfig,
  Project,
  ProtocolInput,
  RunEvent,
  RunState,
  SectionEdit,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const PREFIX = `${API_BASE}/api`;

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${PREFIX}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail: unknown = undefined;
    let message = `${res.status} ${res.statusText}`;
    try {
      detail = await res.json();
      if (detail && typeof detail === "object" && "detail" in detail) {
        const d = (detail as { detail: unknown }).detail;
        message = typeof d === "string" ? d : JSON.stringify(d);
      }
    } catch {
      /* non-JSON body */
    }
    throw new ApiError(res.status, message, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string; [k: string]: unknown }>("/health"),
  metaSchema: () => request<Record<string, unknown>>("/meta/schema"),
  metaExample: () => request<ProtocolInput>("/meta/example"),
  metaConfig: () => request<MetaConfig>("/meta/config"),

  listProjects: () => request<Project[]>("/projects"),
  getProject: (id: string) => request<Project>(`/projects/${encodeURIComponent(id)}`),
  createProject: (name: string, input: ProtocolInput) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name, input }) }),
  updateProject: (id: string, body: { name?: string; input?: ProtocolInput }) =>
    request<Project>(`/projects/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(body) }),

  startRun: (projectId: string) =>
    request<RunState>(`/projects/${encodeURIComponent(projectId)}/runs`, { method: "POST", body: "{}" }),
  listRuns: (projectId: string) => request<RunState[]>(`/projects/${encodeURIComponent(projectId)}/runs`),
  getRun: (id: string) => request<RunState>(`/runs/${encodeURIComponent(id)}`),
  confirmEvidence: (id: string, body: EvidenceConfirmation) =>
    request<RunState>(`/runs/${encodeURIComponent(id)}/confirm-evidence`, { method: "POST", body: JSON.stringify(body) }),
  saveSection: (id: string, key: string, body: SectionEdit) =>
    request<RunState>(`/runs/${encodeURIComponent(id)}/sections/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  cancelRun: (id: string) => request<RunState>(`/runs/${encodeURIComponent(id)}/cancel`, { method: "POST", body: "{}" }),

  exportUrl: (id: string, fmt: "md" | "docx") => `${PREFIX}/runs/${encodeURIComponent(id)}/export.${fmt}`,
  eventsUrl: (id: string) => `${PREFIX}/runs/${encodeURIComponent(id)}/events`,
};

export const TERMINAL_STAGES = new Set(["completed", "failed", "cancelled"]);

/**
 * Subscribe to the run's SSE stream. `onEvent` receives parsed RunEvents; `onDone` fires on the
 * terminal `done` event or when the stream closes. Returns an unsubscribe function.
 */
export function subscribeRunEvents(
  runId: string,
  onEvent: (ev: RunEvent) => void,
  onDone?: () => void,
  onError?: (e: Event) => void,
): () => void {
  if (typeof window === "undefined" || typeof EventSource === "undefined") return () => {};
  const es = new EventSource(api.eventsUrl(runId));
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    es.close();
  };
  const parse = (raw: string): RunEvent | null => {
    try {
      const obj = JSON.parse(raw) as Partial<RunEvent>;
      return {
        ts: obj.ts ?? new Date().toISOString(),
        type: obj.type ?? "log",
        stage: obj.stage ?? null,
        message: obj.message ?? "",
        data: obj.data ?? {},
      };
    } catch {
      return { ts: new Date().toISOString(), type: "log", stage: null, message: raw, data: {} };
    }
  };
  es.onmessage = (m: MessageEvent<string>) => {
    const ev = parse(m.data);
    if (!ev) return;
    onEvent(ev);
    if (ev.type === "done") {
      close();
      onDone?.();
    }
  };
  // Servers may also emit named events (event: done / event: hitl_required …)
  for (const name of ["done", "stage_started", "stage_completed", "progress", "tool_call", "hitl_required", "error", "log"]) {
    es.addEventListener(name, (m) => {
      const ev = parse((m as MessageEvent<string>).data);
      if (!ev) return;
      if (ev.type === "log" && name !== "log") ev.type = name;
      onEvent(ev);
      if (name === "done" || ev.type === "done") {
        close();
        onDone?.();
      }
    });
  }
  es.onerror = (e) => {
    onError?.(e);
    if (es.readyState === EventSource.CLOSED) {
      close();
      onDone?.();
    }
  };
  return close;
}
