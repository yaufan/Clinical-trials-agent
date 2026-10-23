"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ArrowRight, FlaskConical, Rocket, Wand2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Stepper, type StepperStep } from "@/components/ui/stepper";
import { api, ApiError } from "@/lib/api";
import { type FormValues, STEP_FIELDS, defaultValues, formSchema, fromProtocolInput, toProtocolInput } from "./schema";
import { StepAI } from "./step-ai";
import { StepDesign } from "./step-design";
import { StepDevice } from "./step-device";
import { StepReview } from "./step-review";
import { StepStats } from "./step-stats";

const STEPS = [
  { id: "device", zh: "產品基本與法規定位", en: "Device & Regulatory" },
  { id: "ai", zh: "AI 技術規格與人機互動", en: "AI Specs & Workflow" },
  { id: "design", zh: "臨床試驗設計", en: "Study Design" },
  { id: "stats", zh: "評估指標與統計假設", en: "Endpoints & Statistics" },
  { id: "review", zh: "確認並送出", en: "Review & Submit" },
];

export function Wizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState<"example" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues,
    mode: "onBlur",
  });

  const values = form.watch();
  const reviewInput = useMemo(() => (step === STEPS.length - 1 ? toProtocolInput(values) : null), [step, values]);

  async function next() {
    setError(null);
    const fields = STEP_FIELDS[step];
    const ok = fields ? await form.trigger(fields) : true;
    if (!ok) {
      setError("此步驟仍有欄位未通過驗證，請修正紅字欄位。Some fields need attention.");
      return;
    }
    if (step === STEPS.length - 2) {
      // entering review: validate everything (cross-field rules live in superRefine)
      const all = await form.trigger();
      if (!all) {
        setError("跨欄位驗證未通過（例如 MRMC 判讀者數或效能目標配對），請回到對應步驟修正。Cross-field validation failed.");
        return;
      }
      if (!name) {
        const v = form.getValues();
        setName(`${v.device_profile.device_name} — ${v.study_design.design_type}`);
      }
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  async function loadExample() {
    setBusy("example");
    setError(null);
    try {
      const ex = await api.metaExample();
      form.reset(fromProtocolInput(ex));
      setName(`${ex.device_profile.device_name} — 範例專案 Example`);
    } catch (e) {
      setError(`無法載入範例 / failed to load example: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  async function submit() {
    setBusy("submit");
    setError(null);
    try {
      const ok = await form.trigger();
      if (!ok) throw new Error("表單驗證未通過 / validation failed");
      const input = toProtocolInput(form.getValues());
      const project = await api.createProject(name.trim() || `${input.device_profile.device_name} protocol`, input);
      const run = await api.startRun(project.id);
      router.push(`/runs/${run.run_id}`);
    } catch (e) {
      const msg = e instanceof ApiError ? `${e.status}: ${e.message}` : (e as Error).message;
      setError(`建立專案失敗 / failed: ${msg}`);
      setBusy(null);
    }
  }

  const stepperSteps: StepperStep[] = STEPS.map((s, i) => ({
    id: s.id,
    title: s.zh,
    subtitle: s.en,
    state: i < step ? "done" : i === step ? "current" : "todo",
  }));

  return (
    <div className="space-y-5">
      <Card>
        <CardBody>
          <Stepper steps={stepperSteps} onSelect={(id) => setStep(Math.min(STEPS.findIndex((s) => s.id === id), step))} />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              <FlaskConical size={18} className="text-primary" />
              {`${step + 1}. ${STEPS[step].zh} / ${STEPS[step].en}`}
            </span>
          }
          subtitle="欄位設計對應 SPIRIT-AI / STARD-AI / TFDA 指引要求；* 為必填。Fields map to SPIRIT-AI, STARD-AI and TFDA requirements."
          actions={
            <Button type="button" variant="secondary" size="sm" onClick={loadExample} disabled={busy !== null}>
              <Wand2 size={14} /> 載入範例 Load example
            </Button>
          }
        />
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (step === STEPS.length - 1) void submit();
              else void next();
            }}
            noValidate
          >
            {step === 0 && <StepDevice form={form} />}
            {step === 1 && <StepAI form={form} />}
            {step === 2 && <StepDesign form={form} />}
            {step === 3 && <StepStats form={form} />}
            {step === 4 && reviewInput && <StepReview input={reviewInput} name={name} onNameChange={setName} />}

            {error ? (
              <div className="mt-4">
                <Alert tone="danger">{error}</Alert>
              </div>
            ) : null}

            <div className="mt-6 flex items-center justify-between gap-3">
              <Button type="button" variant="secondary" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0 || busy !== null}>
                <ArrowLeft size={16} /> 上一步 Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button type="submit" disabled={busy !== null}>
                  下一步 Next <ArrowRight size={16} />
                </Button>
              ) : (
                <Button type="submit" disabled={busy !== null || !name.trim()}>
                  <Rocket size={16} /> {busy === "submit" ? "建立中… Creating" : "建立專案並開始生成 Create & run"}
                </Button>
              )}
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
