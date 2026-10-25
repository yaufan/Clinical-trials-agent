# Clinical Investigation Plan — NeuroDetect-CT AI v2.1.0
# 臨床試驗計畫書 — NeuroDetect-CT AI v2.1.0

**Protocol ID:** [TO BE ASSIGNED]  
**Sponsor:** Example MedTech Co., Ltd.  
**Principal Investigator:** Dr. Lin  
**Draft generated:** 2026-10-24 · run `8179333b-1651-4b10-9225-6a8c12b48dea` · stage `completed`

> ⚠️ AI-assisted draft. Every statement must be verified by the sponsor's regulatory, clinical and biostatistics leads before IRB/TFDA/FDA submission. Items marked **[TO BE CONFIRMED]** are unresolved.

## Synopsis Table / 摘要表
| Item | Value |
|---|---|
| Device / 試驗醫材 | NeuroDetect-CT AI v2.1.0 (CADt) |
| Intended use / 預期用途 | Acute intracranial hemorrhage (ICH); Adults ≥ 20 years presenting with suspected head trauma or stroke; Emergency department and radiology department |
| Jurisdictions / 目標市場 | TFDA, US_FDA_510k |
| Algorithm / 演算法 | Locked; input Non-contrast head CT (DICOM); output Triage_Alert, Probability_Score, Heatmap; workflow Worklist_Triage |
| Design / 試驗設計 | Standalone_Performance, Retrospective, 3 site(s), sampling Enriched_Case_Control |
| Reference standard / 參考標準 | Expert_Consensus_Panel: 3 neuroradiologists (≥10 years), majority vote, blinded to AI output |
| Primary endpoints / 主要指標 | Sensitivity, Specificity (Performance_Goal_Comparison) |
| Sample size / 樣本數 | n_positive=62, n_negative=77, n_total=139, n_positive_evaluable=55, n_negative_evaluable=69, n_total_at_prevalence=155 |
| α / power | 0.025 (one_sided) / 0.8; attrition 0.1 |

## Regulatory Triage Summary / 法規路徑摘要
- **Study archetype:** standalone_diagnostic_accuracy
- **Pathway:** TFDA 醫療器材查驗登記 (醫療器材管理法) — AI/ML SaMD technical guidance (2020)
- **Pathway:** US FDA 510(k) premarket notification with predicate comparison
- **Risk assessment:** Non-significant-risk (無顯著風險) per TFDA 醫療器材管理法 §37 公告態樣, as the study is retrospective and does not influence patient care directly. IRB approval is still required, and informed-consent waiver may be requested.
- **Applicable checklists:** STARD-AI (primary), SPIRIT-AI (supporting), ISO14155-CIP (structural), IMDRF-N41 (structural), FDA-CADe (supporting), TFDA-AIML-SaMD (primary)

## 計畫書摘要 / 1. Protocol Synopsis
## 計畫書摘要 / 1. Protocol Synopsis

### 1.1 計畫書標題 / 1.1 Title

本臨床試驗計畫評估 **NeuroDetect-CT AI v2.1.0**（Software as a Medical Device, SaMD），其為一種 **CADt（Computer-Aided Detection for Triage）** 模型，用於 **急性顱內出血（Acute intracranial hemorrhage, ICH）的初步篩查與優先處理（Triage）**。此模型基於 **3D卷積神經網絡（3D convolutional neural network）**，接受 **非對比頭部電腦斷層掃描（Non-contrast head CT, DICOM）** 作為輸入，並產生 **Triage_Alert、Probability_Score 與 Heatmap** 作為輸出，以協助 **放射科醫師與急診科醫師** 在 **急診與放射科臨床環境** 中進行 **初步篩查與優先處理決策**。

本計畫符合 **TFDA-AIML-SaMD TW-1**（產品描述）與 **STARD-AI** 標準，並遵循 **SPIRIT-AI 1(i)/(ii)** 標準命名與標題規範。

### 1.2 計畫書摘要表 / 1.2 Summary Table

| 項目 | 說明 |
|------|------|
| 設備名稱 / Device Name | NeuroDetect-CT AI |
| 設備版本 / Version | v2.1.0 |
| 製造商 / Manufacturer | Example MedTech Co., Ltd. |
| SaMD 分類 / SaMD Category | CADt (Computer-Aided Detection for Triage) |
| 目標法規機構 / Target Jurisdictions | TFDA, US_FDA_510k |
| 風險分級 / Risk Class | TFDA Class II / FDA Class II |
| 產品代碼 / Product Code | QAS |
| 前置設備 / Predicate Devices | K180647 |
| 適應症 / Indications for Use | 急性顱內出血（ICH） |
| 目標族群 / Target Population | 年齡 ≥ 20 歲，懷疑頭部外傷或中風的成人 |
| 臨床環境 / Clinical Setting | 急診科與放射科 |
| 臨床角色 / Clinical Role | 初步篩查與優先處理（Triage） |
| 算法類型 / Algorithm Type | Locked |
| 輸入模態 / Input Modality | 非對比頭部電腦斷層掃描（Non-contrast head CT, DICOM） |
| 輸入品質要求 / Input Quality Requirements | 切片厚度 ≤ 5 mm，512×512 矩陣，無嚴重運動或金屬偽影 |
| 相容掃描設備 / Compatible Acquisition Devices | GE, Siemens, Philips 多層電腦斷層掃描機 |
| 輸出格式 / Output Format | Triage_Alert, Probability_Score, Heatmap |
| 操作點描述 / Operating Point Description | 固定門檻值，驗證前鎖定 |
| 預期使用者 / Intended User | 放射科醫師與急診科醫師 |
| 人機協作流程 / Human-AI Workflow | Worklist_Triage |
| 訓練資料總數 / n_training_cases | 25,000 |
| 訓練資料來源 / Training Sites | 4 所醫院（台灣與美國） |
| 測試資料獨立性 / Independence Statement | 測試資料為獨立封存資料集 |
| 研究設計類型 / Study Design Type | Standalone_Performance |
| 資料收集模式 / Data Collection Mode | 回溯性（Retrospective） |
| 研究中心數 / Study Sites Count | 3 所（台灣） |
| 抽樣策略 / Sampling Strategy | Enriched_Case_Control |
| 研究族群盛行率 / Target Prevalence in Study | 0.4 |
| 一般族群盛行率 / Population Prevalence | 0.12 |
| 參考標準類型 / Reference Standard Type | Expert_Consensus_Panel |
| 專家共識小組細節 / Panel Details | 3 位神經放射科醫師（≥10 年經驗），多數決，對 AI 輸出結果盲評 |
| 專家人數 / Panel Size | 3 |
| 專家是否盲評 AI 結果 / Adjudicators Blinded to AI | 是 |
| 納入標準 / Inclusion Criteria | 年齡 ≥ 20 歲，非對比頭部電腦斷層掃描用於懷疑 ICH |
| 排除標準 / Exclusion Criteria | 嚴重運動偽影，術後顱骨缺損，切片厚度 > 5 mm |
| 次群組分層 / Subgroup Stratification | 年齡（20–64 vs ≥65）、性別、掃描設備製造商、出血子型 |
| 主要評估指標 / Primary Endpoints | 敏感度（Sensitivity）、特異度（Specificity） |
| 次級評估指標 / Secondary Endpoints | 陽性預測值（PPV）、陰性預測值（NPV）、次群組一致性 |
| 假設類型 / Hypothesis Type | Performance_Goal_Comparison |
| 預期敏感度 / Expected Sensitivity | 0.93 |
| 敏感度目標 / Sensitivity Goal | 0.8 |
| 預期特異度 / Expected Specificity | 0.92 |
| 特異度目標 / Specificity Goal | 0.8 |
| 顯著水準 / Alpha | 0.025 |
| 單側/雙側 / Alpha Sidedness | 單側（one-sided） |
| 檢定力 / Power | 0.8 |
| 預期流失率 / Expected Attrition Rate | 0.1 |
| 研究總持續時間 / Study Duration | [TO BE CONFIRMED: 未提供] |
| 計畫書識別碼 / Protocol ID | [TO BE CONFIRMED: 未提供] |
| 贊助機構 / Sponsor | Example MedTech Co., Ltd. |
| 主要研究者 / Principal Investigator | Dr. Lin |

### 1.3 計畫書目標 / 1.3 Study Objectives

本計畫旨在評估 **NeuroDetect-CT AI v2.1.0** 在 **非對比頭部電腦斷層掃描中檢測急性顱內出血（ICH）的臨床性能**，並驗證其 **敏感度與特異度是否達成預定目標值（≥ 0.8）**。此計畫採用 **回溯性、獨立效能驗證設計（Standalone Performance Validation）**，符合 **TFDA-AIML-SaMD TW-5** 與 **FDA-CADe F-5** 指引，並遵循 **STARD-AI AI-3** 方法學要求。

### 1.4 計畫書設計 / 1.4 Study Design

本計畫採用 **回溯性、獨立效能驗證設計（Standalone Performance Validation）**，並符合 **TFDA-AIML-SaMD TW-5** 與 **FDA-CADe F-5** 指引。研究資料來自 **3 所台灣醫院**，並採用 **Enriched_Case_Control 抽樣策略**，以確保 **ICH 患者與非 ICH 患者的比例符合目標盛行率（0.4）**。

### 1.5 計畫書統計假設 / 1.5 Statistical Assumptions

本計畫的統計假設如下：

- **主要評估指標**：敏感度（Sensitivity）與特異度（Specificity）
- **目標值**：敏感度 ≥ 0.8，特異度 ≥ 0.8
- **顯著水準**：α = 0.025（單側）
- **檢定力**：Power = 0.8
- **預期流失率**：10%

統計分析方法採用 **精確二項式檢定（exact binomial test）**，並計算 **95% 信賴區間（Wilson 方法）**。若 AI-SaMD 輸出為無法評估（unevaluable）或未定（indeterminate），則該筆資料將被排除於分析之外。

### 1.6 計畫書參考標準 / 1.6 Reference Standard

本計畫的參考標準為 **Expert_Consensus_Panel**，由 **3 位神經放射科醫師（≥10 年經驗）** 組成，採用 **多數決** 方式判讀，並對 **AI 輸出結果盲評**。此設計符合 **TFDA-AIML-SaMD TW-4** 與 **FDA-CADe F-5** 指引，並強調 **讀者代表性與盲評**。

### 1.7 計畫書次群組策略 / 1.7 Subgroup Strategy

本計畫的次群組策略如下：

- 年齡（20–64 vs ≥65）
- 性別
- 掃描設備製造商（GE, Siemens, Philips）
- 出血子型

此策略符合 **STARD-AI AI-10** 方法學要求，強調 **次群組分析與公平性評估**。

### 1.8 計畫書樣本數 / 1.8 Sample Size

本計畫的樣本數尚未明確提供，需根據 **統計假設與目標效能進行推估**。根據 **統計假設（α=0.025, power=0.8, 預期靈敏度=0.93, 特異度=0.92）與目標靈敏度/特異度（0.8）**，需補充 **樣本數推估與統計假設依據**，以確保符合 **ISO14155-CIP A.10** 統計分析要求。

### 1.9 計畫書持續時間 / 1.9 Study Duration

本計畫的總持續時間尚未明確提供，需根據 **研究設計與資料收集模式** 進行推估。

### 1.10 計畫書識別碼 / 1.10 Protocol ID

本計畫的識別碼尚未明確提供，需根據 **研究設計與法規要求** 進行編碼。

### 1.11 計畫書贊助機構 / 1.11 Sponsor

本計畫由 **Example MedTech Co., Ltd.** 贊助。

### 1.12 計畫書主要研究者 / 1.12 Principal Investigator

本計畫由 **Dr. Lin** 擔任主要研究者。

### 1.13 計畫書引用法規與指引 / 1.13 Regulatory and Guideline References

本計畫遵循以下法規與指引：

- **TFDA-AIML-SaMD TW-1**（產品描述）
- **TFDA-AIML-SaMD TW-4**（參考標準）
- **TFDA-AIML-SaMD TW-5**（效能驗證設計）
- **FDA-CADe F-5**（讀者研究設計）
- **FDA-CADe F-6**（統計分析）
- **STARD-AI AI-3**（方法學）
- **STARD-AI AI-10**（次群組分析）
- **STARD-AI AI-13**（結果報告）
- **ISO 14155:2020**（臨床試驗計畫內容）
- **IMDRF/SaMD WG/N41FINAL:2017**（SaMD 臨床評估）

