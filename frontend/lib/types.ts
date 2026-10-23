/**
 * TypeScript mirror of backend/app/schemas/protocol_input.py and backend/app/schemas/run.py.
 * Field names are kept identical to the pydantic models.
 */

// ── ProtocolInput enums ──────────────────────────────────────────────────────
export const SAMD_CATEGORIES = ["CADe", "CADx", "CADt", "CADe_CADx", "Prognostic_Predictive", "Other"] as const;
export type SamdCategory = (typeof SAMD_CATEGORIES)[number];

export const JURISDICTIONS = ["TFDA", "US_FDA_510k", "US_FDA_DeNovo", "US_FDA_PMA", "CE_MDR", "Other"] as const;
export type Jurisdiction = (typeof JURISDICTIONS)[number];

export const CLINICAL_ROLES = ["Replace", "Add_on", "Triage"] as const;
export type ClinicalRole = (typeof CLINICAL_ROLES)[number];

export const ALGORITHM_TYPES = ["Locked", "Adaptive_PCCP"] as const;
export type AlgorithmType = (typeof ALGORITHM_TYPES)[number];

export const OUTPUT_FORMATS = [
  "Bounding_Box",
  "Segmentation_Mask",
  "Heatmap",
  "Probability_Score",
  "Binary_Classification",
  "Triage_Alert",
  "Risk_Score",
  "Measurement",
] as const;
export type OutputFormat = (typeof OUTPUT_FORMATS)[number];

export const HUMAN_AI_WORKFLOWS = ["Standalone_No_Human", "Concurrent_Reader", "Second_Reader", "Worklist_Triage"] as const;
export type HumanAIWorkflow = (typeof HUMAN_AI_WORKFLOWS)[number];

export const DESIGN_TYPES = [
  "Standalone_Performance",
  "MRMC_Reader_Study",
  "Hybrid_Standalone_and_MRMC",
  "Prospective_Interventional_RCT",
] as const;
export type DesignType = (typeof DESIGN_TYPES)[number];

export const DATA_COLLECTION_MODES = ["Retrospective", "Prospective", "Ambispective"] as const;
export type DataCollectionMode = (typeof DATA_COLLECTION_MODES)[number];

export const SAMPLING_STRATEGIES = ["Consecutive", "Random", "Enriched_Case_Control"] as const;
export type SamplingStrategy = (typeof SAMPLING_STRATEGIES)[number];

export const READING_DESIGNS = ["Fully_Crossed", "Split_Plot"] as const;
export type ReadingDesign = (typeof READING_DESIGNS)[number];

export const READING_PARADIGMS = ["Concurrent", "Second_Reader", "Sequential_Unaided_Then_Aided"] as const;
export type ReadingParadigm = (typeof READING_PARADIGMS)[number];

export const REFERENCE_STANDARD_TYPES = [
  "Expert_Consensus_Panel",
  "Pathology_Biopsy",
  "Follow_up_Imaging_Clinical_Outcome",
  "Composite",
] as const;
export type ReferenceStandardType = (typeof REFERENCE_STANDARD_TYPES)[number];

export const PRIMARY_ENDPOINTS = [
  "Sensitivity",
  "Specificity",
  "AUROC",
  "FROC_AFROC",
  "Dice_Score",
  "Reader_Time_Reduction",
  "Time_To_Notification",
  "PPV",
  "NPV",
] as const;
export type PrimaryEndpoint = (typeof PRIMARY_ENDPOINTS)[number];

export const HYPOTHESIS_TYPES = ["Superiority", "Non_Inferiority", "Performance_Goal_Comparison"] as const;
export type HypothesisType = (typeof HYPOTHESIS_TYPES)[number];

export const OUTPUT_LANGUAGES = ["zh-TW", "en", "bilingual"] as const;
export type OutputLanguage = (typeof OUTPUT_LANGUAGES)[number];

export const ALPHA_SIDEDNESS = ["one_sided", "two_sided"] as const;
export type AlphaSidedness = (typeof ALPHA_SIDEDNESS)[number];

// ── ProtocolInput ────────────────────────────────────────────────────────────
export interface IndicationsForUse {
  target_disease: string;
  target_population: string;
  clinical_setting: string;
  clinical_role: ClinicalRole;
  contraindications_or_limitations?: string | null;
}

