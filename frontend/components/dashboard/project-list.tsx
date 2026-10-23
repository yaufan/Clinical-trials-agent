"use client";

import { FolderPlus, Play, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge, type Tone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { api, API_BASE } from "@/lib/api";
import { enumLabel, stageLabel } from "@/lib/labels";
import type { MetaConfig, Project, RunState } from "@/lib/types";
import { formatDate } from "@/lib/utils";

function toneFor(stage?: string | null): Tone {
  if (!stage) return "neutral";
  if (stage === "completed") return "success";
  if (stage === "failed" || stage === "cancelled") return "danger";
  if (stage === "awaiting_evidence_confirmation") return "warning";
  return "info";
}

function latestRun(p: Project): RunState | null {
  if (p.latest_run) return p.latest_run;
  if (p.runs?.length) return [...p.runs].sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
  return null;
}

export function ProjectList() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [runs, setRuns] = useState<Record<string, RunState | null>>({});
  const [config, setConfig] = useState<MetaConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const list = await api.listProjects();
      setProjects(list);
      // fetch latest run per project when the list endpoint does not embed it
      const missing = list.filter((p) => !latestRun(p));
      const entries = await Promise.all(
        missing.map(async (p) => {
          try {
            const rs = await api.listRuns(p.id);
            const latest = [...rs].sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0] ?? null;
            return [p.id, latest] as const;
          } catch {
            return [p.id, null] as const;
          }
        }),
      );
      setRuns(Object.fromEntries(entries));
    } catch (e) {
      setError(`無法連線後端 (${API_BASE}) / cannot reach the backend: ${(e as Error).message}`);
    }
    api.metaConfig().then(setConfig).catch(() => undefined);
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">專案 Projects</h1>
          <p className="text-sm text-muted">每個專案對應一個 AI-SaMD 產品的臨床試驗計畫書輸入；可重複執行生成。</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => void load()}>
            <RefreshCw size={14} /> 重新整理
          </Button>
          <Link href="/projects/new">
            <Button size="sm">
              <FolderPlus size={14} /> 新建專案 New project
            </Button>
          </Link>
        </div>
      </div>

      {config ? (
        <div className="flex flex-wrap gap-2 text-xs text-muted">
          <Badge tone="accent">LLM: {config.llm_provider} · {config.llm_model}</Badge>
          {Object.keys(config.mcp_targets ?? {}).map((k) => (
            <Badge key={k}>MCP {k}</Badge>
          ))}
        </div>
      ) : null}

      {error ? <Alert tone="danger">{error}</Alert> : null}

      {projects && projects.length === 0 ? (
        <Card>
          <CardBody className="py-10 text-center text-sm text-muted">
            尚無專案。點擊「新建專案」開始四步驟輸入。No projects yet — start with “New project”.
          </CardBody>
        </Card>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(projects ?? []).map((p) => {
          const r = latestRun(p) ?? runs[p.id] ?? null;
          return (
            <Card key={p.id}>
              <CardHeader
                title={p.name}
                subtitle={`${p.input.device_profile.device_name} ${p.input.device_profile.version} · ${enumLabel("samd_category", p.input.device_profile.samd_category)}`}
                actions={<Badge tone={toneFor(r?.stage)}>{r ? stageLabel(r.stage) : "尚未執行 / no run"}</Badge>}
              />
              <CardBody className="space-y-2 text-sm">
                <div className="text-muted">{enumLabel("design_type", p.input.study_design.design_type)}</div>
                <div className="text-xs text-muted">建立 {formatDate(p.created_at)}</div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {r ? (
                    <Link href={`/runs/${r.run_id}`}>
                      <Button size="sm" variant="secondary">開啟最新執行 Open run</Button>
                    </Link>
                  ) : null}
                  <Button
                    size="sm"
                    disabled={busy === p.id}
                    onClick={async () => {
                      setBusy(p.id);
                      try {
                        const run = await api.startRun(p.id);
                        window.location.href = `/runs/${run.run_id}`;
                      } catch (e) {
                        setError((e as Error).message);
                        setBusy(null);
                      }
                    }}
                  >
                    <Play size={14} /> {r ? "重新執行 Re-run" : "開始生成 Run"}
                  </Button>
                </div>
              </CardBody>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