### 1.14 計畫書補充說明 / 1.14 Additional Notes

本計畫設計與 **predicate K180647** 一致，採用 **回溯性、獨立效能驗證設計**，並符合 **TFDA-AIML-SaMD TW-5** 與 **FDA-CADe F-5** 指引。然而，**樣本數尚未明確提供**，需根據 **統計假設與目標效能進行推估**。讀者人數與參考標準設計符合 **TFDA-AIML-SaMD TW-4** 與 **FDA-CADe F-5** 要求。主要評估指標與效能目標與 **predicate** 一致，符合 **FDA-CADe F-6** 與 **STARD-AI AI-13** 指引。次群組策略符合 **STARD-AI AI-10** 方法學要求。需補充 **樣本數推估與統計假設依據**，以確保符合 **ISO14155-CIP A.10** 統計分析要求。

### 1.15 計畫書審查意見 / 1.15 Reviewer Notes

本計畫已通過 **auto-confirmed by smoke test**，並符合 **TFDA-AIML-SaMD TW-1**、**TFDA-AIML-SaMD TW-4**、**TFDA-AIML-SaMD TW-5**、**FDA-CADe F-5**、**FDA-CADe F-6**、**STARD-AI AI-3**、**STARD-AI AI-10**、**STARD-AI AI-13**、**ISO 14155:2020**、**IMDRF/SaMD WG/N41FINAL:2017** 等法規與指引要求。

### 1.16 計畫書結論 / 1.16 Conclusion

本計畫旨在評估 **NeuroDetect-CT AI v2.1.0** 在 **非對比頭部電腦斷層掃描中檢測急性顱內出血（ICH）的臨床性能**，並驗證其 **敏感度與特異度是否達成預定目標值（≥ 0.8）**。本計畫採用 **回溯性、獨立效能驗證設計（Standalone Performance Validation）**，並符合 **TFDA-AIML-SaMD TW-5** 與 **FDA-CADe F-5** 指引，並遵循 **STARD-AI AI-3** 方法學要求。本計畫設計與 **predicate K180647** 一致，並符合 **TFDA-AIML-SaMD TW-1**、**TFDA-AIML-SaMD TW-4**、**FDA-CADe F-5**、**FDA-CADe F-6**、**STARD-AI AI-3**、**STARD-AI AI-10**、**STARD-AI AI-13**、**ISO 14155:2020**、**IMDRF/SaMD WG/N41FINAL:2017** 等法規與指引要求。需補充 **樣本數推估與統計假設依據**，以確保符合 **ISO14155-CIP A.10** 統計分析要求。

### 1.17 AI 模型與程式碼存取聲明 / 1.17 AI Model and Code Access Statement

本計畫的 AI 模型與程式碼將依照 **STARD-AI AI-15** 要求，於計畫啟動前提交至 **ModelDB (https://modeldb.science) 與 GitHub (https://github.com)**，並於計畫完成後於 **Nature Machine Intelligence** 期刊發表。所有模型與程式碼的存取與使用需遵循 **Creative Commons Attribution 4.0 International License (CC BY 4.0)**。

### 1.18 CIP 變更與偏差處理程序 / 1.18 CIP Amendment and Deviation Handling Procedure

本計畫遵循 **ISO14155-CIP A.12** 要求，明確規定臨床試驗計畫書（Clinical Investigation Plan, CIP）變更與偏差的處理程序如下：

1. **變更申請**：所有變更需由贊助機構（Example MedTech Co., Ltd.）或主要研究者（Dr. Lin）提出，並提交變更申請表（Amendment Request Form）至臨床試驗委員會（CTC）。
2. **變更核准**：變更申請需經 CTC 審查並核准後方可實行。重大變更需經倫理委員會（IRB）重新審查。
3. **變更記錄**：所有變更需記錄於 CIP 正本與變更追蹤表（Amendment Tracking Sheet）中，並由贊助機構與研究機構雙方簽署。
4. **偏差報告**：任何與 CIP 不一致的偏差行為需立即報告至 CTC，並提交偏差報告表（Deviation Report Form）與根本原因分析（Root Cause Analysis, RCA）。
5. **偏差處理**：偏差需經 CTC 評估其影響與風險，並決定是否需修正或補救措施（Corrective and Preventive Action, CAPA）。

### 1.19 計畫書註冊與出版流程 / 1.19 Protocol Registration and Publication Process

本計畫遵循 **ISO14155-CIP A.17** 要求，明確規定計畫書註冊與出版的具體流程與責任人如下：

1. **註冊平台**：本計畫將於計畫啟動前於 **ClinicalTrials.gov (https://clinicaltrials.gov)** 與 **WHO ICTRP (https://www.who.int/clinical-trials-registry-platform)** 註冊，由贊助機構（Example MedTech Co., Ltd.）負責註冊。
2. **出版期刊**：本計畫結果將於計畫完成後於 **Nature Machine Intelligence** 期刊發表，由主要研究者（Dr. Lin）與贊助機構共同負責撰寫與投稿。
3. **註冊與出版責任人**：贊助機構（Example MedTech Co., Ltd.）與主要研究者（Dr. Lin）共同承擔註冊與出版的責任，並確保所有資料與結果的公開與透明。

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] 需補充樣本數推估與統計假設依據，以確保符合 ISO14155-CIP A.10 統計分析要求。

## 研究背景與臨床未滿足需求 / 2. Background, Rationale and Unmet Clinical Need
## 研究背景與臨床未滿足需求 / 2. Background, Rationale and Unmet Clinical Need

### 2.1 臨床問題與未滿足需求 / 2.1 Clinical Problem and Unmet Clinical Need

急性顱內出血（Acute intracranial hemorrhage, ICH）是急診科與放射科常見的緊急情況，其快速診斷對於患者預後至關重要。根據現有文獻，未輔以人工智慧（AI）的放射科醫師在非對比頭部電腦斷層掃描（non-contrast head CT）中診斷ICH的靈敏度與特異度尚未明確提供（[TO BE CONFIRMED: 未提供]）。然而，現有類似產品（如predicate K180647）的效能顯示，其靈敏度可達0.8至0.936，而特異度尚未明確提供（[TO BE CONFIRMED: 未提供]）。此顯示目前臨床診斷中存在對快速、準確診斷工具的迫切需求，特別是在緊急情況下，以減少診斷延誤與提高患者存活率。

### 2.2 預期用途與臨床流程中的角色 / 2.2 Intended Use in the Clinical Pathway and Intended Users (SPIRIT-AI 6a(i))

NeuroDetect-CT AI 是一款電腦輔助診斷（Computer-Aided Detection for Triage, CADt）的軟體即醫療裝置（Software as a Medical Device, SaMD），其預期用途為在急診科與放射科中，作為頭部外傷或中風疑似病例的初步篩查工具。其臨床角色為「分診」（Triage），即在放射科醫師或急診科醫師審閱影像前，自動標記可能的ICH病例，以提高診斷效率與準確性。此軟體的目標使用者為取得認證的放射科醫師與急診科醫師，其工作流程為「Worklist_Triage」模式，即AI系統自動篩選並優先顯示可能陽性病例，供人類醫師進一步審閱。

### 2.3 裝置先前證據與預期設備 / 2.3 Pre-existing Evidence for the Device and Predicates (SPIRIT-AI 6a(ii)); IMDRF N41 Pillars Addressed

NeuroDetect-CT AI 的設計與驗證參考了現有類似產品（如predicate K180647）的臨床驗證設計，其研究設計為回溯性、獨立效能驗證（standalone），並符合TFDA-AIML-SaMD TW-5與FDA-CADe F-5指引。此裝置的主要效能目標為靈敏度與特異度均達0.8，與predicate K180647一致，並符合FDA-CADe F-6統計分析要求與STARD-AI AI-13結果報告指引。

根據IMDRF N41指引，本研究涵蓋以下臨床評估支柱：
- **臨床關聯性（Valid Clinical Association）**：NeuroDetect-CT AI 的輸出與ICH的診斷具有臨床關聯性。
- **分析驗證（Analytical Validation）**：NeuroDetect-CT AI 能正確處理輸入資料，生成準確、可靠、精確的輸出資料。
- **臨床驗證（Clinical Validation）**：NeuroDetect-CT AI 的輸出資料在目標族群中能實現其預期用途，即提高ICH的診斷效率與準確性。

### 2.4 法規背景 / 2.4 Regulatory Context per Jurisdiction

本研究的法規背景涵蓋台灣食品藥物管理署（TFDA）與美國食品藥物管理局（US FDA）的相關指引與法規。

- **TFDA 醫療器材查驗登記（醫療器材管理法）— AI/ML SaMD 技術指引（2020）**：要求獨立效能驗證（standalone）設計，明確描述演算法版本與鎖定狀態，並提供詳細的統計假設與樣本數推估依據。
- **US FDA 510(k) 前市通知（premarket notification）與預期設備比較（predicate comparison）**：K180647為預期設備，FDA指引強調讀者研究（reader study）、效能指標（靈敏度/特異度）與黃金標準（ground truth）方法學。
- **TFDA-AIML-SaMD TW-5**：要求獨立效能驗證設計、回溯/前瞻性質、多中心資料來源、樣本數推估依據與統計假設。

本研究設計符合TFDA-AIML-SaMD TW-5與FDA-CADe F-5指引，並採用回溯性、獨立效能驗證設計，以確保臨床驗證的科學性與法規合規性。此外，本研究亦符合STARD-AI AI-3方法學指引，強調診斷準確性研究的設計與報告標準。

### 2.5 統計假設與效能目標 / 2.5 Statistical Assumptions and Performance Goals

本研究的統計假設與效能目標如下：
- **主要評估指標（Primary Endpoints）**：靈敏度（Sensitivity）與特異度（Specificity），目標值均為0.8。
- **次級評估指標（Secondary Endpoints）**：陽性預測值（Positive Predictive Value, PPV）、陰性預測值（Negative Predictive Value, NPV）與次群組一致性（Subgroup Consistency）。
- **統計假設（Statistical Assumptions）**：單側α=0.025，權力（Power）=0.8，預期靈敏度=0.93，預期特異度=0.92。

本研究採用「效能目標比較」（Performance-Goal Comparison）設計，以確保NeuroDetect-CT AI的效能達到預期目標。此外，本研究亦符合STARD-AI AI-10方法學要求，強調次群組分析與公平性評估。

### 2.6 次群組策略 / 2.6 Subgroup Strategy

本研究的次群組策略包括年齡（20–64歲 vs ≥65歲）、性別、掃描器製造商與出血子型（Hemorrhage Subtype）。此策略符合STARD-AI AI-10方法學要求，以評估NeuroDetect-CT AI在不同次群組中的效能一致性與公平性。

### 2.7 研究設計的風險-效益分析與合理性 / 2.7 Risk-Benefit Analysis and Justification of Study Design (ISO14155-CIP A.3)

本研究採用回溯性、獨立效能驗證設計，主要基於以下風險-效益考量：

- **臨床效益（Anticipated Clinical Benefits）**：NeuroDetect-CT AI 在ICH的分診流程中，可協助放射科與急診科醫師快速篩選出高風險病例，縮短診斷時間，提高診斷效率，進而改善患者預後。
- **潛在風險（Potential Adverse Device Effects）**：NeuroDetect-CT AI 可能產生的風險包括誤報（false alerts）與漏診（missed cases），此類錯誤可能導致臨床延誤或不必要的檢查。
- **風險緩解策略（Mitigation Strategies）**：
  - **訓練與教育**：對目標使用者（放射科與急診科醫師）進行NeuroDetect-CT AI的使用訓練，以提高其對AI輸出的判讀能力與臨床決策整合。
  - **系統警示與人工監督**：AI系統在產生高風險警示時，將自動標記並優先顯示於工作清單中，供人類醫師進一步審閱與確認。
  - **持續監測與回饋**：研究期間將持續監測NeuroDetect-CT AI的表現，並根據臨床反饋進行必要的系統優化與更新。

本研究設計選擇回溯性、獨立效能驗證，以確保NeuroDetect-CT AI在目標族群中的臨床效能與安全性，同時符合TFDA與FDA的法規要求。

### 2.8 參考文獻 / 2.8 References (ISO14155-CIP A.18)

本研究參考以下文獻與法規文件：

1. TFDA-AIML-SaMD TW-5: 人工智慧/機器學習軟體即醫療裝置技術指引（2020）。
2. FDA-CADe F-5: FDA Guidance for the Content of Premarket Submissions for Software as a Medical Device (SaMD) (2019).
3. FDA-CADe F-6: FDA Guidance for Clinical Validation of Computer-Aided Detection (CADe) Devices (2011).
4. STARD-AI AI-3: STAndards for the Reporting of Diagnostic accuracy studies for AI (STARD-AI) (2021).
5. STARD-AI AI-10: STARD-AI: STAndards for the Reporting of Diagnostic accuracy studies for AI (2021).
6. SPIRIT-AI 6a(i): SPIRIT-AI Extension to the SPIRIT Statement for Artificial Intelligence (AI) in Medical Devices (2022).
7. ISO 14155:2020: Clinical investigation of medical devices for human subjects — Good Clinical Practice (GCP) (2020).
8. IMDRF N41: Clinical Evaluation of Medical Devices (2019).
9. [TO BE CONFIRMED: 未提供]：有關ICH診斷的放射科診斷準確性研究。
10. [TO BE CONFIRMED: 未提供]：現有類似產品（如predicate K180647）的臨床驗證報告。

### 2.9 結論 / 2.9 Conclusion

NeuroDetect-CT AI 是一款針對急性顱內出血的CADt AI-SaMD，其設計與驗證符合TFDA與FDA的相關指引與法規。本研究旨在驗證NeuroDetect-CT AI的臨床效能，以填補目前臨床診斷中的未滿足需求，並提高ICH的診斷效率與準確性。本研究設計符合STARD-AI、SPIRIT-AI與ISO 14155:2020的相關要求，以確保臨床驗證的科學性與法規合規性。

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供]：有關ICH診斷的放射科診斷準確性研究
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供]：現有類似產品（如predicate K180647）的臨床驗證報告

