"use client";

import { Alert } from "@/components/ui/alert";
import { Fieldset } from "@/components/ui/field";
import { L } from "@/lib/labels";
import { DATA_COLLECTION_MODES, DESIGN_TYPES, READING_DESIGNS, READING_PARADIGMS, REFERENCE_STANDARD_TYPES, SAMPLING_STRATEGIES } from "@/lib/types";
import { type Form, NumberField, SelectField, SwitchField, TextAreaField, TextField } from "./fields";

export function StepDesign({ form }: { form: Form }) {
  const design = form.watch("study_design.design_type");
  const needsMrmc = design === "MRMC_Reader_Study" || design === "Hybrid_Standalone_and_MRMC";
  const isRct = design === "Prospective_Interventional_RCT";
  return (
    <div className="space-y-5">
      <Fieldset legend="試驗類型 Study design">
        <SelectField form={form} name="study_design.design_type" label="試驗設計類型 Design type" required options={DESIGN_TYPES} labels={L.design_type} />
        <SelectField form={form} name="study_design.data_collection_mode" label="資料收集方式 Data collection" required options={DATA_COLLECTION_MODES} labels={L.data_collection_mode} />
        <NumberField form={form} name="study_design.study_sites_count" label="試驗中心數 Sites" required step="1" min={1} />
        <TextAreaField form={form} name="study_design.site_countries_text" label="試驗中心國家 Site countries" hint="每行一個 / one per line" rows={2} />
        <SelectField form={form} name="study_design.sampling_strategy" label="抽樣策略 Sampling" required options={SAMPLING_STRATEGIES} labels={L.sampling_strategy} />
        <NumberField form={form} name="study_design.target_prevalence_in_study" label="試驗資料集陽性比例 Target prevalence in study" step="0.01" min={0} max={1} placeholder="0.40" />
        <NumberField form={form} name="study_design.population_prevalence" label="目標族群盛行率 Population prevalence" step="0.01" min={0} max={1} placeholder="0.12" hint="用於 Buderer 法及連續收案總數推估" />
      </Fieldset>

      <div className="md:col-span-2">
        {isRct ? (
          <Alert tone="info" title="前瞻性介入性試驗 → 適用 SPIRIT-AI / CONSORT-AI">
            系統將以 SPIRIT-AI 15 項 AI 擴充條目為主要查核表。Interventional trials are governed by SPIRIT-AI.
          </Alert>
        ) : (
          <Alert tone="info" title="診斷準確性設計 → 適用 STARD-AI + ISO 14155 Annex A">
            獨立性能驗證與 MRMC 閱片試驗屬診斷準確性研究；SPIRIT-AI 僅作為輔助條目。Standalone and reader studies are diagnostic accuracy designs (STARD-AI).
          </Alert>
        )}
      </div>

      <Fieldset legend={needsMrmc ? "MRMC 閱片試驗設定 Reader study configuration (必填 / required)" : "MRMC 閱片試驗設定 Reader study configuration (選填 / optional)"}>
        <NumberField form={form} name="study_design.mrmc_config.total_readers" label="判讀醫師總數 Total readers" required={needsMrmc} step="1" min={2} placeholder="12" />
        <NumberField form={form} name="study_design.mrmc_config.washout_period_weeks" label="洗脫期 (週) Washout weeks" step="1" min={0} />
        <TextField form={form} name="study_design.mrmc_config.reader_specialty_and_experience" label="判讀者專科與年資 Reader specialty & experience" placeholder="Radiologists, 2–20 years post-board" />
        <SelectField form={form} name="study_design.mrmc_config.reading_design" label="閱片設計 Reading design" options={READING_DESIGNS} labels={L.reading_design} />
        <SelectField form={form} name="study_design.mrmc_config.reading_paradigm" label="閱片模式 Reading paradigm" options={READING_PARADIGMS} labels={L.reading_paradigm} />
      </Fieldset>

      <Fieldset legend="參考標準 / 黃金標準 Reference standard (ground truth)">
        <SelectField form={form} name="study_design.ground_truth_method.reference_standard_type" label="參考標準類型 Type" required options={REFERENCE_STANDARD_TYPES} labels={L.reference_standard_type} />
        <NumberField form={form} name="study_design.ground_truth_method.panel_size" label="判定專家人數 Panel size" step="1" min={1} />
        <TextAreaField form={form} name="study_design.ground_truth_method.panel_details" label="專家資格、共識規則 Panel details" placeholder="3 neuroradiologists (≥10 years), majority vote, blinded to AI output" className="md:col-span-2" rows={2} />
        <div className="md:col-span-2">
          <SwitchField form={form} name="study_design.ground_truth_method.adjudicators_blinded_to_ai" label="判定者對 AI 輸出盲化 Adjudicators blinded to AI output" hint="FDA CADe 指引與 STARD-AI 之要求" />
        </div>
      </Fieldset>

      <Fieldset legend="納入 / 排除條件與分層 Eligibility & stratification">
        <TextAreaField form={form} name="study_design.inclusion_text" label="納入條件 Inclusion criteria" hint="每行一條 / one per line" rows={4} />
        <TextAreaField form={form} name="study_design.exclusion_text" label="排除條件 Exclusion criteria" hint="每行一條；含資料層級排除 (SPIRIT-AI 10(ii))" rows={4} />
        <TextAreaField form={form} name="study_design.subgroup_text" label="次族群分層 Subgroup stratification" hint="每行一項，如：年齡、性別、機台廠牌、病灶大小" className="md:col-span-2" rows={3} />
      </Fieldset>
    </div>
  );
}
