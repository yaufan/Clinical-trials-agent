import { z } from "zod";
import {
  ALGORITHM_TYPES,
  ALPHA_SIDEDNESS,
  CLINICAL_ROLES,
  DATA_COLLECTION_MODES,
  DESIGN_TYPES,
  HUMAN_AI_WORKFLOWS,
  HYPOTHESIS_TYPES,
  JURISDICTIONS,
  OUTPUT_FORMATS,
  OUTPUT_LANGUAGES,
  PRIMARY_ENDPOINTS,
  READING_DESIGNS,
  READING_PARADIGMS,
  REFERENCE_STANDARD_TYPES,
  SAMD_CATEGORIES,
  SAMPLING_STRATEGIES,
  type ProtocolInput,
} from "@/lib/types";
import { linesToList, listToLines } from "@/lib/utils";

/** 0 < p < 1, optional (empty input → undefined via setValueAs). */
const prob = z.number({ error: "請輸入 0 到 1 之間的數值 / enter a number between 0 and 1" }).gt(0, "必須大於 0 / must be > 0").lt(1, "必須小於 1 / must be < 1");
const optProb = prob.optional();
const optNum = z.number({ error: "請輸入數值 / enter a number" }).optional();
const reqText = (label: string) => z.string().trim().min(1, `${label}為必填 / required`);
const optText = z.string().trim().optional();