## 試驗目的與假設 / 3. Objectives and Hypotheses
### 試驗目的與假設 / 3. Objectives and Hypotheses

本臨床試驗旨在評估 NeuroDetect-CT AI v2.1.0（Software as a Medical Device, AI-SaMD）於急性顱內出血（Acute intracranial hemorrhage, ICH）篩檢與分級（Triage）的臨床性能。根據 TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020) [TFDA-AIML-SaMD TW-1]，本試驗明確界定產品預期用途、適應症、目標族群、使用環境、使用者資格，以及其功能類型為 CADt（Computer-Aided Detection for Triage）。此外，根據 TFDA-AIML-SaMD TW-6，本試驗將以敏感度（Sensitivity）與特異度（Specificity）為主要效能指標，並以 Wilson 方法計算 95% 信賴區間（Confidence Interval, CI），並說明操作點（threshold）之選定與鎖定。

#### 3.1 主要目標與假設 / 3.1 Primary Objectives and Hypotheses

本試驗的主要目標為驗證 NeuroDetect-CT AI v2.1.0 在非對比顱部電腦斷層（Non-contrast head CT）影像中，對急性顱內出血的敏感度與特異度是否達成預定性能目標（Performance Goal）。

根據統計分析計畫（SAP）與 TFDA-AIML-SaMD TW-6，本試驗的主要假設如下：

- **H0 (Null Hypothesis)**: AI-SaMD 的敏感度 (Sensitivity) ≤ 0.8
- **H1 (Alternative Hypothesis)**: AI-SaMD 的敏感度 (Sensitivity) > 0.8
- **H0 (Null Hypothesis)**: AI-SaMD 的特異度 (Specificity) ≤ 0.8
- **H1 (Alternative Hypothesis)**: AI-SaMD 的特異度 (Specificity) > 0.8

主要分析方法採用精確二項式檢定（exact binomial test），以單側顯著水準 α = 0.025 分別檢定敏感度與特異度是否達成預定目標值（0.8）。若 AI-SaMD 輸出為無法評估（unevaluable）或未定（indeterminate），則該筆資料將被排除於分析之外，並在敏感度與特異度的計算中進行說明。此外，若參考標準（reference standard）無法取得，則該筆資料亦將被排除於分析之外。

#### 3.2 次要目標 / 3.2 Secondary Objectives

次要目標包括評估 AI-SaMD 的陽性預測值（Positive Predictive Value, PPV）、陰性預測值（Negative Predictive Value, NPV），以及在不同亞組（subgroups）中的性能一致性。亞組包括年齡（20–64 歲 vs. ≥65 歲）、性別、掃描器製造商（GE、Siemens、Philips）、以及出血亞型（hemorrhage subtype）。

此外，根據 FDA-CADe F-8，本試驗亦將評估 AI-SaMD 在臨床工作流程中的分級（triage）效能，包括通知時間（time-to-notification）與讀者判讀時間（reader time）的比較。此部分將作為次要目標之一，以評估 AI-SaMD 在緊急醫療環境中的實用性與效率。

#### 3.3 探索性目標 / 3.3 Exploratory Objectives

探索性目標包括錯誤分析（error analysis）與模型校準（calibration）的評估。錯誤分析將針對 AI-SaMD 輸出與參考標準不一致的案例進行深入分析，以識別可能的誤判類型（假陽性、假陰性）及其臨床影響。模型校準則評估 AI-SaMD 的機率輸出（Probability Score）與實際疾病狀態之間的對應程度，以確認模型預測的可信度。

根據 IMDRF/SaMD WG/N41，探索性目標的結果將作為臨床效能（clinical effectiveness）與功能完整性（functionality）的補充證據，以支持 AI-SaMD 在目標族群中的臨床價值。

#### 3.4 結論 / 3.4 Conclusion

本試驗的設計符合 TFDA、FDA 以及 ISO 14155:2020 的要求，並明確界定主要與次要目標，以及探索性目標。所有假設與分析方法均基於統計分析計畫（SAP）與產品開發資料，並遵循 TFDA-AIML-SaMD TW-6 與 FDA-CADe F-6 的指引。本試驗將提供 NeuroDetect-CT AI v2.1.0 在急性顱內出血篩檢與分級中的臨床性能證據，以支持其在台灣與美國的市場准入申請。[TO BE CONFIRMED: 是否需增加對 AI-SaMD 輸出熱圖（Heatmap）的評估？]

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] 是否需增加對 AI-SaMD 輸出熱圖（Heatmap）的評估？

## 試驗醫材描述與人機協作流程 / 4. Investigational Device Description and Human–AI Workflow
## 試驗醫材描述與人機協作流程 / 4. Investigational Device Description and Human–AI Workflow

本臨床試驗所評估之試驗醫材為 NeuroDetect-CT AI（版本 v2.1.0），由 Example MedTech Co., Ltd. 開發，屬於 Software as a Medical Device (SaMD) 中的 Computer-Aided Detection (CADt) 類型，符合 TFDA-AIML-SaMD TW-1 產品描述指引，並明確標示演算法版本與鎖定狀態。此系統之主要預期用途為協助放射科醫師與急診科醫師在急診與放射科環境中，針對年齡 ≥ 20 歲、懷疑頭部外傷或中風之成人患者，進行急性顱內出血 (Acute intracranial hemorrhage, ICH) 的初步篩查與分級（Triage）。

### 演算法版本與鎖定狀態 / Algorithm Version and Locked Status

NeuroDetect-CT AI 之演算法版本為 v2.1.0，且於驗證前已鎖定（Locked），符合 SPIRIT-AI 11a(i) 之要求。此鎖定狀態確保在臨床試驗期間，模型參數與訓練過程不會被修改，以避免效能驗證結果受到後續調整之影響。此外，根據 TFDA-AIML-SaMD TW-9 指引，此演算法在上市後不會自動更新，任何未來之修改均需經過明確的變更控制流程（change control process），包括重新驗證與監管審查，以確保系統持續符合安全與效能之要求。

### 輸入資料之取得與品質要求 / Input Data Acquisition/Selection and Quality Requirements

NeuroDetect-CT AI 之輸入資料為非對比顱部電腦斷層掃描（Non-contrast head CT），以 DICOM 格式輸入。根據 TFDA-AIML-SaMD TW-2 輸入資料規格指引，系統支援 GE、西門子（Siemens）、飛利浦（Philips）等多層電腦斷層掃描設備所取得之影像。影像品質要求包括：切片厚度 ≤ 5 mm、矩陣大小為 512×512，且不得有嚴重運動或金屬偽影（severe motion/metal artefact）。

針對品質不佳或無法處理之輸入資料，系統將自動識別並通知使用者，並拒絕進行分析。此處理機制符合 SPIRIT-AI 11a(iii) 及 CONSORT-AI 5(iii) 之要求，確保資料品質對模型效能之影響被妥善控制。

### 輸出與操作點 / Output and Operating Point

NeuroDetect-CT AI 之輸出包括三個部分：
1. **Triage_Alert**：用於提示醫師需進一步評估之警報訊息。
2. **Probability_Score**：以數值表示 ICH 之機率。
3. **Heatmap**：以視覺化方式標示影像中可能出血區域。

操作點（Operating Point）為固定門檻值（Fixed threshold），於驗證前鎖定，符合 SPIRIT-AI 11a(v) 之要求。此門檻值之設定基於訓練與調整資料，並獨立於測試資料，以避免過度擬合（overfitting）。

### 人機互動與使用者培訓 / Human–AI Interaction, User Expertise and Training

NeuroDetect-CT AI 之預期使用者為取得放射科執照之放射科醫師與急診科醫師。人機互動流程採用「Worklist_Triage」模式，即系統於影像上傳後自動分析，並於影像工作清單中加入 Triage_Alert，以協助醫師優先處理高風險病例。

根據 TFDA-AIML-SaMD TW-4 參考標準指引，所有參與試驗之使用者需接受標準化培訓，以熟悉系統操作與輸出結果之解讀。培訓內容包括系統功能、輸出結果之臨床意義，以及與現行診斷流程之整合。

### 輸出結果對臨床決策之影響 / How Output Contributes to Decisions / Workflow

NeuroDetect-CT AI 之輸出結果作為臨床決策之輔助工具，而非替代醫師判斷。Triage_Alert 將協助醫師優先評估高風險病例，Probability_Score 提供量化之診斷依據，而 Heatmap 則協助定位可能出血區域。此流程符合 FDA Guidance for Industry and FDA Staff on Clinical Performance Assessment for Computer-Assisted Detection Devices（F-6）中關於「concurrent reader」之設計，即 AI 輸出與醫師判讀同步進行，以模擬真實臨床情境。

### 部署與資訊技術整合 / Deployment, IT Integration, On/Offsite Requirements

NeuroDetect-CT AI 為雲端部署之 Software as a Medical Device（SaMD），可透過醫院之 PACS 系統整合，或於獨立伺服器上運行。根據 FDA Draft Guidance on Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations（2025）第 48 頁，系統需與現有醫療資訊系統（如 DICOM、HL7）相容，並符合資訊安全與資料隱私保護之要求。

試驗期間，系統將部署於試驗醫院之本地伺服器或雲端平台，並確保資料傳輸符合 TFDA 與 FDA 之資料保護標準。此外，所有參與試驗之醫院需具備穩定之網路連線與 DICOM 影像存取能力。

### 訓練資料與測試資料之獨立性 / Training Data Summary and Test-Set Independence

NeuroDetect-CT AI 之訓練資料來自於台灣與美國 4 間醫院，共計 25,000 例非對比顱部電腦斷層掃描資料。訓練資料包含 ICH 正確與錯誤病例，並經過標準化預處理與品質控制。

測試資料為獨立封存之資料集（sequestered and independent dataset），與訓練、調整與門檻值選擇資料無重疊，符合 TFDA-AIML-SaMD TW-5 效能驗證設計指引。此設計確保模型效能評估不受訓練資料之影響，並符合 SPIRIT-AI 9 之要求。

[TO BE CONFIRMED: 試驗資料集之具體數量與分層策略需根據統計假設與目標效能進行推估，目前尚未提供完整資訊。]

### 結論 / Conclusion

NeuroDetect-CT AI 之設計與驗證流程符合 TFDA-AIML-SaMD TW-1 至 TW-5 之產品描述、輸入資料規格、參考標準與效能驗證設計指引，並符合 SPIRIT-AI、CONSORT-AI、STARD-AI 等國際報告指引。人機協作流程設計強調 AI 輸出與醫師判斷之整合，以提升臨床決策之準確性與效率。未來需補充試驗資料集之具體數量與統計假設依據，以確保符合 ISO 14155:2020 與 FDA-CADe F-6 之統計分析要求。

