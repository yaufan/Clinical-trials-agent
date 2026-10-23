"use client";

import { Fieldset } from "@/components/ui/field";
import { L } from "@/lib/labels";
import { ALGORITHM_TYPES, HUMAN_AI_WORKFLOWS, OUTPUT_FORMATS } from "@/lib/types";
import { CheckboxGroup, type Form, NumberField, SelectField, TextAreaField, TextField } from "./fields";

export function StepAI({ form }: { form: Form }) {
  return (
    <div className="space-y-5">
      <Fieldset legend="演算法 Algorithm">
        <SelectField form={form} name="ai_specifications.algorithm_type" label="演算法類型 Algorithm type" required options={ALGORITHM_TYPES} labels={L.algorithm_type} hint="自適應演算法需搭配 FDA PCCP / TFDA 變更管制說明" />
        <TextField form={form} name="ai_specifications.model_description" label="模型描述 Model description" placeholder="3D convolutional neural network" />
        <TextField form={form} name="ai_specifications.operating_point_description" label="操作點 / 閾值 Operating point" placeholder="Fixed threshold locked prior to validation" hint="STARD-AI：驗證前應鎖定操作點" />
      </Fieldset>

      <Fieldset legend="輸入資料規格 Input requirements (SPIRIT-AI 10(ii), 11a(ii)–(iii))">
        <TextField form={form} name="ai_specifications.input_modality" label="輸入資料模態 Input modality" required placeholder="Non-contrast head CT (DICOM)" />
        <TextField form={form} name="ai_specifications.compatible_acquisition_devices" label="相容採集設備 Compatible devices" placeholder="GE, Siemens, Philips multi-detector CT" />
        <TextAreaField form={form} name="ai_specifications.input_quality_requirements" label="資料品質要求與低品質排除機制 Quality requirements" placeholder="Slice thickness ≤ 5 mm; 512×512 matrix; exclude severe motion/metal artefact" className="md:col-span-2" rows={2} />
      </Fieldset>

      <Fieldset legend="輸出與人機互動 Output & human–AI workflow (SPIRIT-AI 11a(iv)–(vi))">
        <CheckboxGroup form={form} name="ai_specifications.output_format" label="輸出結果形式 Model output" required options={OUTPUT_FORMATS} labels={L.output_format} columns={3} />
        <TextField form={form} name="ai_specifications.intended_user" label="目標使用者 Intended user" required placeholder="Board-certified radiologists and emergency physicians" />
        <SelectField form={form} name="ai_specifications.human_ai_workflow" label="介入時機 / 工作流程 Workflow" required options={HUMAN_AI_WORKFLOWS} labels={L.human_ai_workflow} />
      </Fieldset>

      <Fieldset legend="訓練資料與獨立性 Training data & test-set independence (STARD-AI / TFDA)">
        <NumberField form={form} name="ai_specifications.training_data_summary.n_training_cases" label="訓練案例數 Training cases" step="1" min={1} />
        <TextField form={form} name="ai_specifications.training_data_summary.training_sites" label="訓練資料來源機構 Training sites" placeholder="4 hospitals in Taiwan and the US" />
        <TextAreaField form={form} name="ai_specifications.training_data_summary.independence_statement" label="測試資料獨立性聲明 Independence statement" required className="md:col-span-2" rows={2} />
      </Fieldset>
    </div>
  );
}
