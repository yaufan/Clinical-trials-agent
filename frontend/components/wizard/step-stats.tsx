"use client";

import { Alert } from "@/components/ui/alert";
import { Fieldset } from "@/components/ui/field";
import { L } from "@/lib/labels";
import { ALPHA_SIDEDNESS, HYPOTHESIS_TYPES, PRIMARY_ENDPOINTS } from "@/lib/types";
import { CheckboxGroup, type Form, NumberField, SelectField, TextAreaField } from "./fields";

export function StepStats({ form }: { form: Form }) {
  const hyp = form.watch("statistical_assumptions.hypothesis_type");
  const design = form.watch("study_design.design_type");
  const needsMrmc = design === "MRMC_Reader_Study" || design === "Hybrid_Standalone_and_MRMC";
  return (
    <div className="space-y-5">
      <Fieldset legend="評估指標 Endpoints">
        <CheckboxGroup form={form} name="statistical_assumptions.primary_endpoints" label="主要評估指標 Primary endpoints" required options={PRIMARY_ENDPOINTS} labels={L.primary_endpoint} columns={3} />
        <TextAreaField form={form} name="statistical_assumptions.secondary_text" label="次要評估指標 Secondary endpoints" hint="每行一項 / one per line" className="md:col-span-2" rows={3} />
      </Fieldset>

      <Fieldset legend="統計假設 Hypothesis & performance goals">
        <SelectField form={form} name="statistical_assumptions.hypothesis_type" label="假設類型 Hypothesis" required options={HYPOTHESIS_TYPES} labels={L.hypothesis_type} />
        {hyp === "Non_Inferiority" ? (
          <NumberField form={form} name="statistical_assumptions.non_inferiority_margin" label="不劣性界限 NI margin (δ)" required step="0.01" min={0} placeholder="0.05" />
        ) : (
          <div />
        )}
        <NumberField form={form} name="statistical_assumptions.expected_sensitivity" label="預期敏感度 Expected sensitivity (P₁)" step="0.01" min={0} max={1} placeholder="0.92" />
        <NumberField form={form} name="statistical_assumptions.sensitivity_goal" label="敏感度效能目標 Sensitivity goal (P₀)" step="0.01" min={0} max={1} placeholder="0.82" />
        <NumberField form={form} name="statistical_assumptions.expected_specificity" label="預期特異度 Expected specificity (P₁)" step="0.01" min={0} max={1} placeholder="0.90" />
        <NumberField form={form} name="statistical_assumptions.specificity_goal" label="特異度效能目標 Specificity goal (P₀)" step="0.01" min={0} max={1} placeholder="0.80" />
        <NumberField form={form} name="statistical_assumptions.expected_auc" label="預期 AUROC Expected AUC" step="0.01" min={0} max={1} />
        <NumberField form={form} name="statistical_assumptions.auc_goal" label="AUROC 效能目標 AUC goal" step="0.01" min={0} max={1} />
      </Fieldset>

      <Fieldset legend="誤差與檢定力 Error rates & power">
        <NumberField form={form} name="statistical_assumptions.alpha" label="型一誤差 α" required step="0.005" min={0} max={1} hint="FDA 慣例：單尾 0.025 (≙ 雙尾 0.05)" />
        <SelectField form={form} name="statistical_assumptions.alpha_sidedness" label="單尾 / 雙尾 Sidedness" options={ALPHA_SIDEDNESS} labels={L.alpha_sidedness} />
        <NumberField form={form} name="statistical_assumptions.power" label="統計檢定力 Power (1 − β)" required step="0.05" min={0} max={1} />
        <NumberField form={form} name="statistical_assumptions.expected_attrition_rate" label="預期退件 / 不可評估率 Attrition rate" required step="0.01" min={0} max={1} />
      </Fieldset>

      <Fieldset legend={`MRMC 效應量與 OR 模型變異成分 MRMC effect size & pilot variance components ${needsMrmc ? "(MRMC 設計建議填寫)" : "(選填)"}`}>
        <NumberField form={form} name="statistical_assumptions.mrmc_effect_size_delta_auc" label="預期 ΔAUC (AI輔助 − 未輔助) Effect size" step="0.005" min={0} placeholder="0.05" required={needsMrmc} />
        <div className="md:col-span-2">
          <Alert tone="info" title="Obuchowski–Rockette / Hillis 樣本數模型需要先導研究變異成分">
            六個欄位需全部填寫或全部留空；留空時系統將以文獻典型值敏感度分析替代，並在 SAP 標註為假設。Fill all six or none.
          </Alert>
        </div>
        <NumberField form={form} name="statistical_assumptions.pilot.var_treatment_reader" label="σ²_TR (treatment × reader)" step="any" min={0} />
        <NumberField form={form} name="statistical_assumptions.pilot.var_error" label="σ²_ε (error)" step="any" min={0} />
        <NumberField form={form} name="statistical_assumptions.pilot.cov1" label="Cov1 (same reader, diff. modality)" step="any" />
        <NumberField form={form} name="statistical_assumptions.pilot.cov2" label="Cov2 (diff. reader, same modality)" step="any" />
        <NumberField form={form} name="statistical_assumptions.pilot.cov3" label="Cov3 (diff. reader, diff. modality)" step="any" />
        <NumberField form={form} name="statistical_assumptions.pilot.pilot_cases" label="先導研究案例數 Pilot cases" step="1" min={1} />
      </Fieldset>
    </div>
  );
}