export const formSchema = z
  .object({
    project_meta: z.object({
      sponsor: optText,
      principal_investigator: optText,
      protocol_id: optText,
      output_language: z.enum(OUTPUT_LANGUAGES),
    }),
    device_profile: z.object({
      device_name: reqText("產品名稱 Device name"),
      version: reqText("版本 Version"),
      manufacturer: optText,
      samd_category: z.enum(SAMD_CATEGORIES, { error: "請選擇 SaMD 功能分類 / select a category" }),
      target_jurisdictions: z.array(z.enum(JURISDICTIONS)).min(1, "至少選擇一個目標法規市場 / select at least one jurisdiction"),
      risk_class: optText,
      product_code: optText,
      predicate_devices_text: z.string().optional(),
      indications_for_use: z.object({
        target_disease: reqText("目標疾病 Target disease"),
        target_population: reqText("目標族群 Target population"),
        clinical_setting: reqText("臨床情境 Clinical setting"),
        clinical_role: z.enum(CLINICAL_ROLES),
        contraindications_or_limitations: optText,
      }),
    }),
    ai_specifications: z.object({
      algorithm_type: z.enum(ALGORITHM_TYPES),
      model_description: optText,
      input_modality: reqText("輸入資料模態 Input modality"),
      input_quality_requirements: optText,
      compatible_acquisition_devices: optText,
      output_format: z.array(z.enum(OUTPUT_FORMATS)).min(1, "至少選擇一種輸出形式 / select at least one output"),
      operating_point_description: optText,
      intended_user: reqText("目標使用者 Intended user"),
      human_ai_workflow: z.enum(HUMAN_AI_WORKFLOWS),
      training_data_summary: z.object({
        n_training_cases: z.number().int().positive().optional(),
        training_sites: optText,
        independence_statement: z.string().trim().min(1, "請說明測試資料獨立性 / required"),
      }),
    }),
    study_design: z.object({
      design_type: z.enum(DESIGN_TYPES),
      data_collection_mode: z.enum(DATA_COLLECTION_MODES),
      study_sites_count: z.number({ error: "請輸入試驗中心數 / enter a number" }).int().min(1, "至少 1 個中心 / ≥ 1"),
      site_countries_text: z.string().optional(),
      sampling_strategy: z.enum(SAMPLING_STRATEGIES),
      target_prevalence_in_study: optProb,
      population_prevalence: optProb,
      mrmc_config: z.object({
        total_readers: optNum,
        reader_specialty_and_experience: optText,
        washout_period_weeks: optNum,
        reading_design: z.enum(READING_DESIGNS),
        reading_paradigm: z.enum(READING_PARADIGMS),
      }),
      ground_truth_method: z.object({
        reference_standard_type: z.enum(REFERENCE_STANDARD_TYPES),
        panel_details: optText,
        panel_size: z.number().int().min(1).optional(),
        adjudicators_blinded_to_ai: z.boolean(),
      }),
      inclusion_text: z.string().optional(),
      exclusion_text: z.string().optional(),
      subgroup_text: z.string().optional(),
    }),
    statistical_assumptions: z.object({
      primary_endpoints: z.array(z.enum(PRIMARY_ENDPOINTS)).min(1, "至少選擇一個主要評估指標 / select at least one endpoint"),
      secondary_text: z.string().optional(),
      hypothesis_type: z.enum(HYPOTHESIS_TYPES),
      expected_sensitivity: optProb,
      sensitivity_goal: optProb,
      expected_specificity: optProb,
      specificity_goal: optProb,
      expected_auc: optProb,
      auc_goal: optProb,
      mrmc_effect_size_delta_auc: z.number().min(0).optional(),
      pilot: z.object({
        var_treatment_reader: optNum,
        var_error: optNum,
        cov1: optNum,
        cov2: optNum,
        cov3: optNum,
        pilot_cases: optNum,
      }),
      non_inferiority_margin: z.number().gt(0).optional(),
      alpha: prob,
      alpha_sidedness: z.enum(ALPHA_SIDEDNESS),
      power: prob,
      expected_attrition_rate: z.number({ error: "請輸入數值 / enter a number" }).min(0).lt(1),
    }),
  })
  .superRefine((v, ctx) => {
    const needsMrmc = v.study_design.design_type === "MRMC_Reader_Study" || v.study_design.design_type === "Hybrid_Standalone_and_MRMC";
    if (needsMrmc) {
      const r = v.study_design.mrmc_config.total_readers;
      if (r === undefined || !Number.isInteger(r) || r < 2) {
        ctx.addIssue({ code: "custom", path: ["study_design", "mrmc_config", "total_readers"], message: "MRMC / 混合設計需至少 2 位判讀醫師 / MRMC designs need ≥ 2 readers" });
      }
      const w = v.study_design.mrmc_config.washout_period_weeks;
      if (w !== undefined && (w < 0 || !Number.isInteger(w))) {
        ctx.addIssue({ code: "custom", path: ["study_design", "mrmc_config", "washout_period_weeks"], message: "洗脫期須為 ≥ 0 之整數週數 / integer weeks ≥ 0" });
      }
    }
    const s = v.statistical_assumptions;
    if (s.hypothesis_type === "Performance_Goal_Comparison") {
      if ((s.expected_sensitivity === undefined) !== (s.sensitivity_goal === undefined)) {
        ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "sensitivity_goal"], message: "預期敏感度與敏感度目標需同時填寫 / give expected sensitivity and its goal together" });
      }
      if ((s.expected_specificity === undefined) !== (s.specificity_goal === undefined)) {
        ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "specificity_goal"], message: "預期特異度與特異度目標需同時填寫 / give expected specificity and its goal together" });
      }
      if ((s.expected_auc === undefined) !== (s.auc_goal === undefined)) {
        ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "auc_goal"], message: "預期 AUC 與 AUC 目標需同時填寫 / give expected AUC and its goal together" });
      }
      if (s.expected_sensitivity !== undefined && s.sensitivity_goal !== undefined && s.expected_sensitivity <= s.sensitivity_goal) {
        ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "expected_sensitivity"], message: "預期值必須高於效能目標 / expected value must exceed the goal" });
      }
      if (s.expected_specificity !== undefined && s.specificity_goal !== undefined && s.expected_specificity <= s.specificity_goal) {
        ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "expected_specificity"], message: "預期值必須高於效能目標 / expected value must exceed the goal" });
      }
      if (s.expected_sensitivity === undefined && s.expected_specificity === undefined && s.expected_auc === undefined) {
        ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "expected_sensitivity"], message: "效能目標比較至少需一組 (預期值, 目標) / at least one (expected, goal) pair is required" });
      }
    }
    if (s.hypothesis_type === "Non_Inferiority" && s.non_inferiority_margin === undefined) {
      ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "non_inferiority_margin"], message: "不劣性設計需填寫不劣性界限 / non-inferiority margin required" });
    }
    const p = s.pilot;
    const pilotVals = [p.var_treatment_reader, p.var_error, p.cov1, p.cov2, p.cov3, p.pilot_cases];
    const given = pilotVals.filter((x) => x !== undefined).length;
    if (given > 0 && given < pilotVals.length) {
      ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "pilot", "pilot_cases"], message: "OR 模型變異成分需全部填寫或全部留空 / fill all six pilot components or none" });
    }
    if (needsMrmc && s.mrmc_effect_size_delta_auc === undefined && s.primary_endpoints.includes("AUROC")) {
      ctx.addIssue({ code: "custom", path: ["statistical_assumptions", "mrmc_effect_size_delta_auc"], message: "MRMC 設計以 AUROC 為主要指標時需填寫預期 ΔAUC / ΔAUC effect size required" });
    }
  });