export interface DeviceProfile {
  device_name: string;
  version: string;
  manufacturer?: string | null;
  samd_category: SamdCategory;
  target_jurisdictions: Jurisdiction[];
  risk_class?: string | null;
  product_code?: string | null;
  predicate_devices: string[];
  indications_for_use: IndicationsForUse;
}

export interface TrainingDataSummary {
  n_training_cases?: number | null;
  training_sites?: string | null;
  independence_statement: string;
}

export interface AISpecifications {
  algorithm_type: AlgorithmType;
  model_description?: string | null;
  input_modality: string;
  input_quality_requirements?: string | null;
  compatible_acquisition_devices?: string | null;
  output_format: OutputFormat[];
  operating_point_description?: string | null;
  intended_user: string;
  human_ai_workflow: HumanAIWorkflow;
  training_data_summary: TrainingDataSummary;
}

export interface MRMCConfig {
  total_readers: number;
  reader_specialty_and_experience?: string | null;
  washout_period_weeks: number;
  reading_design: ReadingDesign;
  reading_paradigm: ReadingParadigm;
}

export interface GroundTruthMethod {
  reference_standard_type: ReferenceStandardType;
  panel_details?: string | null;
  panel_size?: number | null;
  adjudicators_blinded_to_ai: boolean;
}

export interface StudyDesign {
  design_type: DesignType;
  data_collection_mode: DataCollectionMode;
  study_sites_count: number;
  site_countries: string[];
  sampling_strategy: SamplingStrategy;
  target_prevalence_in_study?: number | null;
  population_prevalence?: number | null;
  mrmc_config?: MRMCConfig | null;
  ground_truth_method: GroundTruthMethod;
  inclusion_criteria: string[];
  exclusion_criteria: string[];
  subgroup_stratification: string[];
}

export interface PilotVarianceComponents {
  var_treatment_reader: number;
  var_error: number;
  cov1: number;
  cov2: number;
  cov3: number;
  pilot_cases: number;
}

export interface StatisticalAssumptions {
  primary_endpoints: PrimaryEndpoint[];
  secondary_endpoints: string[];
  hypothesis_type: HypothesisType;
  expected_sensitivity?: number | null;
  sensitivity_goal?: number | null;
  expected_specificity?: number | null;
  specificity_goal?: number | null;
  expected_auc?: number | null;
  auc_goal?: number | null;
  mrmc_effect_size_delta_auc?: number | null;
  pilot_variance_components?: PilotVarianceComponents | null;
  non_inferiority_margin?: number | null;
  alpha: number;
  alpha_sidedness: AlphaSidedness;
  power: number;
  expected_attrition_rate: number;
}

export interface ProjectMeta {
  sponsor?: string | null;
  principal_investigator?: string | null;
  protocol_id?: string | null;
  output_language: OutputLanguage;
}

export interface ProtocolInput {
  project_meta: ProjectMeta;
  device_profile: DeviceProfile;
  ai_specifications: AISpecifications;
  study_design: StudyDesign;
  statistical_assumptions: StatisticalAssumptions;
}

// ── Projects ─────────────────────────────────────────────────────────────────
export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at?: string;
  input: ProtocolInput;
  latest_run?: RunState | null;
  runs?: RunState[];
}

// ── Run state ────────────────────────────────────────────────────────────────
export const RUN_STAGES = [
  "created",
  "triage",
  "harvest",
  "awaiting_evidence_confirmation",
  "biostat",
  "write",
  "audit",
  "completed",
  "failed",
  "cancelled",
] as const;
export type RunStage = (typeof RUN_STAGES)[number];

export type RunEventType =
  | "stage_started"
  | "stage_completed"
  | "progress"
  | "tool_call"
  | "hitl_required"
  | "error"
  | "log"
  | "done"
  | (string & {});

export interface RunEvent {
  ts: string;
  type: RunEventType;
  stage?: RunStage | null;
  message: string;
  data: Record<string, unknown>;
}

export interface TriageDecision {
  study_archetype: string;
  regulatory_pathways: string[];
  applicable_checklists: Array<Record<string, string>>;
  significant_risk_assessment: string;
  key_regulatory_considerations: string[];
  recommended_statistical_framework: string;
  rationale: string;
}