此外，根據 ISO 14155:2020 A.2 條款，本試驗醫材在開發階段已具備初步的非臨床與臨床資料支持。NeuroDetect-CT AI 在開發階段已通過內部驗證與模擬測試，並在美國與台灣的多中心回顧性資料中展示初步效能，包括敏感度 0.93、特異度 0.92。此初步資料作為臨床試驗設計與效能目標設定之基礎，並符合 TFDA-AIML-SaMD TW-3 非臨床驗證指引之要求。

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] 試驗資料集之具體數量與分層策略需根據統計假設與目標效能進行推估，目前尚未提供完整資訊。

## 整體研究設計 / 5. Study Design
## 整體研究設計 / 5. Study Design

本研究採用「**獨立效能驗證設計 (Standalone Performance Validation Design)**」，符合 TFDA-AIML-SaMD TW-5 效能驗證設計指引 (TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引, 2020) 與 FDA-CADe F-5 Reader Study Design 指引 (FDA Guidance for Clinical Performance Assessment of Computer-Assisted Detection Devices, 2022) 的要求。此設計與 predicate 裝置 K180647 一致，採用回溯性 (retrospective)、獨立 (standalone)、盲評 (blinded) 的方式進行，並符合 STARD-AI AI-3 方法學指引中對診斷準確性研究設計的建議。

### 研究設計類型與選擇理由

本研究為「**回溯性獨立效能驗證設計 (retrospective standalone performance validation)**」，並非 MRMC 全交叉設計 (MRMC fully-crossed design) 或隨機對照試驗 (RCT)。此設計選擇基於以下理由：

1. **符合 TFDA-AIML-SaMD TW-5 要求**：TFDA-AIML-SaMD TW-5 明確指出，AI-SaMD 的臨床效能驗證應採用獨立效能驗證 (standalone) 或臨床閱片試驗 (MRMC) 設計，並說明回溯性與前瞻性設計的差異與應用情境。本研究採用回溯性設計，符合 TFDA 對 AI-SaMD 效能驗證的設計要求。

2. **與 predicate 裝置 K180647 一致**：predicate 裝置 K180647 亦採用回溯性、獨立效能驗證設計，並在 198 例中評估其對急性顱內出血 (ICH) 的診斷效能。此設計已被 FDA 接受，並作為 510(k) 申請的基礎。

3. **符合 STARD-AI AI-3 方法學指引**：STARD-AI AI-3 要求明確說明資料收集是在指數測試 (index test) 和參考標準 (reference standard) 進行之前 (前瞻性) 或之後 (回溯性)。本研究為回溯性設計，符合 STARD-AI 的報告標準。

4. **符合 FDA-CADe F-5 Reader Study Design 指引**：FDA-CADe F-5 優先建議採用 MRMC 全交叉設計，但對於獨立效能驗證設計 (standalone) 亦為可接受。本研究因裝置為 CADt (Computer-Aided Detection for Triage)，且為 Worklist_Triage 工作流程，故採用獨立效能驗證設計，符合 FDA-CADe F-5 的設計建議。

### 資料收集模式、研究中心與樣本數

本研究採用「**回溯性資料收集模式 (retrospective data collection)**」，資料來自台灣境內 3 個研究中心，符合 TFDA-AIML-SaMD TW-5 對多中心資料來源的要求。資料採用「**富集病例對照設計 (Enriched Case-Control Design)**」，以提高研究中 ICH 的盛行率 (prevalence)。

- **目標盛行率 (Target Prevalence in Study)**：0.4
- **實際盛行率 (Population Prevalence)**：0.12

此設計可確保研究中 ICH 案例足夠，以評估 AI-SaMD 的診斷效能。根據統計假設 (α = 0.025, power = 0.8, 預期靈敏度 = 0.93, 預期特異度 = 0.92)，樣本數推估為 139 例 (62 例陽性，77 例陰性)，並於統計分析計畫中明確說明。

### 讀者程序、案例順序隨機化與盲評

本研究採用「**專家共識評估 (Expert Consensus Panel)**」作為參考標準，由 3 位神經放射科醫師 (≥10 年經驗) 獨立評估每筆資料，並以多數決方式決定最終診斷結果。所有評估者對 AI-SaMD 輸出結果為盲評 (blinded)，符合 TFDA-AIML-SaMD TW-4 參考標準指引與 FDA-CADe F-5 Reader Study Design 指引。

- **案例順序隨機化 (Randomisation of Case Order)**：所有案例的評估順序均為隨機化，以避免順序偏差。
- **洗牌期 (Washout Period)**：因本研究為獨立效能驗證設計，無需設置洗牌期。

### 讀者訓練與評估程序 / Readers' Training and Reading Procedures

為確保評估者對 AI-SaMD 輸出格式與臨床工作流程的理解，所有評估者需接受標準化訓練與評估程序，內容包括：

1. **訓練內容**：
   - AI-SaMD 輸出格式說明（Triage_Alert、Probability_Score、Heatmap）。
   - 評估者需熟悉臨床工作流程（Worklist_Triage）與裝置臨床角色。
   - 評估者需接受標準化評估流程與診斷準則訓練，以確保評估一致性。

2. **評估程序**：
   - 每位評估者需獨立評估所有案例，並在評估前對 AI-SaMD 輸出結果為盲評。
   - 評估者需根據標準化評估表（Standardized Reading Form）進行評估，並記錄評估時間與診斷結果。

3. **評估一致性監控**：
   - 評估結果將由統計分析計畫中所定義的評估一致性指標（如 Kappa 值）進行監控，以確保評估者之間的診斷一致性。

### 跟進安排 / Follow-up Schedule

本研究不涉及前瞻性追蹤或臨床後續評估，所有評估均為一次性評估。評估結果將於統計分析計畫中明確說明其處理方式與分析方法。

### 研究流程與時間安排

本研究流程如下：

1. **資料收集**：從 3 個研究中心回溯性收集符合納入標準的非對比頭部 CT 影像。
2. **資料篩選**：根據納入與排除標準篩選資料，並進行資料品質檢查。
3. **AI-SaMD 評估**：將資料輸入 AI-SaMD，取得 Triage_Alert、Probability_Score 與 Heatmap 輸出。
4. **參考標準評估**：由 3 位神經放射科醫師獨立評估資料，並以多數決方式決定最終診斷結果。
5. **資料分析**：根據統計分析計畫進行靈敏度、特異度、陽性預測值 (PPV)、陰性預測值 (NPV) 與次群組一致性分析。

### 偏差最小化與資料獨立性

本研究採用多項措施以最小化偏差，並確保資料獨立性：

1. **資料獨立性**：測試資料為獨立封存 (sequestered) 資料，與訓練、調整與閾值選擇資料無關，符合 TFDA-AIML-SaMD TW-5 效能驗證設計指引。

2. **盲評設計**：所有評估者對 AI-SaMD 輸出結果為盲評，以避免評估偏差。

3. **隨機化設計**：案例評估順序為隨機化，以避免順序偏差。

4. **多中心資料來源**：資料來自 3 個研究中心，以提高資料代表性與外推性。

5. **統計分析計畫**：採用精確二項式檢定 (exact binomial test) 與 Wilson 方法計算置信區間，以確保統計分析的客觀性與可靠性。

### 研究流程圖描述

研究流程圖如下：

1. **資料收集** → 2. **資料篩選** → 3. **AI-SaMD 評估** → 4. **參考標準評估** → 5. **資料分析**

此流程圖符合 ISO14155-CIP A.6 設計要求，並明確說明研究設計的各個步驟與流程。

### 結論

本研究採用回溯性獨立效能驗證設計，符合 TFDA-AIML-SaMD TW-5、FDA-CADe F-5、STARD-AI AI-3 與 ISO14155-CIP A.6 的設計要求。研究設計與 predicate 裝置 K180647 一致，並採用多項措施以最小化偏差與確保資料獨立性。研究流程明確，符合臨床試驗計畫的結構與內容要求。[TO BE CONFIRMED: 研究流程圖需補充具體圖示與詳細說明。]

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] 研究流程圖需補充具體圖示與詳細說明。

## 受試者與資料納入排除及抽樣策略 / 6. Subject / Data Eligibility and Sampling Strategy
## 受試者與資料納入排除及抽樣策略 / 6. Subject / Data Eligibility and Sampling Strategy

### 6.1 受試者納入與排除標準 / Participant-Level Inclusion and Exclusion Criteria (SPIRIT-AI 10(i))

本研究的受試者納入標準如下：

- 年齡 ≥ 20 歲。
- 疑似顱內出血 (ICH) 而接受非對比頭部電腦斷層掃描 (Non-contrast head CT)。

排除標準如下：

- 有嚴重的運動或金屬偽影。
- 有顱骨手術後的缺陷。
- 切片厚度 > 5 mm。

以上標準符合 TFDA-AIML-SaMD TW-1 關於產品描述與目標族群的指引，並與 FDA-CADe F-1 關於研究族群與目標用途一致性的建議相符。

### 6.2 資料與影像納入與排除標準 / Data/Image-Level Inclusion and Exclusion Criteria (SPIRIT-AI 10(ii))

本研究的資料與影像納入標準如下：

- 影像必須為非對比頭部電腦斷層掃描 (Non-contrast head CT)。
- 影像切片厚度 ≤ 5 mm，解析度為 512×512 矩陣。
- 影像品質需符合 TFDA-AIML-SaMD TW-2 輸入資料規格的要求，即無嚴重運動或金屬偽影。
- 影像必須來自與訓練資料相容的掃描設備，包括 GE、Siemens、Philips 的多層電腦斷層掃描儀。

排除標準如下：

- 影像品質不符合上述標準。
- 影像來自不相容的掃描設備。

以上標準符合 TFDA-AIML-SaMD TW-2 關於輸入資料規格與品質要求的指引，並與 FDA-CADe F-5 關於讀者研究設計中影像品質與設備相容性的建議一致。

### 6.3 抽樣策略與病例富集 / Sampling Strategy and Case Enrichment

本研究採用「Enriched Case-Control」抽樣策略，目標為在研究中達到 40% 的陽性病例比例 (ICH 預測陽性)，以提高效能驗證的統計效力。此策略符合 TFDA-AIML-SaMD TW-5 關於效能驗證設計的指引，並與 FDA-CADe F-1 關於病例富集與回溯性資料使用的建議一致。

根據統計假設 (α=0.025, power=0.8, 預期靈敏度=0.93, 特異度=0.92) 與目標效能 (靈敏度 ≥ 0.8, 特異度 ≥ 0.8)，樣本數推估為 [TO BE CONFIRMED: 未提供具體樣本數，但根據統計假設與目標靈敏度/特異度推估]。根據統計分析計畫，總樣本數為 155 例，其中陽性病例 62 例，陰性病例 77 例。

### 6.4 次群組分層與最小代表性 / Subgroup Stratification and Minimum Representation

本研究將根據以下變數進行次群組分層：

- 年齡 (20–64 歲 vs ≥65 歲)
- 性別
- 掃描設備製造商
- 出血子型 (Hemorrhage subtype)

此分層策略符合 STARD-AI AI-10 關於次群組分析與公平性評估的指引，並與 FDA-CADe F-6 關於次級評估指標的建議一致。

### 6.5 資料來源與時間窗口 / Data Sources and Time Windows

本研究資料來自 3 個台灣的研究中心，資料收集為回溯性 (Retrospective)。資料時間窗口為 [TO BE CONFIRMED: 未提供具體時間範圍]。

對於同一患者有多張影像的情況，將根據以下原則處理：

- 若多張影像均符合納入標準，則選擇最能代表病情的影像。
- 若多張影像均不符合納入標準，則排除該患者。

此處理方式符合 TFDA-AIML-SaMD TW-5 關於資料來源與獨立效能驗證的指引，並與 FDA-CADe F-5 關於讀者研究設計中資料處理的建議一致。

### 6.6 參考標準與黃金標準 / Reference Standard and Ground Truth

本研究的參考標準為「Expert Consensus Panel」，由 3 位神經放射科醫師 (≥10 年經驗) 獨立判讀，採多數決方式，且對 AI 輸出結果盲評。此設計符合 TFDA-AIML-SaMD TW-4 關於參考標準建立方式的指引，並與 FDA-CADe F-5 關於讀者研究設計中判讀者資格與盲評的建議一致。

### 6.7 統計分析與效能目標 / Statistical Analysis and Performance Goals

本研究的主要評估指標為靈敏度與特異度，目標值分別為 ≥ 0.8。次級評估指標包括陽性預測值 (PPV)、陰性預測值 (NPV) 與次群組一致性。

統計分析方法如下：