export type FormValues = z.infer<typeof formSchema>;

export const STEP_FIELDS: Array<Array<keyof FormValues>> = [
  ["project_meta", "device_profile"],
  ["ai_specifications"],
  ["study_design"],
  ["statistical_assumptions"],
];

export const defaultValues: FormValues = {
  project_meta: { sponsor: "", principal_investigator: "", protocol_id: "", output_language: "bilingual" },
  device_profile: {
    device_name: "",
    version: "",
    manufacturer: "",
    samd_category: "CADe",
    target_jurisdictions: ["TFDA"],
    risk_class: "",
    product_code: "",
    predicate_devices_text: "",
    indications_for_use: { target_disease: "", target_population: "", clinical_setting: "", clinical_role: "Add_on", contraindications_or_limitations: "" },
  },
  ai_specifications: {
    algorithm_type: "Locked",
    model_description: "",
    input_modality: "",
    input_quality_requirements: "",
    compatible_acquisition_devices: "",
    output_format: [],
    operating_point_description: "",
    intended_user: "",
    human_ai_workflow: "Second_Reader",
    training_data_summary: {
      n_training_cases: undefined,
      training_sites: "",
      independence_statement: "The test dataset is sequestered and independent of all training, tuning and threshold-selection data.",
    },
  },
  study_design: {
    design_type: "Standalone_Performance",
    data_collection_mode: "Retrospective",
    study_sites_count: 1,
    site_countries_text: "Taiwan",
    sampling_strategy: "Enriched_Case_Control",
    target_prevalence_in_study: undefined,
    population_prevalence: undefined,
    mrmc_config: { total_readers: undefined, reader_specialty_and_experience: "", washout_period_weeks: 4, reading_design: "Fully_Crossed", reading_paradigm: "Sequential_Unaided_Then_Aided" },
    ground_truth_method: { reference_standard_type: "Expert_Consensus_Panel", panel_details: "", panel_size: undefined, adjudicators_blinded_to_ai: true },
    inclusion_text: "",
    exclusion_text: "",
    subgroup_text: "",
  },
  statistical_assumptions: {
    primary_endpoints: ["Sensitivity", "Specificity"],
    secondary_text: "PPV\nNPV\nSubgroup consistency",
    hypothesis_type: "Performance_Goal_Comparison",
    expected_sensitivity: undefined,
    sensitivity_goal: undefined,
    expected_specificity: undefined,
    specificity_goal: undefined,
    expected_auc: undefined,
    auc_goal: undefined,
    mrmc_effect_size_delta_auc: undefined,
    pilot: { var_treatment_reader: undefined, var_error: undefined, cov1: undefined, cov2: undefined, cov3: undefined, pilot_cases: undefined },
    non_inferiority_margin: undefined,
    alpha: 0.025,
    alpha_sidedness: "one_sided",
    power: 0.8,
    expected_attrition_rate: 0.1,
  },
};

const nz = (s: string | undefined | null): string | null => (s && s.trim() ? s.trim() : null);
const nu = (n: number | undefined | null): number | null => (n === undefined || n === null || Number.isNaN(n) ? null : n);

