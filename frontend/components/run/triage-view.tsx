import { Badge } from "@/components/ui/badge";
import type { TriageDecision } from "@/lib/types";

export function TriageView({ triage }: { triage: TriageDecision }) {
  return (
    <div className="grid gap-4 text-sm lg:grid-cols-2">
      <div className="space-y-2">
        <div>
          <span className="text-muted">研究類型 Archetype：</span>
          <Badge tone="accent">{triage.study_archetype}</Badge>
        </div>
        <div>
          <span className="text-muted">法規路徑 Pathways：</span>
          {triage.regulatory_pathways.map((p) => (
            <Badge key={p} className="mr-1">
              {p}
            </Badge>
          ))}
        </div>
        <div>
          <span className="text-muted">風險判定 (IRB)：</span>
          {triage.significant_risk_assessment}
        </div>
        <div>
          <span className="text-muted">建議統計架構：</span>
          {triage.recommended_statistical_framework}
        </div>
        <p className="text-muted">{triage.rationale}</p>
      </div>
      <div className="space-y-3">
        <div>
          <div className="mb-1 font-medium">適用查核表 Applicable checklists</div>
          <ul className="space-y-1">
            {triage.applicable_checklists.map((c, i) => (
              <li key={i} className="rounded-md border border-border px-2 py-1">
                <Badge tone={c.role === "primary" ? "success" : c.role === "structural" ? "info" : "neutral"} className="mr-2">
                  {c.role}
                </Badge>
                <span className="font-medium">{c.checklist_id}</span>
                {c.rationale ? <span className="text-muted"> — {c.rationale}</span> : null}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-1 font-medium">關鍵法規考量 Key considerations</div>
          <ul className="list-disc space-y-0.5 pl-5">
            {triage.key_regulatory_considerations.map((k, i) => (
              <li key={i}>{k}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
