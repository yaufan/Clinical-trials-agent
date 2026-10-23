"use client";

import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { enumLabel } from "@/lib/labels";
import type { ProtocolInput } from "@/lib/types";

function Row({ k, v }: { k: string; v: string | number | null | undefined | string[] }) {
  const text = Array.isArray(v) ? (v.length ? v.join("; ") : "—") : v === null || v === undefined || v === "" ? "—" : String(v);
  return (
    <div className="grid grid-cols-3 gap-2 border-b border-border py-1.5 text-sm last:border-0">
      <dt className="text-muted">{k}</dt>
      <dd className="col-span-2 break-words">{text}</dd>
    </div>
  );
}

export function StepReview({ input, name, onNameChange }: { input: ProtocolInput; name: string; onNameChange: (v: string) => void }) {
  const d = input.device_profile;
  const a = input.ai_specifications;
  const s = input.study_design;
  const t = input.statistical_assumptions;
  return (
    <div className="space-y-5">
      <Field label="專案名稱 Project name" required>
        <Input value={name} onChange={(e) => onNameChange(e.target.value)} placeholder={`${d.device_name} — ${s.design_type}`} />
      </Field>
      <div className="grid gap-5 lg:grid-cols-2">
        <section>
          <h3 className="mb-2 text-sm font-semibold">1. 產品與法規 Device & regulatory</h3>
          <dl>
            <Row k="產品 Device" v={`${d.device_name} ${d.version}`} />
            <Row k="分類 Category" v={enumLabel("samd_category", d.samd_category)} />
            <Row k="市場 Jurisdictions" v={d.target_jurisdictions.map((j) => enumLabel("jurisdiction", j))} />
            <Row k="產品代碼 Product code" v={d.product_code} />
            <Row k="同類產品 Predicates" v={d.predicate_devices} />
            <Row k="目標疾病 Disease" v={d.indications_for_use.target_disease} />
            <Row k="族群 Population" v={d.indications_for_use.target_population} />
            <Row k="情境 Setting" v={d.indications_for_use.clinical_setting} />
            <Row k="臨床角色 Role" v={enumLabel("clinical_role", d.indications_for_use.clinical_role)} />
          </dl>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-semibold">2. AI 規格 AI specifications</h3>
          <dl>
            <Row k="演算法 Algorithm" v={enumLabel("algorithm_type", a.algorithm_type)} />
            <Row k="輸入 Input" v={a.input_modality} />
            <Row k="品質要求 Quality" v={a.input_quality_requirements} />
            <Row k="輸出 Output" v={a.output_format.map((o) => enumLabel("output_format", o))} />
            <Row k="使用者 User" v={a.intended_user} />
            <Row k="工作流程 Workflow" v={enumLabel("human_ai_workflow", a.human_ai_workflow)} />
            <Row k="訓練案例 Training n" v={a.training_data_summary.n_training_cases} />
          </dl>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-semibold">3. 試驗設計 Study design</h3>
          <dl>
            <Row k="設計 Design" v={enumLabel("design_type", s.design_type)} />
            <Row k="資料收集 Collection" v={enumLabel("data_collection_mode", s.data_collection_mode)} />
            <Row k="中心數 Sites" v={`${s.study_sites_count} (${s.site_countries.join(", ") || "—"})`} />
            <Row k="抽樣 Sampling" v={enumLabel("sampling_strategy", s.sampling_strategy)} />
            <Row k="盛行率 Prevalence" v={`study ${s.target_prevalence_in_study ?? "—"} / population ${s.population_prevalence ?? "—"}`} />
            <Row k="MRMC" v={s.mrmc_config ? `${s.mrmc_config.total_readers} readers, washout ${s.mrmc_config.washout_period_weeks} wk, ${enumLabel("reading_design", s.mrmc_config.reading_design)}` : "—"} />
            <Row k="參考標準 Reference" v={`${enumLabel("reference_standard_type", s.ground_truth_method.reference_standard_type)}${s.ground_truth_method.panel_size ? ` (n=${s.ground_truth_method.panel_size})` : ""}`} />
            <Row k="納入 Inclusion" v={s.inclusion_criteria} />
            <Row k="排除 Exclusion" v={s.exclusion_criteria} />
            <Row k="分層 Subgroups" v={s.subgroup_stratification} />
          </dl>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-semibold">4. 統計 Statistics</h3>
          <dl>
            <Row k="主要指標 Primary" v={t.primary_endpoints.map((e) => enumLabel("primary_endpoint", e))} />
            <Row k="假設 Hypothesis" v={enumLabel("hypothesis_type", t.hypothesis_type)} />
            <Row k="敏感度 Sens (P₁ vs P₀)" v={t.expected_sensitivity !== null && t.expected_sensitivity !== undefined ? `${t.expected_sensitivity} vs ${t.sensitivity_goal}` : "—"} />
            <Row k="特異度 Spec (P₁ vs P₀)" v={t.expected_specificity !== null && t.expected_specificity !== undefined ? `${t.expected_specificity} vs ${t.specificity_goal}` : "—"} />
            <Row k="AUC" v={t.expected_auc !== null && t.expected_auc !== undefined ? `${t.expected_auc} vs ${t.auc_goal}` : "—"} />
            <Row k="ΔAUC (MRMC)" v={t.mrmc_effect_size_delta_auc} />
            <Row k="α / power" v={`${t.alpha} (${enumLabel("alpha_sidedness", t.alpha_sidedness)}) / ${t.power}`} />
            <Row k="退件率 Attrition" v={t.expected_attrition_rate} />
            <Row k="先導變異成分 Pilot VC" v={t.pilot_variance_components ? "provided" : "—"} />
          </dl>
        </section>
      </div>
      <details className="rounded-md border border-border bg-surface-2 p-3 text-xs">
        <summary className="cursor-pointer font-medium">送出的 JSON (ProtocolInput)</summary>
        <pre className="mt-2 max-h-80 overflow-auto font-mono">{JSON.stringify(input, null, 2)}</pre>
      </details>
    </div>
  );
}
