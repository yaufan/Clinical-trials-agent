"use client";

import { Stepper, type StepperStep } from "@/components/ui/stepper";
import { PIPELINE_STAGES, STAGE_LABELS } from "@/lib/labels";
import type { RunStage } from "@/lib/types";

export function StageStepper({ stage, error }: { stage: RunStage; error?: string | null }) {
  const idx = PIPELINE_STAGES.indexOf(stage);
  const failed = stage === "failed" || stage === "cancelled";
  const steps: StepperStep[] = PIPELINE_STAGES.map((s, i) => {
    let state: StepperStep["state"] = "todo";
    if (stage === "completed") state = "done";
    else if (failed) state = i === 0 ? "error" : "todo";
    else if (idx >= 0 && i < idx) state = "done";
    else if (i === idx) state = s === "awaiting_evidence_confirmation" ? "waiting" : "current";
    return { id: s, title: STAGE_LABELS[s].zh, subtitle: STAGE_LABELS[s].en, state };
  });
  if (failed) {
    steps.unshift({ id: stage, title: STAGE_LABELS[stage].zh, subtitle: error ?? STAGE_LABELS[stage].en, state: "error" });
    steps.splice(1);
  }
  return <Stepper steps={steps} />;
}
