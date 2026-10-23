"use client";

import { AlertTriangle, Ban, Cpu, RefreshCw, Wrench } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { api, ApiError, TERMINAL_STAGES } from "@/lib/api";
import { stageLabel } from "@/lib/labels";
import type { EvidenceConfirmation, Project } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { AuditView } from "./audit-view";
import { SectionEditor } from "./editor";
import { EventLog } from "./event-log";
import { EvidencePanel } from "./evidence-panel";
import { ExportView } from "./export-view";
import { SapView } from "./sap-view";
import { StageStepper } from "./stage-stepper";
import { TriageView } from "./triage-view";
import { useRun } from "./use-run";

export function RunWorkspace({ runId }: { runId: string }) {
  const { run, setRun, events, error, connected, refresh } = useRun(runId);
  const [project, setProject] = useState<Project | null>(null);
  const [tab, setTab] = useState<string>("protocol");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (run?.project_id && !project) {
      api.getProject(run.project_id).then(setProject).catch(() => undefined);
    }
  }, [run?.project_id, project]);

  // land on the most useful tab for the current stage
  useEffect(() => {
    if (!run) return;
    if (run.stage === "awaiting_evidence_confirmation") setTab("evidence");
    else if (run.stage === "completed" && tab === "evidence") setTab("protocol");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.stage]);

  async function act<T>(fn: () => Promise<T>) {
    setBusy(true);
    setActionError(null);
    try {
      return await fn();
    } catch (e) {
      setActionError(e instanceof ApiError ? `${e.status}: ${e.message}` : (e as Error).message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  if (error && !run) {
    return (
      <Alert tone="danger" title="無法載入執行狀態 / failed to load run">
        {error} — <Link href="/" className="underline">回專案列表 back to projects</Link>
      </Alert>
    );
  }
  if (!run) return <div className="text-sm text-muted">載入中… Loading run…</div>;

  const terminal = TERMINAL_STAGES.has(run.stage);
  const hitl = run.stage === "awaiting_evidence_confirmation";
  const hasSections = run.sections.length > 0;

  const tabs = [
    { id: "protocol", label: "計畫書 Protocol", badge: hasSections ? <Badge className="text-[10px]">{run.sections.length}</Badge> : undefined },
    { id: "evidence", label: "實證矩陣 Evidence", badge: hitl ? <Badge tone="warning" className="text-[10px]">待確認</Badge> : undefined },
    { id: "sap", label: "統計分析計畫 SAP" },
    { id: "audit", label: "合規審查 Audit", badge: run.audits.length ? <Badge tone={run.audits[run.audits.length - 1].n_fail ? "danger" : "success"} className="text-[10px]">{run.audits[run.audits.length - 1].n_fail} fail</Badge> : undefined },
    { id: "triage", label: "法規路徑 Triage" },
    { id: "export", label: "匯出 Export" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs text-muted">
            <Link href="/" className="hover:underline">專案 Projects</Link> / {project?.name ?? run.project_id}
          </div>
          <h1 className="text-xl font-semibold">{project?.input.device_profile.device_name ?? "Protocol run"} <span className="text-muted">· {project?.input.study_design.design_type}</span></h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
            <Badge tone={run.stage === "completed" ? "success" : run.stage === "failed" ? "danger" : hitl ? "warning" : "info"}>{stageLabel(run.stage)}</Badge>
            <span>run {run.run_id.slice(0, 8)}</span>
            <span>建立 {formatDate(run.created_at)}</span>
            <span>更新 {formatDate(run.updated_at)}</span>
            <span className="inline-flex items-center gap-1"><Cpu size={12} /> LLM calls {run.llm_calls}</span>
            <span className="inline-flex items-center gap-1"><Wrench size={12} /> tool calls {run.tool_calls}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => void refresh()} disabled={busy}>
            <RefreshCw size={14} /> 重新整理
          </Button>
          {!terminal ? (
            <Button
              variant="danger"
              size="sm"
              disabled={busy}
              onClick={() => void act(async () => setRun(await api.cancelRun(run.run_id)))}
            >
              <Ban size={14} /> 取消 Cancel
            </Button>
          ) : null}
          {terminal && project ? (
            <Button size="sm" disabled={busy} onClick={() => void act(async () => { const r = await api.startRun(project.id); window.location.href = `/runs/${r.run_id}`; })}>
              重新執行 Re-run
            </Button>
          ) : null}
        </div>
      </div>

      <Card>
        <CardBody>
          <StageStepper stage={run.stage} error={run.error} />
        </CardBody>
      </Card>

      {run.error ? (
        <Alert tone="danger" title="執行錯誤 Run error">{run.error}</Alert>
      ) : null}
      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}
      {run.warnings.length ? (
        <Alert tone="warning" title={`警示 Warnings (${run.warnings.length})`}>
          <ul className="list-disc pl-4">
            {run.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_22rem]">
        <Card className="min-w-0">
          <CardHeader
            title={<Tabs items={tabs} value={tab} onChange={setTab} className="-mb-4 border-0" />}
            className="pb-0"
          />
          <CardBody>
            {tab === "protocol" ? (
              hasSections ? (
                <SectionEditor
                  sections={run.sections}
                  busy={busy}
                  onSave={async (key, markdown) => {
                    await act(async () => setRun(await api.saveSection(run.run_id, key, { markdown, editor: "user" })));
                  }}
                />
              ) : (
                <p className="text-sm text-muted">
                  {hitl ? "請先於「實證矩陣」分頁確認實證。Confirm the evidence first." : terminal ? "本次執行未產生章節。No sections were produced." : "章節將於「計畫書章節草擬」階段產生… Sections appear during the writing stage."}
                </p>
              )
            ) : null}
            {tab === "evidence" ? (
              run.evidence ? (
                <EvidencePanel
                  key={`${run.evidence.confirmed}-${run.evidence.items.length}`}
                  evidence={run.evidence}
                  readOnly={!hitl}
                  busy={busy}
                  onConfirm={(c: EvidenceConfirmation) => void act(async () => setRun(await api.confirmEvidence(run.run_id, c)))}
                />
              ) : (
                <p className="text-sm text-muted">實證檢索尚未完成… Evidence harvest has not completed yet.</p>
              )
            ) : null}
            {tab === "sap" ? (run.sap ? <SapView sap={run.sap} /> : <p className="text-sm text-muted">統計分析計畫尚未產生… SAP not available yet.</p>) : null}
            {tab === "audit" ? <AuditView audits={run.audits} /> : null}
            {tab === "triage" ? (run.triage ? <TriageView triage={run.triage} /> : <p className="text-sm text-muted">法規路徑解析尚未完成… Triage pending.</p>) : null}
            {tab === "export" ? <ExportView runId={run.run_id} disabled={!hasSections} /> : null}
          </CardBody>
        </Card>

        <Card className="xl:sticky xl:top-4 xl:h-[calc(100vh-2rem)]">
          <CardBody className="flex h-full flex-col">
            <EventLog events={events} connected={connected} className="flex-1" />
            {hitl ? (
              <div className="mt-2 flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-2 text-xs">
                <AlertTriangle size={14} className="mt-0.5 text-warning" />
                等待人工確認實證 — 流程暫停中。Pipeline paused for evidence confirmation.
              </div>
            ) : null}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
