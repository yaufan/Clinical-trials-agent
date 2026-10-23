"""The front-end ↔ back-end data contract for a protocol-generation request.

This is the corrected version of the Gemini draft's JSON Schema:
* `predicate_devices` is a list (K/DEN numbers), not a single id;
* a `clinical_role` (replace / add-on / triage) is captured because STARD-AI and the FDA CADe
  guidance key study design on it;
* `training_data_summary` records test-set independence (STARD-AI / TFDA requirement);
* sampling strategy and target prevalence drive the sample-size tools;
* MRMC designs carry pilot variance components (needed by the Obuchowski–Rockette power model);
* `alpha_sidedness` is explicit (FDA convention: one-sided 0.025).

`ProtocolInput.model_json_schema()` is served at GET /api/meta/schema for the wizard.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class SamdCategory(StrEnum):
    CADe = "CADe"
    CADx = "CADx"
    CADt = "CADt"
    CADe_CADx = "CADe_CADx"
    Prognostic_Predictive = "Prognostic_Predictive"
    Other = "Other"


class Jurisdiction(StrEnum):
    TFDA = "TFDA"
    US_FDA_510k = "US_FDA_510k"
    US_FDA_DeNovo = "US_FDA_DeNovo"
    US_FDA_PMA = "US_FDA_PMA"
    CE_MDR = "CE_MDR"
    Other = "Other"


class ClinicalRole(StrEnum):
    Replace = "Replace"
    Add_on = "Add_on"
    Triage = "Triage"


class AlgorithmType(StrEnum):
    Locked = "Locked"
    Adaptive_PCCP = "Adaptive_PCCP"


class OutputFormat(StrEnum):
    Bounding_Box = "Bounding_Box"
    Segmentation_Mask = "Segmentation_Mask"
    Heatmap = "Heatmap"
    Probability_Score = "Probability_Score"
    Binary_Classification = "Binary_Classification"
    Triage_Alert = "Triage_Alert"
    Risk_Score = "Risk_Score"
    Measurement = "Measurement"


class HumanAIWorkflow(StrEnum):
    Standalone_No_Human = "Standalone_No_Human"
    Concurrent_Reader = "Concurrent_Reader"
    Second_Reader = "Second_Reader"
    Worklist_Triage = "Worklist_Triage"


class DesignType(StrEnum):
    Standalone_Performance = "Standalone_Performance"
    MRMC_Reader_Study = "MRMC_Reader_Study"
    Hybrid_Standalone_and_MRMC = "Hybrid_Standalone_and_MRMC"
    Prospective_Interventional_RCT = "Prospective_Interventional_RCT"


class DataCollectionMode(StrEnum):
    Retrospective = "Retrospective"
    Prospective = "Prospective"
    Ambispective = "Ambispective"


class SamplingStrategy(StrEnum):
    Consecutive = "Consecutive"
    Random = "Random"
    Enriched_Case_Control = "Enriched_Case_Control"


class ReadingDesign(StrEnum):
    Fully_Crossed = "Fully_Crossed"
    Split_Plot = "Split_Plot"


class ReadingParadigm(StrEnum):
    Concurrent = "Concurrent"
    Second_Reader = "Second_Reader"
    Sequential_Unaided_Then_Aided = "Sequential_Unaided_Then_Aided"


class ReferenceStandardType(StrEnum):
    Expert_Consensus_Panel = "Expert_Consensus_Panel"
    Pathology_Biopsy = "Pathology_Biopsy"
    Follow_up_Imaging_Clinical_Outcome = "Follow_up_Imaging_Clinical_Outcome"
    Composite = "Composite"


class PrimaryEndpoint(StrEnum):
    Sensitivity = "Sensitivity"
    Specificity = "Specificity"
    AUROC = "AUROC"
    FROC_AFROC = "FROC_AFROC"
    Dice_Score = "Dice_Score"
    Reader_Time_Reduction = "Reader_Time_Reduction"
    Time_To_Notification = "Time_To_Notification"
    PPV = "PPV"
    NPV = "NPV"


class HypothesisType(StrEnum):
    Superiority = "Superiority"
    Non_Inferiority = "Non_Inferiority"
    Performance_Goal_Comparison = "Performance_Goal_Comparison"


class OutputLanguage(StrEnum):
    zh_TW = "zh-TW"
    en = "en"
    bilingual = "bilingual"


Prob = Annotated[float, Field(gt=0, lt=1)]


class IndicationsForUse(BaseModel):
    target_disease: str = Field(examples=["Acute intracranial hemorrhage (ICH)"])
    target_population: str = Field(
        examples=["Adults ≥ 20 years with suspected head trauma or stroke"]
    )
    clinical_setting: str = Field(examples=["Emergency department and radiology department"])
    clinical_role: ClinicalRole = Field(
        default=ClinicalRole.Add_on, description="STARD-AI: replace / add-on / triage"
    )
    contraindications_or_limitations: str | None = None


class DeviceProfile(BaseModel):
    device_name: str = Field(examples=["NeuroDetect-CT AI"])
    version: str = Field(examples=["v2.1.0"])
    manufacturer: str | None = None
    samd_category: SamdCategory
    target_jurisdictions: list[Jurisdiction] = Field(min_length=1)
    risk_class: str | None = Field(default=None, examples=["TFDA Class II / FDA Class II"])
    product_code: str | None = Field(
        default=None, description="FDA product code of the device type, e.g. QAS (triage ICH)"
    )
    predicate_devices: list[str] = Field(
        default_factory=list,
        description="FDA K-numbers / DEN-numbers of predicates or reference devices",
    )
    indications_for_use: IndicationsForUse


class TrainingDataSummary(BaseModel):
    n_training_cases: int | None = None
    training_sites: str | None = None
    independence_statement: str = Field(
        default="The test dataset is sequestered and independent of all training, tuning and threshold-selection data.",
        description="STARD-AI / TFDA: independence of evaluation data from development data",
    )


class AISpecifications(BaseModel):
    algorithm_type: AlgorithmType
    model_description: str | None = Field(
        default=None, examples=["3D convolutional neural network with attention"]
    )
    input_modality: str = Field(examples=["Non-contrast head CT (DICOM)"])
    input_quality_requirements: str | None = Field(
        default=None,
        examples=["Slice thickness ≤ 5 mm; 512×512 matrix; no severe motion or metal artefact"],
    )
    compatible_acquisition_devices: str | None = Field(
        default=None, examples=["GE, Siemens, Philips CT scanners"]
    )
    output_format: list[OutputFormat] = Field(min_length=1)
    operating_point_description: str | None = Field(
        default=None, examples=["Fixed probability threshold 0.5 locked before validation"]
    )
    intended_user: str = Field(examples=["Board-certified radiologists and emergency physicians"])
    human_ai_workflow: HumanAIWorkflow
    training_data_summary: TrainingDataSummary = Field(default_factory=TrainingDataSummary)


class MRMCConfig(BaseModel):
    total_readers: int = Field(ge=2, examples=[12])
    reader_specialty_and_experience: str | None = Field(
        default=None, examples=["Radiologists, 2–20 years post-board"]
    )
    washout_period_weeks: int = Field(ge=0, default=4)
    reading_design: ReadingDesign = ReadingDesign.Fully_Crossed
    reading_paradigm: ReadingParadigm = ReadingParadigm.Sequential_Unaided_Then_Aided


class GroundTruthMethod(BaseModel):
    reference_standard_type: ReferenceStandardType
    panel_details: str | None = Field(
        default=None,
        examples=["Independent adjudication by 3 neuroradiologists (≥10 years) with majority vote"],
    )
    panel_size: int | None = Field(default=None, ge=1)
    adjudicators_blinded_to_ai: bool = True


class StudyDesign(BaseModel):
    design_type: DesignType
    data_collection_mode: DataCollectionMode
    study_sites_count: int = Field(ge=1, examples=[3])
    site_countries: list[str] = Field(default_factory=lambda: ["Taiwan"])
    sampling_strategy: SamplingStrategy = SamplingStrategy.Enriched_Case_Control
    target_prevalence_in_study: Prob | None = Field(
        default=None, description="Expected proportion of positives in the study set"
    )
    population_prevalence: Prob | None = Field(
        default=None, description="Disease prevalence in the intended-use population"
    )
    mrmc_config: MRMCConfig | None = None
    ground_truth_method: GroundTruthMethod
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    subgroup_stratification: list[str] = Field(
        default_factory=list,
        examples=[
            ["Age (20–64 vs ≥65)", "Sex", "Scanner manufacturer", "Lesion size (<10 mm vs ≥10 mm)"]
        ],
    )

    @model_validator(mode="after")
    def _mrmc_requires_config(self) -> StudyDesign:
        if (
            self.design_type
            in (DesignType.MRMC_Reader_Study, DesignType.Hybrid_Standalone_and_MRMC)
            and self.mrmc_config is None
        ):
            raise ValueError("mrmc_config is required for MRMC / hybrid designs")
        return self


class PilotVarianceComponents(BaseModel):
    """Obuchowski–Rockette components from a pilot reader study (same FOM scale as the endpoint)."""

    var_treatment_reader: float = Field(ge=0)
    var_error: float = Field(gt=0)
    cov1: float
    cov2: float
    cov3: float
    pilot_cases: int = Field(gt=0)


class StatisticalAssumptions(BaseModel):
    primary_endpoints: list[PrimaryEndpoint] = Field(min_length=1)
    secondary_endpoints: list[str] = Field(
        default_factory=lambda: ["PPV", "NPV", "Subgroup consistency"]
    )
    hypothesis_type: HypothesisType = HypothesisType.Performance_Goal_Comparison
    expected_sensitivity: Prob | None = Field(default=None, examples=[0.92])
    sensitivity_goal: Prob | None = Field(default=None, examples=[0.82])
    expected_specificity: Prob | None = Field(default=None, examples=[0.90])
    specificity_goal: Prob | None = Field(default=None, examples=[0.80])
    expected_auc: Prob | None = None
    auc_goal: Prob | None = None
    mrmc_effect_size_delta_auc: float | None = Field(default=None, ge=0, examples=[0.05])
    pilot_variance_components: PilotVarianceComponents | None = None
    non_inferiority_margin: float | None = Field(default=None, gt=0)
    alpha: Prob = 0.025
    alpha_sidedness: Annotated[str, Field(pattern="^(one_sided|two_sided)$")] = "one_sided"
    power: Prob = 0.80
    expected_attrition_rate: Annotated[float, Field(ge=0, lt=1)] = 0.10

    @model_validator(mode="after")
    def _goals_match_expectations(self) -> StatisticalAssumptions:
        if (self.expected_sensitivity is None) != (
            self.sensitivity_goal is None
        ) and self.hypothesis_type == HypothesisType.Performance_Goal_Comparison:
            raise ValueError("expected_sensitivity and sensitivity_goal must be given together")
        if (self.expected_specificity is None) != (
            self.specificity_goal is None
        ) and self.hypothesis_type == HypothesisType.Performance_Goal_Comparison:
            raise ValueError("expected_specificity and specificity_goal must be given together")
        return self


class ProjectMeta(BaseModel):
    sponsor: str | None = None
    principal_investigator: str | None = None
    protocol_id: str | None = None
    output_language: OutputLanguage = OutputLanguage.bilingual


class ProtocolInput(BaseModel):
    """Top-level request body (stored on the Project)."""

    project_meta: ProjectMeta = Field(default_factory=ProjectMeta)
    device_profile: DeviceProfile
    ai_specifications: AISpecifications
    study_design: StudyDesign
    statistical_assumptions: StatisticalAssumptions

    model_config = {"json_schema_extra": {"title": "AISaMDProtocolInput"}}


EXAMPLE_INPUT: dict = {
    "project_meta": {
        "sponsor": "Example MedTech Co., Ltd.",
        "principal_investigator": "Dr. Lin",
        "output_language": "bilingual",
    },
    "device_profile": {
        "device_name": "NeuroDetect-CT AI",
        "version": "v2.1.0",
        "manufacturer": "Example MedTech Co., Ltd.",
        "samd_category": "CADt",
        "target_jurisdictions": ["TFDA", "US_FDA_510k"],
        "risk_class": "TFDA Class II / FDA Class II",
        "product_code": "QAS",
        "predicate_devices": ["K180647"],
        "indications_for_use": {
            "target_disease": "Acute intracranial hemorrhage (ICH)",
            "target_population": "Adults ≥ 20 years presenting with suspected head trauma or stroke",
            "clinical_setting": "Emergency department and radiology department",
            "clinical_role": "Triage",
        },
    },
    "ai_specifications": {
        "algorithm_type": "Locked",
        "model_description": "3D convolutional neural network",
        "input_modality": "Non-contrast head CT (DICOM)",
        "input_quality_requirements": "Slice thickness ≤ 5 mm, 512×512 matrix, no severe motion/metal artefact",
        "compatible_acquisition_devices": "GE, Siemens, Philips multi-detector CT",
        "output_format": ["Triage_Alert", "Probability_Score", "Heatmap"],
        "operating_point_description": "Fixed threshold locked prior to validation",
        "intended_user": "Board-certified radiologists and emergency physicians",
        "human_ai_workflow": "Worklist_Triage",
        "training_data_summary": {
            "n_training_cases": 25000,
            "training_sites": "4 hospitals in Taiwan and the US",
        },
    },
    "study_design": {
        "design_type": "Standalone_Performance",
        "data_collection_mode": "Retrospective",
        "study_sites_count": 3,
        "site_countries": ["Taiwan"],
        "sampling_strategy": "Enriched_Case_Control",
        "target_prevalence_in_study": 0.4,
        "population_prevalence": 0.12,
        "ground_truth_method": {
            "reference_standard_type": "Expert_Consensus_Panel",
            "panel_details": "3 neuroradiologists (≥10 years), majority vote, blinded to AI output",
            "panel_size": 3,
        },
        "inclusion_criteria": ["Age ≥ 20 years", "Non-contrast head CT acquired for suspected ICH"],
        "exclusion_criteria": [
            "Severe motion artefact",
            "Post-operative skull defects",
            "Slice thickness > 5 mm",
        ],
        "subgroup_stratification": [
            "Age (20–64 vs ≥65)",
            "Sex",
            "Scanner manufacturer",
            "Hemorrhage subtype",
        ],
    },
    "statistical_assumptions": {
        "primary_endpoints": ["Sensitivity", "Specificity"],
        "hypothesis_type": "Performance_Goal_Comparison",
        "expected_sensitivity": 0.93,
        "sensitivity_goal": 0.80,
        "expected_specificity": 0.92,
        "specificity_goal": 0.80,
        "alpha": 0.025,
        "alpha_sidedness": "one_sided",
        "power": 0.8,
        "expected_attrition_rate": 0.10,
    },
}
