"use client";

import { useMemo, useState } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import type { AuditReport } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONE: Record<string, Tone> = { pass: "success", partial: "warning", fail: "danger", not_applicable: "neutral" };
const LABEL: Record<string, string> = { pass: "通過 pass", partial: "部分 partial", fail: "未達 fail", not_applicable: "不適用 N/A" };

export function AuditView({ audits }: { audits: AuditReport[] }) {
  const [iteration, setIteration] = useState(audits.length - 1);
  const [filter, setFilter] = useState<string>("all");
  const [checklist, setChecklist] = useState<string>("all");
  const report = audits[iteration] ?? audits[audits.length - 1];

  const items = useMemo(() => {
    if (!report) return [];
    return report.items.filter((it) => (filter === "all" || it.status === filter) && (checklist === "all" || it.checklist_id === checklist));
  }, [report, filter, checklist]);

  if (!report) return <p className="text-sm text-muted">尚無審查結果 / no audit yet.</p>;

  const counts = [
    ["pass", report.n_pass],
    ["partial", report.n_partial],
    ["fail", report.n_fail],
    ["not_applicable", report.n_not_applicable],
  ] as const;

  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="text-muted">迭代 Iteration</span>
          {audits.map((a, i) => (
            <button key={i} onClick={() => setIteration(i)} className={cn("rounded-md border px-2 py-0.5 text-xs", i === iteration ? "border-primary bg-primary/10" : "border-border")}>
              #{a.iteration}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted">查核表</span>
          <select value={checklist} onChange={(e) => setChecklist(e.target.value)} className="h-7 rounded-md border border-border bg-surface px-2 text-xs">
            <option value="all">全部 all</option>
            {report.checklists_audited.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <button onClick={() => setFilter("all")} className={cn("rounded-full border px-2.5 py-0.5 text-xs", filter === "all" ? "border-primary bg-primary/10" : "border-border")}>
            全部 all ({report.items.length})
          </button>
          {counts.map(([k, n]) => (
            <button key={k} onClick={() => setFilter(k)} className={cn("rounded-full", filter === k && "ring-2 ring-primary/40")}>
              <Badge tone={TONE[k]}>
                {LABEL[k]} {n}
              </Badge>
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-md border border-border bg-surface-2 px-3 py-2">
        <span className="font-medium">總評 Verdict：</span>
        {report.overall_verdict}
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 text-left">
            <tr>
              <th className="px-3 py-2">查核表 / 條目</th>
              <th className="px-3 py-2">狀態</th>
              <th className="px-3 py-2">條目內容 Item</th>
              <th className="px-3 py-2">發現 Finding</th>
              <th className="px-3 py-2">建議修正 Fix</th>
              <th className="px-3 py-2">對應章節</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={`${it.checklist_id}-${it.item_id}-${i}`} className="border-t border-border align-top">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">
                  {it.checklist_id} {it.item_id}
                </td>
                <td className="px-3 py-2">
                  <Badge tone={TONE[it.status] ?? "neutral"}>{LABEL[it.status] ?? it.status}</Badge>
                </td>
                <td className="max-w-[20rem] px-3 py-2 text-xs">{it.item_text}</td>
                <td className="max-w-[20rem] px-3 py-2 text-xs text-muted">{it.finding}</td>
                <td className="max-w-[20rem] px-3 py-2 text-xs">{it.fix_suggestion ?? "—"}</td>
                <td className="px-3 py-2 text-xs text-muted">{it.evidence_sections.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {Object.keys(report.revision_requests).length ? (
        <div>
          <h3 className="mb-1 font-semibold">退回 Writer 之修訂要求 Revision requests</h3>
          <ul className="space-y-1">
            {Object.entries(report.revision_requests).map(([sec, fixes]) => (
              <li key={sec} className="rounded-md border border-border px-3 py-2">
                <div className="font-mono text-xs text-muted">{sec}</div>
                <ul className="list-disc pl-5 text-xs">
                  {fixes.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