export function toProtocolInput(v: FormValues): ProtocolInput {
  const needsMrmc = v.study_design.design_type === "MRMC_Reader_Study" || v.study_design.design_type === "Hybrid_Standalone_and_MRMC";
  const m = v.study_design.mrmc_config;
  const p = v.statistical_assumptions.pilot;
  const pilotComplete = [p.var_treatment_reader, p.var_error, p.cov1, p.cov2, p.cov3, p.pilot_cases].every((x) => x !== undefined);
  return {
    project_meta: {
      sponsor: nz(v.project_meta.sponsor),
      principal_investigator: nz(v.project_meta.principal_investigator),
      protocol_id: nz(v.project_meta.protocol_id),
      output_language: v.project_meta.output_language,
    },
    device_profile: {
      device_name: v.device_profile.device_name,
      version: v.device_profile.version,
      manufacturer: nz(v.device_profile.manufacturer),
      samd_category: v.device_profile.samd_category,
      target_jurisdictions: v.device_profile.target_jurisdictions,
      risk_class: nz(v.device_profile.risk_class),
      product_code: nz(v.device_profile.product_code),
      predicate_devices: linesToList(v.device_profile.predicate_devices_text),
      indications_for_use: {
        target_disease: v.device_profile.indications_for_use.target_disease,
        target_population: v.device_profile.indications_for_use.target_population,
        clinical_setting: v.device_profile.indications_for_use.clinical_setting,
        clinical_role: v.device_profile.indications_for_use.clinical_role,
        contraindications_or_limitations: nz(v.device_profile.indications_for_use.contraindications_or_limitations),
      },
    },
    ai_specifications: {
      algorithm_type: v.ai_specifications.algorithm_type,
      model_description: nz(v.ai_specifications.model_description),
      input_modality: v.ai_specifications.input_modality,
      input_quality_requirements: nz(v.ai_specifications.input_quality_requirements),
      compatible_acquisition_devices: nz(v.ai_specifications.compatible_acquisition_devices),
      output_format: v.ai_specifications.output_format,
      operating_point_description: nz(v.ai_specifications.operating_point_description),
      intended_user: v.ai_specifications.intended_user,
      human_ai_workflow: v.ai_specifications.human_ai_workflow,
      training_data_summary: {
        n_training_cases: nu(v.ai_specifications.training_data_summary.n_training_cases),
        training_sites: nz(v.ai_specifications.training_data_summary.training_sites),
        independence_statement: v.ai_specifications.training_data_summary.independence_statement,
      },
    },
    study_design: {
      design_type: v.study_design.design_type,
      data_collection_mode: v.study_design.data_collection_mode,
      study_sites_count: v.study_design.study_sites_count,
      site_countries: linesToList(v.study_design.site_countries_text),
      sampling_strategy: v.study_design.sampling_strategy,
      target_prevalence_in_study: nu(v.study_design.target_prevalence_in_study),
      population_prevalence: nu(v.study_design.population_prevalence),
      mrmc_config:
        needsMrmc || (m.total_readers !== undefined && m.total_readers >= 2)
          ? {
              total_readers: m.total_readers ?? 2,
              reader_specialty_and_experience: nz(m.reader_specialty_and_experience),
              washout_period_weeks: m.washout_period_weeks ?? 4,
              reading_design: m.reading_design,
              reading_paradigm: m.reading_paradigm,
            }
          : null,
      ground_truth_method: {
        reference_standard_type: v.study_design.ground_truth_method.reference_standard_type,
        panel_details: nz(v.study_design.ground_truth_method.panel_details),
        panel_size: nu(v.study_design.ground_truth_method.panel_size),
        adjudicators_blinded_to_ai: v.study_design.ground_truth_method.adjudicators_blinded_to_ai,
      },
      inclusion_criteria: linesToList(v.study_design.inclusion_text),
      exclusion_criteria: linesToList(v.study_design.exclusion_text),
      subgroup_stratification: linesToList(v.study_design.subgroup_text),
    },
    statistical_assumptions: {
      primary_endpoints: v.statistical_assumptions.primary_endpoints,
      secondary_endpoints: linesToList(v.statistical_assumptions.secondary_text),
      hypothesis_type: v.statistical_assumptions.hypothesis_type,
      expected_sensitivity: nu(v.statistical_assumptions.expected_sensitivity),
      sensitivity_goal: nu(v.statistical_assumptions.sensitivity_goal),
      expected_specificity: nu(v.statistical_assumptions.expected_specificity),
      specificity_goal: nu(v.statistical_assumptions.specificity_goal),
      expected_auc: nu(v.statistical_assumptions.expected_auc),
      auc_goal: nu(v.statistical_assumptions.auc_goal),
      mrmc_effect_size_delta_auc: nu(v.statistical_assumptions.mrmc_effect_size_delta_auc),
      pilot_variance_components: pilotComplete
        ? {
            var_treatment_reader: p.var_treatment_reader as number,
            var_error: p.var_error as number,
            cov1: p.cov1 as number,
            cov2: p.cov2 as number,
            cov3: p.cov3 as number,
            pilot_cases: p.pilot_cases as number,
          }
        : null,
      non_inferiority_margin: nu(v.statistical_assumptions.non_inferiority_margin),
      alpha: v.statistical_assumptions.alpha,
      alpha_sidedness: v.statistical_assumptions.alpha_sidedness,
      power: v.statistical_assumptions.power,
      expected_attrition_rate: v.statistical_assumptions.expected_attrition_rate,
    },
  };
}

const u = <T,>(x: T | null | undefined): T | undefined => (x === null ? undefined : x);

