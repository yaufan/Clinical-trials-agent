/** Bilingual (zh-TW first) labels for enums and stages. */
import type { RunStage } from "./types";

export const L = {
  samd_category: {
    CADe: "CADe 電腦輔助偵測 / Detection",
    CADx: "CADx 電腦輔助診斷 / Diagnosis",
    CADt: "CADt 電腦輔助分流 / Triage",
    CADe_CADx: "CADe + CADx 偵測與診斷",
    Prognostic_Predictive: "預後/風險預測模型 / Prognostic–Predictive",
    Other: "其他 / Other",
  },
  jurisdiction: {
    TFDA: "台灣 TFDA 查驗登記",
    US_FDA_510k: "美國 FDA 510(k)",
    US_FDA_DeNovo: "美國 FDA De Novo",
    US_FDA_PMA: "美國 FDA PMA",
    CE_MDR: "歐盟 CE MDR",
    Other: "其他 / Other",
  },
  clinical_role: {
    Replace: "取代 / Replace",
    Add_on: "輔助加值 / Add-on",
    Triage: "分流 / Triage",
  },
  algorithm_type: {
    Locked: "鎖定型演算法 / Locked",
    Adaptive_PCCP: "自適應 (PCCP) / Adaptive",
  },
  output_format: {
    Bounding_Box: "邊界框 Bounding box",
    Segmentation_Mask: "分割遮罩 Segmentation mask",
    Heatmap: "熱力圖 Heatmap",
    Probability_Score: "機率分數 Probability score",
    Binary_Classification: "二元分類 Binary classification",
    Triage_Alert: "分流警示 Triage alert",
    Risk_Score: "風險分數 Risk score",
    Measurement: "量測值 Measurement",
  },
  human_ai_workflow: {
    Standalone_No_Human: "獨立運作 Standalone (no human)",
    Concurrent_Reader: "同步判讀 Concurrent reader",
    Second_Reader: "第二判讀 Second reader",
    Worklist_Triage: "工作清單分流 Worklist triage",
  },
  design_type: {
    Standalone_Performance: "獨立性能驗證 Standalone performance",
    MRMC_Reader_Study: "多醫師多案例閱片試驗 MRMC reader study",
    Hybrid_Standalone_and_MRMC: "混合 Standalone + MRMC",
    Prospective_Interventional_RCT: "前瞻性介入性試驗 Prospective interventional (RCT)",
  },
  data_collection_mode: {
    Retrospective: "回溯性 Retrospective",
    Prospective: "前瞻性 Prospective",
    Ambispective: "雙向性 Ambispective",
  },
  sampling_strategy: {
    Consecutive: "連續收案 Consecutive",
    Random: "隨機抽樣 Random",
    Enriched_Case_Control: "富集/病例對照 Enriched case–control",
  },
  reading_design: {
    Fully_Crossed: "完全交叉 Fully crossed",
    Split_Plot: "分割區 Split-plot",
  },
  reading_paradigm: {
    Concurrent: "同步 Concurrent",
    Second_Reader: "第二判讀 Second reader",
    Sequential_Unaided_Then_Aided: "序列 (先無AI再有AI) Sequential",
  },
  reference_standard_type: {
    Expert_Consensus_Panel: "專家共識 Expert consensus panel",
    Pathology_Biopsy: "病理/切片 Pathology / biopsy",
    Follow_up_Imaging_Clinical_Outcome: "追蹤影像/臨床結果 Follow-up outcome",
    Composite: "複合參考標準 Composite",
  },
  primary_endpoint: {
    Sensitivity: "敏感度 Sensitivity",
    Specificity: "特異度 Specificity",
    AUROC: "AUROC",
    FROC_AFROC: "FROC / AFROC",
    Dice_Score: "Dice score",
    Reader_Time_Reduction: "判讀時間縮短 Reader time reduction",
    Time_To_Notification: "通知時間 Time to notification",
    PPV: "陽性預測值 PPV",
    NPV: "陰性預測值 NPV",
  },
  hypothesis_type: {
    Superiority: "優越性 Superiority",
    Non_Inferiority: "不劣性 Non-inferiority",
    Performance_Goal_Comparison: "效能目標比較 Performance goal",
  },
  output_language: {
    "zh-TW": "繁體中文",
    en: "English",
    bilingual: "雙語 Bilingual",
  },
  alpha_sidedness: {
    one_sided: "單尾 One-sided",
    two_sided: "雙尾 Two-sided",
  },
} as const;

export const STAGE_LABELS: Record<RunStage, { zh: string; en: string }> = {
  created: { zh: "已建立", en: "Created" },
  triage: { zh: "法規路徑解析", en: "Regulatory triage" },
  harvest: { zh: "平行實證檢索", en: "Evidence harvest" },
  awaiting_evidence_confirmation: { zh: "實證確認 (人工)", en: "Evidence confirmation" },
  biostat: { zh: "生物統計與樣本數", en: "Biostatistics" },
  write: { zh: "計畫書章節草擬", en: "Protocol writing" },
  audit: { zh: "合規性審查", en: "Compliance audit" },
  completed: { zh: "完成", en: "Completed" },
  failed: { zh: "失敗", en: "Failed" },
  cancelled: { zh: "已取消", en: "Cancelled" },
};

/** Ordered pipeline stages for the stepper (terminal/failure states excluded). */
export const PIPELINE_STAGES: RunStage[] = [
  "triage",
  "harvest",
  "awaiting_evidence_confirmation",
  "biostat",
  "write",
  "audit",
  "completed",
];

export const SOURCE_LABELS: Record<string, string> = {
  clinicaltrials: "ClinicalTrials.gov 臨床試驗",
  openfda: "FDA 510(k) / De Novo 同類產品",
  pubmed: "PubMed 文獻基準",
  regulatory_rag: "法規指引 Regulatory guidance",
};

export function stageLabel(stage: RunStage | string | null | undefined): string {
  if (!stage) return "—";
  const l = STAGE_LABELS[stage as RunStage];
  return l ? `${l.zh} / ${l.en}` : stage;
}

export function enumLabel<T extends keyof typeof L>(group: T, value: string | null | undefined): string {
  if (!value) return "—";
  const m = L[group] as Record<string, string>;
  return m[value] ?? value;
}
