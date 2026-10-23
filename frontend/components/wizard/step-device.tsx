"use client";

import { Fieldset } from "@/components/ui/field";
import { L } from "@/lib/labels";
import { CLINICAL_ROLES, JURISDICTIONS, OUTPUT_LANGUAGES, SAMD_CATEGORIES } from "@/lib/types";
import { CheckboxGroup, type Form, SelectField, TextAreaField, TextField } from "./fields";

export function StepDevice({ form }: { form: Form }) {
  return (
    <div className="space-y-5">
      <Fieldset legend="專案資訊 Project">
        <TextField form={form} name="project_meta.sponsor" label="試驗委託者 Sponsor" />
        <TextField form={form} name="project_meta.principal_investigator" label="計畫主持人 Principal investigator" />
        <TextField form={form} name="project_meta.protocol_id" label="計畫書編號 Protocol ID" />
        <SelectField form={form} name="project_meta.output_language" label="輸出語言 Output language" options={OUTPUT_LANGUAGES} labels={L.output_language} />
      </Fieldset>

      <Fieldset legend="產品基本資料 Device profile">
        <TextField form={form} name="device_profile.device_name" label="產品名稱 Device name" required placeholder="NeuroDetect-CT AI" />
        <TextField form={form} name="device_profile.version" label="型號 / 版本 Version" required placeholder="v2.1.0" hint="SPIRIT-AI 11a(i)：須明確標示演算法版本" />
        <TextField form={form} name="device_profile.manufacturer" label="製造商 Manufacturer" />
        <SelectField form={form} name="device_profile.samd_category" label="SaMD 功能分類 Category" required options={SAMD_CATEGORIES} labels={L.samd_category} />
        <TextField form={form} name="device_profile.risk_class" label="風險等級 Risk class" placeholder="TFDA Class II / FDA Class II" />
        <TextField form={form} name="device_profile.product_code" label="FDA 產品代碼 Product code" placeholder="QAS" hint="用於 openFDA 同類產品檢索 / used for predicate search" />
        <CheckboxGroup form={form} name="device_profile.target_jurisdictions" label="目標法規市場 Target jurisdictions" required options={JURISDICTIONS} labels={L.jurisdiction} columns={3} />
        <TextAreaField form={form} name="device_profile.predicate_devices_text" label="同類 / 參考產品編號 Predicate devices" hint="每行一個 K 或 DEN 編號 / one K- or DEN-number per line, e.g. K180647" className="md:col-span-2" rows={2} />
      </Fieldset>

      <Fieldset legend="適應症與預期用途 Indications for use">
        <TextField form={form} name="device_profile.indications_for_use.target_disease" label="目標疾病 / 病灶 Target disease" required placeholder="Acute intracranial hemorrhage (ICH)" />
        <TextField form={form} name="device_profile.indications_for_use.target_population" label="目標族群 Target population" required placeholder="Adults ≥ 20 years with suspected head trauma or stroke" />
        <TextField form={form} name="device_profile.indications_for_use.clinical_setting" label="臨床情境 Clinical setting" required placeholder="Emergency department and radiology department" />
        <SelectField form={form} name="device_profile.indications_for_use.clinical_role" label="臨床角色 Clinical role (STARD-AI)" options={CLINICAL_ROLES} labels={L.clinical_role} hint="取代 / 輔助加值 / 分流 — 決定試驗設計與比較對象" />
        <TextAreaField form={form} name="device_profile.indications_for_use.contraindications_or_limitations" label="禁忌症 / 限制 Limitations" className="md:col-span-2" rows={2} />
      </Fieldset>
    </div>
  );
}