export function fromProtocolInput(i: ProtocolInput): FormValues {
  const d = defaultValues;
  const pm = i.project_meta ?? d.project_meta;
  const dp = i.device_profile;
  const ai = i.ai_specifications;
  const sd = i.study_design;
  const st = i.statistical_assumptions;
  const pv = st.pilot_variance_components;
  return {
    project_meta: {
      sponsor: pm.sponsor ?? "",
      principal_investigator: pm.principal_investigator ?? "",
      protocol_id: pm.protocol_id ?? "",
      output_language: pm.output_language ?? "bilingual",
    },
    device_profile: {
      device_name: dp.device_name,
      version: dp.version,
      manufacturer: dp.manufacturer ?? "",
      samd_category: dp.samd_category,
      target_jurisdictions: dp.target_jurisdictions,
      risk_class: dp.risk_class ?? "",
      product_code: dp.product_code ?? "",
      predicate_devices_text: listToLines(dp.predicate_devices),
      indications_for_use: {
        target_disease: dp.indications_for_use.target_disease,
        target_population: dp.indications_for_use.target_population,
        clinical_setting: dp.indications_for_use.clinical_setting,
        clinical_role: dp.indications_for_use.clinical_role ?? "Add_on",
        contraindications_or_limitations: dp.indications_for_use.contraindications_or_limitations ?? "",
      },
    },
    ai_specifications: {
      algorithm_type: ai.algorithm_type,
      model_description: ai.model_description ?? "",
      input_modality: ai.input_modality,
      input_quality_requirements: ai.input_quality_requirements ?? "",
      compatible_acquisition_devices: ai.compatible_acquisition_devices ?? "",
      output_format: ai.output_format,
      operating_point_description: ai.operating_point_description ?? "",
      intended_user: ai.intended_user,
      human_ai_workflow: ai.human_ai_workflow,
      training_data_summary: {
        n_training_cases: u(ai.training_data_summary?.n_training_cases),
        training_sites: ai.training_data_summary?.training_sites ?? "",
        independence_statement: ai.training_data_summary?.independence_statement ?? d.ai_specifications.training_data_summary.independence_statement,
      },
    },
    study_design: {
      design_type: sd.design_type,
      data_collection_mode: sd.data_collection_mode,
      study_sites_count: sd.study_sites_count,
      site_countries_text: listToLines(sd.site_countries ?? ["Taiwan"]),
      sampling_strategy: sd.sampling_strategy ?? "Enriched_Case_Control",
      target_prevalence_in_study: u(sd.target_prevalence_in_study),
      population_prevalence: u(sd.population_prevalence),
      mrmc_config: {
        total_readers: u(sd.mrmc_config?.total_readers),
        reader_specialty_and_experience: sd.mrmc_config?.reader_specialty_and_experience ?? "",
        washout_period_weeks: sd.mrmc_config?.washout_period_weeks ?? 4,
        reading_design: sd.mrmc_config?.reading_design ?? "Fully_Crossed",
        reading_paradigm: sd.mrmc_config?.reading_paradigm ?? "Sequential_Unaided_Then_Aided",
      },
      ground_truth_method: {
        reference_standard_type: sd.ground_truth_method.reference_standard_type,
        panel_details: sd.ground_truth_method.panel_details ?? "",
        panel_size: u(sd.ground_truth_method.panel_size),
        adjudicators_blinded_to_ai: sd.ground_truth_method.adjudicators_blinded_to_ai ?? true,
      },
      inclusion_text: listToLines(sd.inclusion_criteria),
      exclusion_text: listToLines(sd.exclusion_criteria),
      subgroup_text: listToLines(sd.subgroup_stratification),
    },
    statistical_assumptions: {
      primary_endpoints: st.primary_endpoints,
      secondary_text: listToLines(st.secondary_endpoints ?? []),
      hypothesis_type: st.hypothesis_type ?? "Performance_Goal_Comparison",
      expected_sensitivity: u(st.expected_sensitivity),
      sensitivity_goal: u(st.sensitivity_goal),
      expected_specificity: u(st.expected_specificity),
      specificity_goal: u(st.specificity_goal),
      expected_auc: u(st.expected_auc),
      auc_goal: u(st.auc_goal),
      mrmc_effect_size_delta_auc: u(st.mrmc_effect_size_delta_auc),
      pilot: {
        var_treatment_reader: u(pv?.var_treatment_reader),
        var_error: u(pv?.var_error),
        cov1: u(pv?.cov1),
        cov2: u(pv?.cov2),
        cov3: u(pv?.cov3),
        pilot_cases: u(pv?.pilot_cases),
      },
      non_inferiority_margin: u(st.non_inferiority_margin),
      alpha: st.alpha ?? 0.025,
      alpha_sidedness: st.alpha_sidedness ?? "one_sided",
      power: st.power ?? 0.8,
      expected_attrition_rate: st.expected_attrition_rate ?? 0.1,
    },
  };
}