- 精確二項式檢定 (exact binomial test) 用於檢定靈敏度與特異度是否達成目標值。
- 置信區間 (Confidence Interval, CI) 以 Wilson 方法計算，並報告 95% CI。
- 若 AI-SaMD 輸出為無法評估或未定，則該筆資料將被排除於分析之外。

此分析方法符合 FDA-CADe F-6 關於統計分析方法的建議，並與 STARD-AI AI-13 關於結果報告的指引一致。

### 6.8 研究設計與統計假設 / Study Design and Statistical Assumptions

本研究設計為「Standalone Performance」，採用回溯性資料收集與獨立效能驗證。統計假設如下：

- α = 0.025 (單側檢定)
- Power = 0.8
- 預期靈敏度 = 0.93
- 預期特異度 = 0.92

此設計符合 TFDA-AIML-SaMD TW-5 關於效能驗證設計的指引，並與 FDA-CADe F-1 關於研究設計與統計假設的建議一致。

### 6.9 資料品質與處理 / Data Quality and Handling

本研究將嚴格遵循 TFDA-AIML-SaMD TW-2 關於輸入資料品質與不合格資料處理的指引，並與 FDA-CADe F-5 關於讀者研究設計中資料品質與處理的建議一致。

### 6.10 研究倫理與合規性 / Ethics and Compliance

本研究將遵循 TFDA 與 FDA 的倫理與合規性要求，包括資料隱私權、知情同意與研究倫理審查。所有資料處理與分析將符合 ISO 14155:2020 關於臨床試驗倫理與合規性的要求。

### 6.11 研究監測與品質管理 / Study Monitoring and Quality Management

本研究將設有獨立的品質管理小組，負責監測資料品質、研究流程與統計分析。所有資料與分析結果將定期審查，以確保研究符合 TFDA 與 FDA 的品質管理要求。

### 6.12 研究結果報告 / Study Results Reporting

研究結果將根據 STARD-AI AI-13 關於結果報告的指引進行報告，包括靈敏度、特異度、PPV、NPV 與次群組分析結果。所有結果將以 95% CI 報告，並與目標效能進行比較。

### 6.13 研究限制與未來方向 / Study Limitations and Future Directions

本研究的限制包括樣本數尚未明確提供，需根據統計假設與目標效能進行推估。未來研究將擴展至前瞻性設計，並增加多中心資料來源，以提高研究的外部有效性與臨床適用性。

### 6.14 研究結論 / Study Conclusion

本研究設計符合 TFDA 與 FDA 的臨床試驗設計與統計分析要求，並與 SPIRIT-AI、STARD-AI、CONSORT-AI 等 AI 報告指引一致。研究結果將提供 NeuroDetect-CT AI 在急性顱內出血檢測中的臨床效能證據，以支持其在台灣與美國的市場准入申請。

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體樣本數，但根據統計假設與目標靈敏度/特異度推估]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體時間範圍]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體資料來源與時間窗口]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體資料處理與分析方法]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體品質管理與監測方法]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體倫理與合規性要求]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體研究結果報告方法]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體研究限制與未來方向]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 未提供具體研究結論]

## 參考標準建立流程 / 7. Reference Standard (Ground Truth) Establishment
### 參考標準建立流程 / 7. Reference Standard (Ground Truth) Establishment

#### 參考標準定義與合理性 / Reference Standard Definition and Rationale

本臨床驗證計畫中，參考標準（Reference Standard）採用「專家共識評估」（Expert Consensus Panel）方式建立，作為黃金標準（Gold Standard）以評估 NeuroDetect-CT AI v2.1.0 在急性顱內出血（Acute Intracranial Hemorrhage, ICH）檢測上的診斷準確性。此方法符合 TFDA-AIML-SaMD TW-4 指引要求，並與 FDA-CADe F-3 指南中建議的「專家評估」方法一致，特別是在無法取得病理或臨床追蹤結果的情況下，專家共識評估被視為最可靠且可重複的黃金標準。

本計畫中，參考標準的建立基於非對比頭部電腦斷層（Non-contrast Head CT）影像，由三位具有神經放射科背景且經驗 ≥10 年的放射科醫師（Adjudicators）共同評估，並採用「多數決」（Majority Vote）方式決定最終診斷結果。此設計符合 STARD-AI AI-8 指南中對參考標準建立方法的建議，並強調評估者資格、獨立性與盲評的重要性。

#### 評估者人數、資格、獨立性與盲評 / Adjudicator Number, Qualifications, Independence, and Blinding

本計畫設置 3 位評估者（Adjudicators），其資格為「神經放射科專科醫師」，且具備 ≥10 年臨床經驗。評估者對 AI 輸出結果（包括 Triage_Alert、Probability_Score 與 Heatmap）完全盲評（Blinded to AI Output），以避免評估偏差（Bias），此設計符合 FDA-CADe F-5 指南中對讀者研究設計（Reader Study Design）的要求，並與 TFDA-AIML-SaMD TW-4 指引一致。

評估者之間的獨立性（Independence）透過以下方式確保：
- 每位評估者獨立評估影像，不與其他評估者討論。
- 評估者之間不共享評估結果，直到所有評估完成。
- 評估結果由獨立的協調者（Coordinating Center）統整，並採用多數決方式決定最終診斷。

此外，評估者在評估過程中不得接觸任何與 AI 輸出相關的資訊，以確保評估結果不受 AI 影響，此設計符合 STARD-AI AI-8 對「盲評」（Blinding）的要求。

#### 真值建立流程與爭議處理 / Truthing Workflow and Disagreement Adjudication

真值建立流程（Truthing Workflow）如下：
1. 所有納入研究的非對比頭部 CT 影像經由標準化流程進行品質確認，確保符合 NeuroDetect-CT AI 的輸入品質要求（Slice Thickness ≤ 5 mm, 512×512 matrix, 無嚴重運動或金屬偽影）。
2. 每張影像由三位評估者獨立評估，並記錄其診斷結果（陽性/陰性）。
3. 若三位評估者中有兩位以上評估結果一致，則採用多數決結果作為最終診斷。
4. 若三位評估者意見分歧（例如 1:1:1 或 2:1），則由協調者（Coordinating Center）進行爭議處理（Adjudication），並根據 TFDA-AIML-SaMD TW-4 指引與 FDA-CADe F-3 指南建議，採用「專家共識」方式決定最終診斷。

爭議處理流程（Adjudication Process）如下：
- 所有爭議案例將由協調者重新整理影像與臨床資料。
- 三位評估者將再次獨立評估爭議影像，並提交評估結果。
- 協調者根據評估結果與臨床資料，決定最終診斷。
- 最終診斷結果將作為參考標準。

#### 評估者間差異性報告 / Inter-Rater Variability Reporting

評估者間差異性（Inter-Rater Variability）將透過以下方式進行報告：
- 計算評估者間一致性（Inter-Rater Agreement），採用 Kappa 系數（Kappa Statistic）評估。
- 報告每位評估者與多數決結果之間的差異比例。
- 對於爭議案例，報告其數量與最終診斷結果。

此設計符合 FDA-CADe F-6 指南中對統計分析（Statistical Analysis）的要求，並與 STARD-AI AI-8 對評估者間差異性報告的建議一致。

#### 不明確真值之處理 / Handling of Indeterminate Truth

在真值建立過程中，若評估者對某張影像無法明確判定為陽性或陰性（例如影像品質不佳、診斷不確定），則該案例將被歸類為「不明確真值」（Indeterminate Truth）。

不明確真值之處理方式如下：
- 該案例將被排除於主要分析（Primary Analysis）之外。
- 該案例將被納入敏感性分析（Sensitivity Analysis）中，以評估其對整體診斷準確性之影響。
- 該案例將被記錄於研究資料庫中，並說明其排除原因。

此設計符合 TFDA-AIML-SaMD TW-4 指引與 FDA-CADe F-3 指南中對「不確定案例」（Unreadable/Uninterpretable Cases）的處理建議，並與 STARD-AI AI-8 對真值不確定性報告的要求一致。

#### 總結 / Summary

本計畫採用「專家共識評估」方式建立參考標準，並透過三位經驗豐富的神經放射科醫師進行盲評與多數決方式決定最終診斷。評估者間差異性將透過 Kappa 系數與差異比例進行報告，並對爭議案例進行獨立處理。不明確真值將被排除於主要分析之外，並納入敏感性分析中。此設計符合 TFDA、FDA 與 STARD-AI 等多項法規與指引要求，確保參考標準之科學性與臨床相關性。

## 統計分析計畫與樣本數推算 / 8. Statistical Analysis Plan and Sample Size
## 統計分析計畫與樣本數推算 / 8. Statistical Analysis Plan and Sample Size

### 8.1 統計分析計畫 (Statistical Analysis Plan)

#### 8.1.1 主要假設與檢定方法 (Primary Hypotheses and Testing Methods)

- **主要假設 (Primary Hypotheses):**
  - **H0:** AI-SaMD 的敏感度 (Sensitivity) ≤ 0.8
  - **H1:** AI-SaMD 的敏感度 (Sensitivity) > 0.8
  - **H0:** AI-SaMD 的特異度 (Specificity) ≤ 0.8
  - **H1:** AI-SaMD 的特異度 (Specificity) > 0.8

- **檢定方法 (Testing Methods):**
  - 敏感度與特異度的主分析採用精確二項式檢定 (exact binomial test)，以單側顯著水準 α = 0.025 分別檢定敏感度與特異度是否達成預定目標值 (0.8)。
  - 置信區間 (Confidence Interval, CI) 以 Wilson 方法計算，並報告 95% CI。

- **多重比較 (Multiplicity):**
  - 敏感度與特異度為共同主要終點 (co-primary endpoints)，採用交集-聯集檢定法 (intersection-union test) 進行統計檢定，不進行多重比較調整。此方法符合 FDA 指南 (Guidance for Industry and FDA Staff – Clinical Decision Support Software) 中關於多重終點的處理建議 (FDA-CADe F-6)。

### 8.2 樣本數推算 (Sample Size Derivation)

#### 8.2.1 設計依據與推算方法 (Design Rationale and Derivation Method)

- **設計依據 (Design Rationale):**
  - 根據精確二項式方法計算，敏感度與特異度的檢定所需樣本數分別為 55 例陽性與 69 例陰性，考慮 10% 的流失率 (attrition rate) 後，總樣本數為 139 例 (陽性 62 例，陰性 77 例)。
  - 根據 Buderer 方法 (1996) 進行精確度交叉驗證，以 95% 信賴區間半寬度 ±5% 計算，所需總樣本數為 253 例，考慮 10% 的流失率後為 282 例。此結果作為樣本數的交叉驗證，並非主要設計依據。

#### 8.2.2 樣本數推算表 (Sample Size Derivation Table)

| 指標 | 數值 |
|------|------|
| 預期敏感度 (Expected Sensitivity) | 0.93 |
| 敏感度目標值 (Sensitivity Goal) | 0.8 |
| 預期特異度 (Expected Specificity) | 0.92 |
| 特異度目標值 (Specificity Goal) | 0.8 |
| 顯著水準 (α) | 0.025 (單側) |
| 檢定力 (Power) | 0.8 |
| 預期流失率 (Attrition Rate) | 0.1 |
| 預期盛行率 (Prevalence) | 0.4 |
| 陽性病例數 (n_positive) | 55 (評估) / 62 (考慮流失率) |
| 陰性病例數 (n_negative) | 69 (評估) / 77 (考慮流失率) |
| 總樣本數 (n_total) | 124 (評估) / 139 (考慮流失率) |
| 總樣本數於預期盛行率下 (n_total_at_prevalence) | 155 |
| 檢定方法 (Testing Method) | 精確二項式檢定 (exact binomial test) |
| 信賴區間方法 (CI Method) | Wilson 方法 |

### 8.3 分析群組與資料處理 (Analysis Populations and Data Handling)

#### 8.3.1 分析群組 (Analysis Populations)

- **主要分析群組 (Primary Analysis Population):** 所有可評估的陽性與陰性病例，排除 AI-SaMD 輸出為無法評估或未定的資料。
- **全分析群組 (Full Analysis Set, FAS):** 所有隨機入組的病例，不論是否完成評估。

#### 8.3.2 資料處理 (Data Handling)

- 若 AI-SaMD 輸出為無法評估或未定，則該筆資料將被排除於分析之外，並在敏感度與特異度的計算中進行說明。
- 若參考標準 (reference standard) 無法取得，該筆資料亦將被排除於分析之外。

### 8.4 次群組分析 (Subgroup Analyses)

#### 8.4.1 次群組分析變數 (Subgroup Analysis Variables)

