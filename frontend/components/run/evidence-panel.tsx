"use client";

import { CheckCircle2, ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SOURCE_LABELS } from "@/lib/labels";
import type { EvidenceConfirmation, EvidenceItem, EvidenceMatrix } from "@/lib/types";

function perf(p: Record<string, unknown>): string {
  const entries = Object.entries(p ?? {});
  if (!entries.length) return "—";
  return entries
    .slice(0, 6)
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(" · ");
}

export function EvidencePanel({
  evidence,
  readOnly,
  busy,
  onConfirm,
}: {
  evidence: EvidenceMatrix;
  readOnly: boolean;
  busy?: boolean;
  onConfirm?: (c: EvidenceConfirmation) => void;
}) {
  const [accepted, setAccepted] = useState<Record<string, boolean>>(() => Object.fromEntries(evidence.items.map((i) => [i.ref_id, i.accepted])));
  const [notes, setNotes] = useState<Record<string, string>>(() => Object.fromEntries(evidence.items.filter((i) => i.user_note).map((i) => [i.ref_id, i.user_note as string])));
  const [reviewerNotes, setReviewerNotes] = useState(evidence.reviewer_notes ?? "");
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  const grouped = useMemo(() => {
    const g: Record<string, EvidenceItem[]> = {};
    for (const it of evidence.items) (g[it.source] ??= []).push(it);
    return g;
  }, [evidence.items]);

  const nAccepted = Object.values(accepted).filter(Boolean).length;

  function confirm() {
    const baseline_overrides: Record<string, number> = {};
    for (const [k, v] of Object.entries(overrides)) {
      const n = Number(v);
      if (v.trim() && !Number.isNaN(n)) baseline_overrides[k] = n;
    }
    onConfirm?.({
      accepted_ref_ids: Object.entries(accepted)
        .filter(([, v]) => v)
        .map(([k]) => k),
      item_notes: Object.fromEntries(Object.entries(notes).filter(([, v]) => v.trim())),
      reviewer_notes: reviewerNotes.trim() || null,
      baseline_overrides,
    });
  }

  const baselineEntries = Object.entries(evidence.baseline_performance ?? {});

  return (
    <div className="space-y-5">
      {!readOnly ? (
        <Alert tone="warning" title="人工確認 (Human-in-the-loop)：請檢視檢索到的同類產品與文獻，勾選要納入計畫書實證基礎的項目。">
          Review the harvested evidence, untick anything irrelevant, add notes, then confirm to continue to the biostatistics stage.
        </Alert>
      ) : evidence.confirmed ? (
        <Alert tone="success" title={`實證已於 ${evidence.confirmed_at ? new Date(evidence.confirmed_at).toLocaleString("zh-TW", { hour12: false }) : ""} 確認 / Evidence confirmed`}>
          {evidence.reviewer_notes}
        </Alert>
      ) : null}

      {evidence.narrative_summary ? (
        <section>
          <h3 className="mb-1 text-sm font-semibold">摘要 Summary</h3>
          <p className="whitespace-pre-wrap text-sm text-muted">{evidence.narrative_summary}</p>
        </section>
      ) : null}

      {evidence.gaps_and_warnings.length ? (
        <section>
          <h3 className="mb-1 text-sm font-semibold">缺口與警示 Gaps & warnings</h3>
          <ul className="list-disc space-y-0.5 pl-5 text-sm">
            {evidence.gaps_and_warnings.map((g, i) => (
              <li key={i} className="text-warning">
                {g}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {evidence.benchmark_rows.length ? (
        <section>
          <h3 className="mb-2 text-sm font-semibold">同類產品臨床設計基準矩陣 Predicate Benchmark Matrix</h3>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left">
                <tr>
                  <th className="px-3 py-2">參數 Parameter</th>
                  <th className="px-3 py-2">同類產品 / 文獻值 Predicate & literature</th>
                  <th className="px-3 py-2">建議值 Proposed</th>
                  <th className="px-3 py-2">理由 Justification</th>
                </tr>
              </thead>
              <tbody>
                {evidence.benchmark_rows.map((r, i) => (
                  <tr key={i} className="border-t border-border align-top">
                    <td className="px-3 py-2 font-medium">{r.parameter}</td>
                    <td className="px-3 py-2">
                      <ul className="list-disc pl-4">
                        {r.predicate_or_literature_values.map((v, j) => (
                          <li key={j}>{v}</li>
                        ))}
                      </ul>
                    </td>
                    <td className="px-3 py-2 font-semibold text-primary">{r.proposed_value}</td>
                    <td className="px-3 py-2 text-muted">{r.justification}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {baselineEntries.length ? (
        <section>
          <h3 className="mb-2 text-sm font-semibold">基準效能 Baseline performance (文獻 / unaided readers)</h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {baselineEntries.map(([k, v]) => (
              <div key={k} className="rounded-md border border-border px-3 py-2 text-sm">
                <div className="text-xs text-muted">{k}</div>
                <div className="font-mono">{typeof v === "object" ? JSON.stringify(v) : String(v)}</div>
                {!readOnly && typeof v === "number" ? (
                  <Input
                    className="mt-1 h-8 text-xs"
                    type="number"
                    step="any"
                    placeholder="覆寫 override"
                    value={overrides[k] ?? ""}
                    onChange={(e) => setOverrides({ ...overrides, [k]: e.target.value })}
                  />
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="space-y-4">
        <h3 className="text-sm font-semibold">
          檢索項目 Evidence items ({nAccepted}/{evidence.items.length} 納入 accepted)
        </h3>
        {Object.entries(grouped).map(([source, items]) => (
          <div key={source}>
            <div className="mb-1 flex items-center gap-2 text-sm font-medium">
              <Badge tone="info">{SOURCE_LABELS[source] ?? source}</Badge>
              <span className="text-muted">{items.length}</span>
            </div>
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead className="bg-surface-2 text-left">
                  <tr>
                    <th className="w-10 px-2 py-2">納入</th>
                    <th className="px-3 py-2">編號 / 標題 Ref & title</th>
                    <th className="px-3 py-2">設計 Design</th>
                    <th className="px-3 py-2">樣本 / 判讀者 n / readers</th>
                    <th className="px-3 py-2">指標與效能 Endpoints & performance</th>
                    <th className="px-3 py-2">參考標準 Ground truth</th>
                    <th className="px-3 py-2">備註 Note</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.ref_id} className="border-t border-border align-top">
                      <td className="px-2 py-2 text-center">
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-[var(--primary)]"
                          checked={accepted[it.ref_id] ?? true}
                          disabled={readOnly}
                          onChange={(e) => setAccepted({ ...accepted, [it.ref_id]: e.target.checked })}
                        />
                      </td>
                      <td className="max-w-[18rem] px-3 py-2">
                        <div className="font-mono text-xs text-muted">{it.ref_id}</div>
                        <div className="font-medium">{it.title}</div>
                        {it.summary ? <div className="mt-0.5 line-clamp-3 text-xs text-muted">{it.summary}</div> : null}
                        {it.url ? (
                          <a href={it.url} target="_blank" rel="noreferrer" className="mt-0.5 inline-flex items-center gap-1 text-xs text-primary underline">
                            開啟 open <ExternalLink size={11} />
                          </a>
                        ) : null}
                      </td>
                      <td className="px-3 py-2">{it.design ?? "—"}</td>
                      <td className="px-3 py-2">
                        <div>{it.sample_size ?? "—"}</div>
                        {it.readers ? <div className="text-xs text-muted">readers: {it.readers}</div> : null}
                      </td>
                      <td className="max-w-[16rem] px-3 py-2">
                        {it.endpoints.length ? <div className="text-xs">{it.endpoints.join("; ")}</div> : null}
                        <div className="text-xs text-muted">{perf(it.reported_performance)}</div>
                        {it.eligibility_highlights.length ? <div className="mt-0.5 text-xs text-muted">{it.eligibility_highlights.slice(0, 3).join(" · ")}</div> : null}
                      </td>
                      <td className="max-w-[12rem] px-3 py-2 text-xs">{it.ground_truth ?? "—"}</td>
                      <td className="px-3 py-2">
                        {readOnly ? (
                          <span className="text-xs text-muted">{it.user_note ?? notes[it.ref_id] ?? ""}</span>
                        ) : (
                          <Input className="h-8 min-w-[9rem] text-xs" placeholder="note…" value={notes[it.ref_id] ?? ""} onChange={(e) => setNotes({ ...notes, [it.ref_id]: e.target.value })} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
        {evidence.items.length === 0 ? <p className="text-sm text-muted">未檢索到實證項目 / no evidence items were retrieved.</p> : null}
      </section>

      {!readOnly ? (
        <section className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-sm font-medium">審閱者備註 Reviewer notes</span>
            <Textarea value={reviewerNotes} onChange={(e) => setReviewerNotes(e.target.value)} rows={3} placeholder="e.g. 排除 NCT… 因適應症不同；採用 K… 之 MRMC 設計作為主要參考" />
          </label>
          <div className="flex justify-end">
            <Button onClick={confirm} disabled={busy}>
              <CheckCircle2 size={16} /> {busy ? "送出中… Submitting" : "確認實證並繼續 Confirm & continue"}
            </Button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