export interface EvidenceItem {
  source: string;
  ref_id: string;
  title: string;
  url?: string | null;
  summary: string;
  design?: string | null;
  sample_size?: string | null;
  readers?: string | null;
  endpoints: string[];
  reported_performance: Record<string, unknown>;
  ground_truth?: string | null;
  eligibility_highlights: string[];
  raw: Record<string, unknown>;
  accepted: boolean;
  user_note?: string | null;
}

export interface BenchmarkRow {
  parameter: string;
  predicate_or_literature_values: string[];
  proposed_value: string;
  justification: string;
}

export interface EvidenceMatrix {
  items: EvidenceItem[];
  benchmark_rows: BenchmarkRow[];
  narrative_summary: string;
  baseline_performance: Record<string, unknown>;
  gaps_and_warnings: string[];
  confirmed: boolean;
  confirmed_at?: string | null;
  reviewer_notes?: string | null;
}

export interface SampleSizeComputation {
  tool: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  interpretation: string;
}

export interface StatisticalAnalysisPlan {
  primary_hypotheses: string[];
  computations: SampleSizeComputation[];
  final_sample_size: Record<string, unknown>;
  stratified_allocation: Record<string, unknown>;
  analysis_methods: string[];
  handling_of_missing_and_indeterminate: string;
  subgroup_analyses: string[];
  sap_markdown: string;
}

export interface DraftSection {
  key: string;
  title_en: string;
  title_zh: string;
  markdown: string;
  citations: string[];
  open_questions: string[];
  revision: number;
  last_edited_by: string;
}

export interface AuditItemResult {
  checklist_id: string;
  item_id: string;
  item_text: string;
  status: "pass" | "partial" | "fail" | "not_applicable" | (string & {});
  evidence_sections: string[];
  finding: string;
  fix_suggestion?: string | null;
}

export interface AuditReport {
  iteration: number;
  checklists_audited: string[];
  items: AuditItemResult[];
  n_pass: number;
  n_partial: number;
  n_fail: number;
  n_not_applicable: number;
  overall_verdict: string;
  revision_requests: Record<string, string[]>;
}

export interface RunState {
  run_id: string;
  project_id: string;
  stage: RunStage;
  created_at: string;
  updated_at: string;
  error?: string | null;
  triage?: TriageDecision | null;
  evidence?: EvidenceMatrix | null;
  sap?: StatisticalAnalysisPlan | null;
  sections: DraftSection[];
  audits: AuditReport[];
  llm_calls: number;
  tool_calls: number;
  warnings: string[];
}

export interface EvidenceConfirmation {
  accepted_ref_ids?: string[] | null;
  item_notes: Record<string, string>;
  reviewer_notes?: string | null;
  baseline_overrides: Record<string, number>;
}

export interface SectionEdit {
  markdown: string;
  editor: string;
}

export interface MetaConfig {
  llm_provider: string;
  llm_model: string;
  mcp_targets: Record<string, string>;
  [key: string]: unknown;
}

/** Mirrors backend SECTION_KEYS: [key, title_en, title_zh]. */
export const SECTION_KEYS: ReadonlyArray<readonly [string, string, string]> = [
  ["synopsis", "1. Protocol Synopsis", "計畫書摘要"],
  ["background", "2. Background, Rationale and Unmet Clinical Need", "研究背景與臨床未滿足需求"],
  ["objectives", "3. Objectives and Hypotheses", "試驗目的與假設"],
  ["device", "4. Investigational Device Description and Human–AI Workflow", "試驗醫材描述與人機協作流程"],
  ["design", "5. Study Design", "整體研究設計"],
  ["eligibility", "6. Subject / Data Eligibility and Sampling Strategy", "受試者與資料納入排除及抽樣策略"],
  ["ground_truth", "7. Reference Standard (Ground Truth) Establishment", "參考標準建立流程"],
  ["statistics", "8. Statistical Analysis Plan and Sample Size", "統計分析計畫與樣本數推算"],
  ["data_management", "9. Data Management, De-identification and Information Security", "資料管理、去識別化與資安規範"],
  ["ethics", "10. Ethical Considerations and IRB / Regulatory Compliance", "倫理考量與人體試驗委員會規範"],
];