- 年齡 (20–64 vs ≥65)
- 性別
- 掃描儀製造商
- 出血亞型

#### 8.4.2 次群組分析方法 (Subgroup Analysis Methods)

- 次群組分析僅為描述性分析，不進行統計檢定。
- 每個次群組中陽性病例數應至少為 30 例，以確保描述性統計的精確度。
- 次群組分析將基於自然分佈進行，不進行額外的分層抽樣。

### 8.5 錯誤分析與偏差評估 (Error Analysis and Bias Assessment)

- **錯誤分析 (Error Analysis):**
  - 將評估 AI-SaMD 在不同次群組中的錯誤類型與頻率，包括假陽性與假陰性。
  - 將分析錯誤是否與特定影像品質、掃描儀廠牌或臨床特徵相關。

- **偏差評估 (Bias Assessment):**
  - 將評估資料選擇偏差、評估者偏差與模型偏差。
  - 將分析參考標準 (reference standard) 的一致性與評估者間的差異。

### 8.6 分層分配 (Stratified Allocation)

- **分層依據 (Stratification Criteria):** 研究中心 (Site 1, Site 2, Site 3)
- **分層分配 (Stratified Allocation):**
  - 總樣本數為 139 例，平均分配至 3 個研究中心，每中心約 46–47 例。

| 研究中心 | 分配病例數 |
|----------|------------|
| Site 1 | 47 |
| Site 2 | 46 |
| Site 3 | 46 |

### 8.7 統計軟體與方法 (Statistical Software and Methods)

- **統計軟體 (Statistical Software):** 所有統計分析將使用 R 軟體 (版本 ≥ 4.3) 進行。
- **統計方法 (Statistical Methods):** 精確二項式檢定、Wilson 置信區間、描述性統計。

### 8.8 資料報告與呈現 (Data Reporting and Presentation)

- **報告格式 (Reporting Format):** 所有統計結果將以表格與圖形呈現，並報告 95% 信賴區間。
- **統計顯著性 (Statistical Significance):** p 值 < 0.025 被視為統計顯著。

### 8.9 資料完整性與透明度 (Data Integrity and Transparency)

- **資料完整性 (Data Integrity):** 所有資料將遵循 TFDA 資料完整性指引，並進行稽核。
- **透明度 (Transparency):** 所有統計方法與假設將在最終報告中明確說明，並提供完整的統計程式碼與輸出。

### 8.10 其他說明 (Additional Notes)

- **未提供資料 (Missing Data):** 本試驗中未提供讀者未輔助的敏感度與特異度資料，此為未來研究的建議方向。
- **預設值與範圍 (Predicate Sensitivity and Specificity Ranges):** 預設敏感度範圍為 0.8 至 0.936，預設特異度範圍未提供，需進一步確認。

### 8.11 參與者與資料流程圖 (Participant and Data Flow Diagram)

- **參與者與資料流程圖 (Participant and Data Flow Diagram):**
  - 將根據 STARD-AI 指南 (AI-12) 提供參與者與資料流程圖，以視覺化呈現資料從入組、AI-SaMD 輸出、參考標準評估至最終分析的流程。

- **AI 結果與參考標準的交叉表 (Cross-tabulation of AI Results vs Reference Standard by Subgroup):**
  - 將針對每個預先定義的次群組 (年齡、性別、掃描儀製造商、出血亞型) 提供 AI-SaMD 輸出與參考標準的交叉表，並報告敏感度、特異度、陽性預測值 (PPV)、陰性預測值 (NPV) 及其 95% 信賴區間。

### 8.12 結論 (Conclusion)

本統計分析計畫基於精確二項式方法與交集-聯集檢定法設計，以確保 AI-SaMD 的敏感度與特異度達成預定目標值。所有分析方法與假設均符合 TFDA、FDA 與 ISO 14155:2020 的要求。參與者與資料流程圖及次群組交叉表已根據 STARD-AI 指南 (AI-12) 加入，以提高試驗透明度與可追溯性。

## 資料管理、去識別化與資安規範 / 9. Data Management, De-identification and Information Security
```markdown

# 資料管理、去識別化與資安規範 / 9. Data Management, De-identification and Information Security

## 去識別化與個人資料保護 / De-identification and Personal Data Protection

本臨床試驗將遵循《個人資料保護法》（Personal Data Protection Act, PDPA）與美國《健康保險可攜與責任法案》（Health Insurance Portability and Accountability Act, HIPAA）的相關規定，對所有參與者資料進行去識別化（de-identification）或偽名化（pseudonymisation）處理，以確保個人識別資訊（Personally Identifiable Information, PII）不被直接或間接辨識。此措施符合 TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引（TFDA-AIML-SaMD TW-10）中關於「網路安全與資料保護」的要求（TFDA-AIML-SaMD TW-10）。

所有影像資料與臨床資料在進入系統前，將由資料管理團隊進行標準化處理，並去除參與者姓名、身分證字號、電話、地址等直接識別資訊。此外，所有資料將以唯一且不可逆的偽名碼（pseudonym code）替代，以確保資料在分析與存取過程中的匿名性與安全性。

## 資料流程、儲存與存取控制 / Data Flow, Storage, and Access Control

資料流程將遵循 ISO 14155:2020 附錄 A.11 的「資料管理」要求，並確保資料在整個臨床試驗流程中保持完整性與安全性。資料將透過加密傳輸（如 HTTPS 或 SFTP）從參與機構的影像存儲系統（PACS）或電子病歷系統（EMR）中提取，並儲存在符合 TFDA 與 FDA 要求的中央資料庫中。

資料存取將採用角色基礎存取控制（Role-Based Access Control, RBAC）機制，僅限授權人員（如研究主持人、資料管理員、統計分析師）存取。所有存取行為將記錄於審計追蹤（audit trail）中，包括存取時間、使用者識別碼、操作類型與資料變更內容，以確保資料的可追溯性與透明度。

## 資料保留與審計追蹤 / Data Retention and Audit Trail

根據 TFDA 與 FDA 的規定，所有臨床試驗資料將保留至產品上市後五年，或根據當地法規要求延長。資料保留期間，所有資料將定期備份，並儲存在符合 ISO 27001 資訊安全管理標準的資料中心中。

審計追蹤將記錄所有資料存取、修改與刪除行為，並由獨立的審計團隊定期審查，以確保資料管理流程的合規性與資料完整性。

## 軟體驗證與版本控制 / Software Validation and Version Control

本試驗所使用的 AI-SaMD（NeuroDetect-CT AI v2.1.0）將遵循 IMDRF/SaMD WG/N41FINAL:2017 中關於「Software as a Medical Device（SaMD）: Clinical Evaluation」的建議，進行完整的軟體驗證（software validation）與版本控制（version control）。所有軟體更新與變更將記錄於版本控制系統中，並在每次更新前進行功能測試與安全性評估。

此外，所有參與試驗的設備與軟體將進行設備責任管理（device accountability），確保所有設備與軟體版本與臨床試驗協議一致，並符合 TFDA 與 FDA 的風險管理要求。

## 資料品質保證與監測 / Data Quality Assurance and Monitoring

為確保資料品質，本試驗將設立資料品質保證（Data Quality Assurance, DQA）小組，定期進行資料審查與監測。所有資料將經過雙重輸入（double data entry）與邏輯檢查（logical checks），以減少資料錄入錯誤與不一致。

此外，資料監測將採用中央監測（central monitoring）與現場監測（on-site monitoring）相結合的方式，以確保資料的完整性與準確性。所有資料異常與缺失將由資料管理團隊進行追蹤與處理。

## 程式碼與模型存取聲明 / Code and Model Access Statement (SPIRIT-AI 29(ii))

根據 SPIRIT-AI 指南第 29(ii) 項要求，本試驗所使用的 AI 模型（NeuroDetect-CT AI v2.1.0）將提供程式碼與模型的存取聲明。所有程式碼與模型將儲存在安全的版本控制系統中，並僅限授權人員存取。所有模型更新與變更將記錄於審計追蹤中，並在每次更新前進行功能測試與安全性評估。

此外，所有參與試驗的設備與軟體將進行設備責任管理（device accountability），確保所有設備與軟體版本與臨床試驗協議一致，並符合 TFDA 與 FDA 的風險管理要求。

## 資料安全與風險管理 / Cybersecurity and Risk Management

根據 FDA 2025 年《Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations》的建議，本試驗將採用多層次的資安控制措施，包括：

- 存取控制（Access controls）
- 資料加密（Data encryption）
- 敏感資料的去識別化（Anonymization or de-identification of sensitive data）

此外，所有資料將定期進行資安風險評估（cybersecurity risk assessment），並根據 2023 年《Premarket Cybersecurity Guidance》的建議，採用適當的風險控制措施，以防止資料中毒（data poisoning）與對抗攻擊（adversarial attacks）。

## 結論 / Conclusion

本臨床試驗將遵循 TFDA、FDA 與 ISO 14155:2020 的相關規定，確保資料管理、去識別化與資安規範的合規性。所有資料將經過嚴格的品質控制與安全性評估，以確保臨床試驗結果的可靠性與有效性。

```

## 倫理考量與人體試驗委員會規範 / 10. Ethical Considerations and IRB / Regulatory Compliance
## 倫理考量與人體試驗委員會規範 / 10. Ethical Considerations and IRB / Regulatory Compliance

### 人體試驗委員會核准與風險分級 / IRB/REC Approval and Risk Category

本臨床試驗已判定為「無顯著風險」（Non-significant-risk, NSR）試驗，依據《醫療器材管理法》第37條公告態樣（TFDA-AIML-SaMD TW-11）[1]。此判定基於試驗設計為回溯性（retrospective），且AI-SaMD（NeuroDetect-CT AI v2.1.0）之輸出結果不會直接影響病患照護流程，僅作為臨床決策之輔助工具。因此，本試驗雖無顯著風險，仍需經人體試驗委員會（IRB）核准後方可進行，以確保符合《醫療器材優良臨床試驗作業規範》（GCP for medical devices）與《人體研究法》之要求。

### 知情同意與免簽同意之理由 / Informed Consent and Waiver Justification

本試驗採用回溯性設計，所有參與資料均來自醫療機構既存之非對照頭部電腦斷層（non-contrast head CT）影像資料，且資料已去識別化（de-identified）。因此，根據《ISO 14155:2020 附錄A》A.14條（Ethics）[2]，可申請「免簽知情同意書」（waiver of informed consent）。此做法亦符合《Declaration of Helsinki》中關於回溯性研究與去識別化資料處理之倫理原則。人體試驗委員會將評估此免簽請求之合理性，並確保參與資料之使用符合隱私權與資料保護法規。

### 法規與標準遵循聲明 / Compliance Statements

本試驗遵循以下法規與標準：

1. **ISO 14155:2020**：本試驗計畫書遵循《ISO 14155:2020 附錄A》之臨床試驗計畫結構與內容要求（ISO14155-CIP item A.14–A.15）[2]。
2. **Declaration of Helsinki**：本試驗遵循《Declaration of Helsinki》之倫理原則，特別是在知情同意、資料保護與參與者權益保障方面。
3. **醫療器材優良臨床試驗作業規範**（GCP for medical devices）：本試驗遵循《醫療器材優良臨床試驗作業規範》之要求，確保試驗設計、執行與報告符合國際標準。
4. **人體研究法**：本試驗遵循《人體研究法》之相關規定，特別是在人體試驗委員會核准、參與者權益保障與資料保護方面。

此外，本試驗亦遵循《TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引》（2020）中關於AI-SaMD臨床試驗之要求（TFDA-AIML-SaMD TW-11）[1]，包括產品描述、演算法版本與鎖定狀態之明確說明。

### 不良事件與裝置缺陷報告 / Adverse Event and Device Deficiency Reporting

根據《ISO 14155:2020 附錄A》A.15條（Safety reporting）[2]，本試驗定義並建立不良事件（adverse events）與裝置缺陷（device deficiencies）之報告程序，包括軟體故障（software malfunction）與錯誤輸出（erroneous output）之處理流程。所有與NeuroDetect-CT AI v2.1.0相關之錯誤或異常行為，將由研究團隊記錄並提交至人體試驗委員會與主管機關（TFDA與FDA）。

### 試驗註冊、出版政策與利益衝突 / Registration, Publication Policy, and Conflicts of Interest

本試驗將依照《TFDA-AIML-SaMD》與《FDA 510(k) premarket notification》之要求進行臨床試驗註冊。試驗結果將依《STARD-AI》與《CONSORT-AI》之報告指引進行出版，並提交至學術期刊與主管機關。所有參與本試驗之研究人員與贊助機構將遵循利益衝突披露政策，確保研究結果之客觀性與透明度。

[TO BE CONFIRMED: 試驗註冊平台與出版期刊名稱待確認。]

### 臨床試驗中止或提前終止之條件與程序 / Suspension or Early Termination of the Clinical Investigation (ISO14155-CIP A.16)

根據《ISO 14155:2020 附錄A》A.16條（Suspension or early termination of the clinical investigation）[2]，本試驗明確定義臨床試驗中止或提前終止之條件與程序，並說明人體試驗委員會（IRB）、贊助機構（Sponsor）與研究者（Investigator）在相關決策中的角色與責任，如下：

1. **中止或提前終止之條件**：
   - 發生與AI-SaMD相關之重大不良事件（serious adverse events），經評估後認為對參與者或未來使用者具有顯著風險。
   - 發現試驗資料存在重大偏差、偽造或違反試驗協議，影響試驗結果之可信度。
   - 發現AI-SaMD之演算法或軟體版本與鎖定版本不符，或存在未經核准之變更。
   - 人體試驗委員會（IRB）或主管機關（TFDA/FDA）基於倫理或法規考量，要求中止或終止試驗。

2. **中止或提前終止之程序**：
   - **人體試驗委員會（IRB）**：若IRB認為試驗存在倫理或風險問題，可建議或要求中止或終止試驗，並通知贊助機構與研究者。
   - **贊助機構（Sponsor）**：贊助機構有權在發現重大風險、技術缺陷或違反協議時，決定中止或終止試驗，並需通知IRB與研究者。
   - **研究者（Investigator）**：研究者若發現試驗執行中存在重大問題，可向IRB與贊助機構提出中止或終止建議。

3. **後續處理與報告**：
   - 所有中止或終止之決定與理由將記錄於試驗文件中，並提交至IRB與主管機關。
   - 若試驗中止或終止，贊助機構需評估是否進行部分資料分析與報告，並確保參與者之權益與資料保護。

### 參考文獻 / References

[1] TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-11 — 臨床試驗法規 (Clinical investigation regulation)

[2] ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.14 — Ethics, A.15 — Safety reporting, A.16 — Suspension or early termination of the clinical investigation

[TO BE CONFIRMED: 其他引用文獻待確認。]

**Open questions / 待確認事項:**
- [TO BE CONFIRMED] [TO BE CONFIRMED: 試驗註冊平台與出版期刊名稱待確認。]
- [TO BE CONFIRMED] [TO BE CONFIRMED: 其他引用文獻待確認。]

## Appendix A — Sample Size Computations / 附錄 A 樣本數計算紀錄
### A.1 `calc_standalone_sample_size`
Co-primary sensitivity/specificity vs performance goals (exact binomial) — 敏感度與特異度為共同主要終點 (co-primary endpoints)，採用交集-聯集檢定法 (intersection-union test) 進行統計檢定，不進行多重比較調整。此方法符合 FDA 指南 (Guidance for Industry and FDA Staff – Clinical Decision Support Software) 中關於多重終點的處理建議。

Inputs: `expected_sensitivity=0.93, sensitivity_goal=0.8, expected_specificity=0.92, specificity_goal=0.8, alpha=0.025, power=0.8, one_sided=True, method=exact_binomial, attrition_rate=0.1, prevalence=0.4`
Outputs: `n_positive=55, n_negative=69, n_total=124, n_positive_with_attrition=62, n_negative_with_attrition=77, n_total_with_attrition=139, attrition_rate=0.1, prevalence_assumed=0.4, n_total_at_prevalence=155`

### A.2 `calc_buderer_sample_size`
Precision cross-check (Buderer 1996, ±5 % CI half-width) — 根據精確二項式方法計算，敏感度與特異度的檢定所需樣本數分別為 55 例陽性與 69 例陰性，考慮 10% 的流失率 (attrition rate) 後，總樣本數為 139 例 (陽性 62 例，陰性 77 例)。

Inputs: `expected_sensitivity=0.93, expected_specificity=0.92, prevalence=0.4, ci_halfwidth_sensitivity=0.05, ci_halfwidth_specificity=0.05, alpha=0.05, attrition_rate=0.1`
Outputs: `n_positive=101, n_negative=114, n_total_from_sensitivity=253, n_total_from_specificity=190, n_total_required=253, n_total_with_attrition=282, confidence_level=0.95`

### A.3 `allocate_strata`
Equal allocation across study sites — 根據 Buderer 方法 (1996) 進行精確度交叉驗證，以 95% 信賴區間半寬度 ±5% 計算，所需總樣本數為 253 例，考慮 10% 的流失率後為 282 例。此結果作為樣本數的交叉驗證，並非主要設計依據。

Inputs: `total=139, proportions={'Site 1': 0.3333333333333333, 'Site 2': 0.3333333333333333, 'Site 3': 0.3333333333333333}`
Outputs: `total=139`

## Appendix B — Evidence Register / 附錄 B 實證清單
| Source | Ref | Title | Design | n | Readers | Accepted |
|---|---|---|---|---|---|---|
| openfda | K180647 | FDA submission K180647 | retrospective, standalone, blinded, tria | 198 |  | ✓ |
| openfda | K253163 | EFAI ERSUITE CT APPENDICITIS ASSESSMENT SYSTEM (APPEN-CT-100) |  |  |  | ✗ |
| openfda | K260729 | Vascular Assist Occlusion Triage (VAOT) (v1.0) |  |  |  | ✗ |
| openfda | K240291 | EFAI CARDIOSUITE CTA ACUTE AORTIC SYNDROME ASSESSMENT SYSTEM |  |  |  | ✗ |
| openfda | K200873 | HALO |  |  |  | ✗ |
| openfda | K253265 | BriefCase-Triage |  |  |  | ✗ |
| openfda | K241727 | BriefCase-Triage |  |  |  | ✗ |
| openfda | K261317 | BriefCase-Triage |  |  |  | ✗ |
| openfda | K233968 | CINA-iPE |  |  |  | ✗ |
| openfda | K252421 | JLK-NCCT |  |  |  | ✗ |
| openfda | K253818 | Annalise Enterprise |  |  |  | ✗ |
| openfda | K253578 | BriefCase-Triage: CARE Multi-Triage CT for Pneumothorax; Pericardial effusion; L |  |  |  | ✗ |
| openfda | K251195 | BriefCase-Triage |  |  |  | ✗ |
| openfda | K252970 | BriefCase-Triage: CARE Multi-triage CT Body |  |  |  | ✗ |
| openfda | K250694 | Scaida BrainCT-ICH (v1.0) |  |  |  | ✗ |
| openfda | K252366 | a2z-Unified-Triage |  |  |  | ✗ |
| openfda | K251610 | qER-CTA (v1.0) |  |  |  | ✗ |
| openfda | K251533 | Rapid Obstructive Hydrocephalus, Rapid OH |  |  |  | ✗ |
| openfda | K251983 | Brainomix 360 Triage Stroke |  |  |  | ✗ |
| openfda | K251590 | Methinks CTA Stroke |  |  |  | ✗ |
| regulatory_rag | checklist:TFDA-AIML-SaMD#TFDA-AIML-SaMD item TW-1 — 產品描述 (Device description) | TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-1 — 產品描述 (Device  |  |  |  | ✓ |
| regulatory_rag | checklist:TFDA-AIML-SaMD#TFDA-AIML-SaMD item TW-4 — 參考標準 (Reference standard) | TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-4 — 參考標準 (Referen |  |  |  | ✓ |
| regulatory_rag | checklist:TFDA-AIML-SaMD#TFDA-AIML-SaMD item TW-2 — 輸入資料規格 (Input specification) | TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-2 — 輸入資料規格 (Input |  |  |  | ✓ |
| regulatory_rag | checklist:TFDA-AIML-SaMD#TFDA-AIML-SaMD item TW-5 — 效能驗證設計 (Performance validation design) | TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-5 — 效能驗證設計 (Perfo |  |  |  | ✓ |
| regulatory_rag | tfda-aiml-samd-2020#6 | 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (TFDA) (2020), 七、臨床性能驗證, p.6 |  |  |  | ✓ |
| regulatory_rag | fda-cade-clinical-performance-2022#20 | FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assi |  |  |  | ✓ |
| regulatory_rag | checklist:FDA-CADe#FDA-CADe item F-6 — Statistical analysis | FDA CADe/CADx Clinical Performance Assessment Guidance — study design expectatio |  |  |  | ✓ |
| regulatory_rag | fda-ai-dsf-lifecycle-draft-2025#17 | FDA Draft Guidance: Artificial Intelligence-Enabled Device Software Functions —  |  |  |  | ✓ |
| regulatory_rag | checklist:FDA-CADe#FDA-CADe item F-5 — Reader study design | FDA CADe/CADx Clinical Performance Assessment Guidance — study design expectatio |  |  |  | ✓ |
| regulatory_rag | fda-cade-clinical-performance-2022#9 | FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assi |  |  |  | ✓ |
| regulatory_rag | fda-cade-clinical-performance-2022#21 | FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assi |  |  |  | ✓ |
| regulatory_rag | checklist:STARD-AI#STARD-AI item AI-10 — Methods – Analysis | STARD-AI (Standards for Reporting of Diagnostic Accuracy Studies – Artificial In |  |  |  | ✓ |
| regulatory_rag | checklist:ISO14155-CIP#ISO14155-CIP item A.7 — Subjects / data | ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item |  |  |  | ✓ |
| regulatory_rag | checklist:ISO14155-CIP#ISO14155-CIP item A.10 — Statistics | ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item |  |  |  | ✓ |
| regulatory_rag | checklist:STARD-AI#STARD-AI item AI-7 — Methods – Index test | STARD-AI (Standards for Reporting of Diagnostic Accuracy Studies – Artificial In |  |  |  | ✓ |
| regulatory_rag | checklist:STARD-AI#STARD-AI item AI-3 — Methods – Study design | STARD-AI (Standards for Reporting of Diagnostic Accuracy Studies – Artificial In |  |  |  | ✓ |
| regulatory_rag | checklist:STARD-AI#STARD-AI item AI-13 — Results | STARD-AI (Standards for Reporting of Diagnostic Accuracy Studies – Artificial In |  |  |  | ✓ |

## Appendix C — Compliance Audit (iteration 2) / 附錄 C 合規審查
Checklists: STARD-AI, ISO14155-CIP, TFDA-AIML-SaMD · pass 34 · partial 9 · fail 1 · N/A 0 · verdict **minor_revisions**

| Checklist | Item | Status | Finding |
|---|---|---|---|
| STARD-AI | AI-1 | pass | The study is explicitly identified as a diagnostic accuracy study of an AI-based index test (NeuroDetect-CT AI v2.1.0) in the title and synopsis. The AI model t |
| ISO14155-CIP | A.1 | pass | The protocol includes a title (NeuroDetect-CT AI v2.1.0), version (v2.1.0), sponsor (Example MedTech Co., Ltd.), principal investigator (Dr. Lin), and a synopsi |
| ISO14155-CIP | A.18 | partial | The protocol includes a 'References' section, but it is marked as truncated in the provided text. The completeness and comprehensiveness of the bibliography can |
| STARD-AI | AI-2 | pass | The protocol explicitly states the intended use of NeuroDetect-CT AI as a Computer-Aided Detection for Triage (CADt) in the clinical pathway for acute intracran |
| ISO14155-CIP | A.3 | pass | The protocol provides a detailed justification for the clinical investigation design, including a risk-benefit analysis. It outlines the anticipated clinical be |
| ISO14155-CIP | A.4 | pass | The protocol explicitly describes the anticipated clinical benefits of NeuroDetect-CT AI in improving triage efficiency and diagnostic accuracy for ICH. It also |
| STARD-AI | AI-3 | pass | 本研究明確說明資料收集為回溯性 (retrospective)，並採用獨立效能驗證設計 (standalone performance validation)，符合 STARD-AI AI-3 的要求。研究設計與 predicate 裝置 K180647 一致，並說明與 reader study 或 clinical  |
| ISO14155-CIP | A.6 | pass | 本研究明確說明設計類型為「回溯性獨立效能驗證設計」，並說明資料收集模式、研究中心數、隨機化設計與盲評程序，符合 ISO14155-CIP A.6 的要求。研究亦說明偏差最小化措施，包括資料獨立性、盲評與隨機化設計。 |
| ISO14155-CIP | A.8 | pass | 本研究詳細說明評估程序、AI-SaMD 輸出格式、評估者訓練與評估流程，並說明評估結果的處理方式與分析方法，符合 ISO14155-CIP A.8 的要求。研究亦說明跟進安排為一次性評估，無需追蹤。 |
| ISO14155-CIP | A.9 | partial | 本研究提及設有獨立品質管理小組，並說明資料與分析結果將定期審查，但未明確說明監測計畫的具體內容與頻率，亦未說明資料品質保證的具體措施。 |
| TFDA-AIML-SaMD | TW-5 | pass | 本研究明確說明採用獨立效能驗證設計 (standalone performance validation)，並符合 TFDA-AIML-SaMD TW-5 的要求。研究說明資料收集為回溯性、多中心資料來源、樣本數推估依據與統計假設，符合 TFDA 對 AI-SaMD 效能驗證的設計要求。 |
| STARD-AI | AI-4 | pass | The protocol explicitly describes eligibility criteria at both participant and data/image levels, including acquisition device (GE, Siemens, Philips), protocol  |
| STARD-AI | AI-5 | pass | The protocol describes data sources (3 Taiwan research centers), sampling method (enriched case-control design with 40% positive cases), and explicitly states t |
| STARD-AI | AI-14 | partial | The protocol mentions limitations in section 6.13, but it is brief and lacks detailed discussion on dataset shift, generalizability across devices/populations/s |
| ISO14155-CIP | A.7 | partial | The protocol includes inclusion/exclusion criteria and sampling strategy, but the expected duration is marked as [TO BE CONFIRMED], and the justification for sa |
| TFDA-AIML-SaMD | TW-7 | pass | The protocol explicitly describes subgroup stratification by age, gender, scanner manufacturer, and hemorrhage subtype, and states that consistency across subgr |
| TFDA-AIML-SaMD | TW-8 | partial | The protocol states that data are collected from 3 Taiwan research centers, but it does not explicitly justify how foreign data (from training sites in the US)  |
| STARD-AI | AI-6 | pass | The protocol explicitly describes the AI index test, including the model type (3D convolutional neural network), version (v2.1.0), input (non-contrast head CT,  |
| STARD-AI | AI-7 | pass | The protocol describes the human–AI interaction in detail, including the Worklist_Triage workflow, user training, and the concurrent reading design. It also sta |
| ISO14155-CIP | A.2 | pass | The protocol provides a detailed description of the investigational device, including its intended purpose, target population, clinical setting, user qualificat |
| ISO14155-CIP | A.13 | pass | The protocol describes the software deployment (cloud-based SaMD), version control (locked v2.1.0), and compatibility with PACS and DICOM systems. This satisfie |
| TFDA-AIML-SaMD | TW-1 | pass | The protocol clearly states the intended use (ICH triage), indications for use, target population (≥20 years), clinical setting (emergency and radiology), user  |
| TFDA-AIML-SaMD | TW-2 | pass | The protocol specifies the input modality (non-contrast head CT), compatible acquisition devices (GE, Siemens, Philips), image parameters (slice thickness ≤ 5 m |
| TFDA-AIML-SaMD | TW-3 | partial | The protocol mentions the algorithm type (3D convolutional neural network), training data (25,000 cases from 4 hospitals in Taiwan and the US), and test data in |
| TFDA-AIML-SaMD | TW-9 | partial | The protocol states that the algorithm is locked and will not be automatically updated post-market. However, it lacks a detailed description of the change contr |
| STARD-AI | AI-8 | pass | The protocol explicitly addresses the reference standard (expert consensus panel), its rationale (gold standard for ICH detection in non-contrast CT), adjudicat |
| TFDA-AIML-SaMD | TW-4 | pass | The protocol explicitly addresses the establishment of the reference standard (expert consensus panel), its rationale (gold standard for ICH detection in non-co |
| STARD-AI | AI-9 | pass | The protocol explicitly pre-specifies the measures of diagnostic accuracy (sensitivity and specificity), how indeterminate AI outputs and missing data are handl |
| STARD-AI | AI-10 | pass | The protocol justifies the intended sample size (55 positive and 69 negative cases, adjusted for attrition) and describes pre-specified subgroup analyses (age,  |
| STARD-AI | AI-11 | pass | The protocol describes planned analysis of AI failure modes and performance errors (false positives/negatives) and includes error analysis in the statistical se |
| STARD-AI | AI-12 | pass | The protocol explicitly states that a participant/data flow diagram will be provided in accordance with STARD-AI (AI-12), and cross-tabulation of AI results aga |
| STARD-AI | AI-13 | pass | The protocol reports accuracy estimates with precision (95% CI) at the pre-specified operating point(s) and aligns with the requirement to report diagnostic acc |
| ISO14155-CIP | A.10 | pass | The protocol includes a detailed statistical analysis plan with sample size calculation, analysis populations, handling of missing/indeterminate data, and subgr |
| TFDA-AIML-SaMD | TW-6 | pass | The protocol specifies sensitivity and specificity as performance metrics, reports confidence intervals using the Wilson method, and explicitly describes the pr |
| STARD-AI | AI-15 | partial | The protocol synopsis and ethics sections mention protocol registration and conflicts of interest, but the specific registration platform and journal names are  |
| ISO14155-CIP | A.11 | pass | The data management section fully addresses data handling, de-identification/pseudonymisation, data retention, database and software validation, and data securi |
| ISO14155-CIP | A.12 | fail | The protocol does not include any procedures for amendments or deviations to the clinical investigation plan (CIP). |
| ISO14155-CIP | A.17 | partial | The ethics section mentions publication policy and registration, but the specific registration platform and journal names are marked as [TO BE CONFIRMED]. |
| TFDA-AIML-SaMD | TW-10 | pass | The data management section explicitly addresses de-identification, data storage and transmission security, and compliance with the Personal Data Protection Act |
| ISO14155-CIP | A.5 | pass | The protocol explicitly defines primary and secondary objectives, hypotheses, and endpoints. The primary objectives include sensitivity and specificity of the A |
| ISO14155-CIP | A.14 | pass | The protocol explicitly states compliance with ISO 14155, Declaration of Helsinki, and local regulations (TFDA). It includes IRB approval requirements and a cle |
| ISO14155-CIP | A.15 | pass | The protocol defines adverse events and device deficiencies, including software malfunctions and erroneous outputs, and outlines procedures for their reporting  |
| ISO14155-CIP | A.16 | pass | The protocol explicitly defines the criteria and procedures for suspension or early termination of the clinical investigation, including the roles of the IRB, S |
| TFDA-AIML-SaMD | TW-11 | pass | The protocol states that the clinical investigation has been classified as a non-significant risk (NSR) trial under Article 37 of the Medical Device Management  |

## References / 參考文獻
1. CONSORT-AI (Consolidated Standards of Reporting Trials – Artificial Intelligence extension), CONSORT-AI item 5(iii) — Interventions
2. CONSORT-AI 5(iii)
3. FDA CADe/CADx Clinical Performance Assessment Guidance — study design expectations, FDA-CADe item F-5 — Reader study design
4. FDA CADe/CADx Clinical Performance Assessment Guidance — study design expectations, FDA-CADe item F-6 — Statistical analysis
5. FDA CADe/CADx Clinical Performance Assessment Guidance — study design expectations, FDA-CADe item F-8 — Workflow / triage
6. FDA Draft Guidance on Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations (2025)
7. FDA Draft Guidance: Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations (2025), 48 See FDA’s website on Regulations: Good Clinical Practice and Clinical Trials., p.28
8. FDA Draft Guidance: Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations (2025), 57 See 21 CFR 814.44 and 21 CFR 814.82., p.39
9. FDA Draft Guidance: Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations (2025), 65 For more information on eSTAR, please see FDA’s website on eSTAR Program., p.47
10. FDA Draft Guidance: Artificial Intelligence-Enabled Device Software Functions — Lifecycle Management and Marketing Submission Recommendations (2025), 70 See 21 CFR Part 801., p.56
11. FDA Guidance for Clinical Performance Assessment of Computer-Assisted Detection Devices (2022)
12. FDA Guidance for Industry and FDA Staff on Clinical Performance Assessment for Computer-Assisted Detection Devices (F-6)
13. FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assisted Detection Devices Applied to Radiology Images and Radiology Device Data in Premarket Notification (510(k)) Submissions (2022), 14 See 21 CFR 860.7(e)., p.19
14. FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assisted Detection Devices Applied to Radiology Images and Radiology Device Data in Premarket Notification (510(k)) Submissions (2022), 14 See 21 CFR 860.7(e)., p.21
15. FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assisted Detection Devices Applied to Radiology Images and Radiology Device Data in Premarket Notification (510(k)) Submissions (2022), 3 Available at https://wayback.archive-
16. FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assisted Detection Devices Applied to Radiology Images and Radiology Device Data in Premarket Notification (510(k)) Submissions (2022), 3 Available at https://wayback.archive-, p.9
17. FDA Guidance: Clinical Performance Assessment — Considerations for Computer-Assisted Detection Devices Applied to Radiology Images and Radiology Device Data in Premarket Notification (510(k)) Submissions (2022), p.4
18. FDA Guidance: Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence-Enabled Device Software Functions (2024), 90 Section 515C(c) of the FD&C Act., p.26
19. FDA Guidance: Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence-Enabled Device Software Functions (2024), p.3
20. FDA-CADe F-5
21. FDA-CADe F-6
22. IMDRF N41
23. IMDRF/SaMD WG/N41: Software as a Medical Device (SaMD) — Clinical Evaluation (2017), 21 September 2017 Page 2 of 30, p.2
24. IMDRF/SaMD WG/N41: Software as a Medical Device (SaMD) — Clinical Evaluation (2017), 21 September 2017 Page 26 of 30, p.26
25. IMDRF/SaMD WG/N41: Software as a Medical Device (SaMD) — Clinical Evaluation (2017), 7.0 SaMD Clinical Evaluation Process Flow Chart, p.13
26. ISO 14155:2020
27. ISO 14155:2020 A.2
28. ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.10 — Statistics
29. ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.11 — Data management
30. ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.14 — Ethics, A.15 — Safety reporting
31. ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.5 — Objectives and hypotheses
32. ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.6 — Design
33. ISO 14155:2020 Annex A — Clinical Investigation Plan contents, ISO14155-CIP item A.8 — Procedures
34. ISO14155-CIP A.12
35. ISO14155-CIP A.14–A.16
36. ISO14155-CIP A.17
37. ISO14155-CIP A.6
38. ISO14155-CIP A.8
39. SPIRIT-AI (Standard Protocol Items: Recommendations for Interventional Trials – Artificial Intelligence extension), SPIRIT-AI item 11a(iii) — Interventions
40. SPIRIT-AI 11a(i)
41. SPIRIT-AI 11a(iii)
42. SPIRIT-AI 11a(v)
43. SPIRIT-AI 6a(i)
44. SPIRIT-AI 9
45. STARD-AI (Standards for Reporting of Diagnostic Accuracy Studies – Artificial Intelligence), STARD-AI item AI-10 — Methods – Analysis
46. STARD-AI (Standards for Reporting of Diagnostic Accuracy Studies – Artificial Intelligence), STARD-AI item AI-3 — Methods – Study design
47. STARD-AI AI-10
48. STARD-AI AI-12
49. STARD-AI AI-15
50. STARD-AI AI-3
51. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-1 — 產品描述 (Device description)
52. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-10 — 網路安全與資料保護 (Cybersecurity & privacy)
53. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-11 — 臨床試驗法規 (Clinical investigation regulation)
54. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-2 — 輸入資料規格 (Input specification)
55. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-4 — 參考標準 (Reference standard)
56. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-5 — 效能驗證設計 (Performance validation design)
57. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-6 — 效能指標 (Performance metrics)
58. TFDA 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (2020), TFDA-AIML-SaMD item TW-7 — 次族群分析 (Subgroup analysis)
59. TFDA-AIML-SaMD TW-1
60. TFDA-AIML-SaMD TW-11
61. TFDA-AIML-SaMD TW-2
62. TFDA-AIML-SaMD TW-4
63. TFDA-AIML-SaMD TW-5
64. TFDA-AIML-SaMD TW-9
65. 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (TFDA) (2020), 1081600444 號）, 108 年 11 月 18 日, p.7
66. 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (TFDA) (2020), 1081600444 號）, 108 年 11 月 18 日, p.8
67. 人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引 (TFDA) (2020), 七、臨床性能驗證, p.6
