# Gemini 規劃文件正確性檢視與修正紀錄

> 對象：`ai_samd.md`（以 Gemini 先行規劃的《AI-SaMD Clinical Protocol Copilot》設計文件）
> 檢視日期：2026-10-23　檢視方式：逐條比對公開法規文件、API 文件與套件現況（可連線者皆實際驗證）

整體評價：**架構方向正確、可實作**。四模組輸入、五個 MCP 伺服器分工、Multi-agent 流程、十章節輸出都合理。
但有 **3 處概念性錯誤、6 處事實性錯誤、1 個關鍵設計缺口（GB10 上的 LLM 推論層完全未規劃）**。以下逐項說明，並標註本專案如何修正。

---

## 一、概念性錯誤（會影響計畫書是否符合審查要求）

### 1. 把 SPIRIT-AI 當成所有 AI 醫材臨床研究的「萬用查核表」 ❌
- **問題**：SPIRIT-AI（Cruz Rivera et al., *Lancet Digit Health* 2020;2:e549–60，另刊於 *Nat Med* 與 *BMJ*）是 **介入性臨床試驗（RCT）計畫書**的報告規範；15 個新增項目（12 extensions + 3 elaborations）這個數字正確。
- 但 AI-SaMD 最常見的 **回溯性獨立效能驗證（standalone）與 MRMC 閱片試驗屬於「診斷準確度研究」**，對應規範是 **STARD 2015 / STARD-AI（Sounderajah et al., *Nat Med* 2025）**，風險偏差評估用 QUADAS-2；計畫書「結構」則應依 **ISO 14155:2020 Annex A（Clinical Investigation Plan 必要內容）**。預後/風險預測模型則用 **TRIPOD+AI（BMJ 2024）**。
- **修正**：`mcp-regulatory-rag` 的 `select_checklists()` 依 `design_type × samd_category × jurisdictions` 決定主/輔查核表（standalone/MRMC → STARD-AI 主、SPIRIT-AI 僅借用 10(ii)、11a(i)–(vi)、22(ii) 作為器材描述良好實務；RCT → SPIRIT-AI + CONSORT-AI；Prognostic → TRIPOD+AI；ISO 14155 CIP 與 IMDRF N41 永遠列入結構性檢核）。八份查核表以 YAML 結構化於 `mcp-servers/mcp-regulatory-rag/src/mcp_regulatory_rag/checklists/`。

### 2. `verify_spirit_ai_compliance(draft_text)` 放在 MCP 伺服器內 ❌
- **問題**：逐項判斷草稿是否「符合」需要 LLM 推理；MCP 伺服器應是確定性工具，不應自行呼叫 LLM（除非走 MCP sampling，而本地 vLLM/Ollama 的 host 端不一定支援）。
- **修正**：拆成兩層——RAG 伺服器提供 **確定性 keyword 預篩** `prescreen_checklist_coverage()`（likely_covered / weak / missing）＋查核表條文；後端 **Auditor Agent** 以 LLM 逐項判定 pass/partial/fail 並產生「修訂需求 → Writer 回修」迴圈（預設最多 2 輪）。

### 3. 把 Human-in-the-loop 畫成流程箭頭，但沒有狀態持久化 ❌
- **問題**：「Harvester → 使用者確認 → Biostat」中間是一個會停數小時到數天的閘門；若 backend 重啟，流程必須能從閘門恢復。
- **修正**：Run 狀態（triage / evidence / sap / sections / audits）全部以 JSON 持久化在 PostgreSQL（測試用 SQLite）；`awaiting_evidence_confirmation` 為正式 stage，`POST /api/runs/{id}/confirm-evidence` 從 DB 載回狀態後續跑第 3–5 階段；事件以 SSE 推送並持久化。

---

## 二、事實性錯誤 / 需更新

| # | Gemini 文件內容 | 實際情況（已驗證） | 修正 |
|---|---|---|---|
| 1 | TFDA 指引名為「人工智慧/機器學習技術之電腦輔助偵測(CADe)及電腦輔助診斷(CADx)醫療器材查驗登記技術指引」、「AI/ML 醫療器材臨床評估技術指引」 | 食藥署 2020-09-11 公告的是 **《人工智慧/機器學習技術之醫療器材軟體查驢登記技術指引》**（FDA器字第1091607253號，PDF 可自 fda.gov.tw 下載，541 KB）；另有 2021 成立之「智慧醫療器材專案辦公室」提供諮詢。查無上述兩個名稱的指引。 | `sources.yaml` 收錄正確 PDF 連結；`tfda_aiml_samd.yaml` 以該指引之證據要項建立 11 項檢核 |
| 2 | TFDA 專區網址 `aicenter.fda.gov.tw` | 本環境無法解析/連線該網域（fda.gov.tw 正常），**無法證實其存在**，請以 www.fda.gov.tw 為準 | 文件僅引用 fda.gov.tw |
| 3 | 「台灣臨床試驗資訊網 taiwanclinicaltrials.tw」 | 查無此站。實際為 CDE 建置之 **台灣藥品臨床試驗資訊網**（www1.cde.org.tw/ct_taiwan/），以**藥品**為主、無公開 API；**醫療器材**臨床試驗在台灣沒有可程式化查詢的公開登錄系統 | 不建 MCP；國際登錄以 ClinicalTrials.gov API v2 為主（可用 `countries` 過濾 Taiwan） |
| 4 | openFDA 可查 510(k) **與 De Novo** | openFDA **只有** `/device/510k.json`，**沒有 De Novo endpoint**。De Novo 決定摘要在 `accessdata.fda.gov/cdrh_docs/reviews/DENxxxxxx.pdf`；FDA AI-enabled device list 是 **CSV/XLSX/XML 下載檔**（非 API，約 1,614 筆，2026-09），不是「openFDA」資料 | `mcp-openfda-predicate` 分別實作 510(k) 查詢、510(k)/De Novo PDF 摘要擷取、AI 清單 CSV 解析 |
| 5 | 510(k) 範例 `K210123` | 該號碼無摘要 PDF（404）。摘要 PDF 路徑規則為 `cdrh_docs/pdf{YY}/K{YY}xxxx.pdf`（去除前導 0），且需瀏覽器 User-Agent，否則 accessdata 回 404 | 已實作路徑規則與 UA；已實測可取得 K183285、K253163、K173542、DEN170073 |
| 6 | 用 Python **FastMCP** 寫 MCP 伺服器 | 官方 `mcp` Python SDK 已升至 **2.x**：`FastMCP` 改名 `MCPServer`（`from mcp.server.mcpserver import MCPServer`），`mcp.server.fastmcp` import 會直接失敗；獨立套件 `fastmcp` 已到 4.x 且依賴 `mcp>=2`；`streamablehttp_client` 改為 `streamable_http_client`；HTTP 層改用 `httpx2` | 全部伺服器以 `mcp>=2.3` 的 `MCPServer` 實作，後端用 `mcp.client.client.Client` |
| 7 | JSON Schema 使用 `"example"` 關鍵字 | draft-07 沒有 `example`（應為 `examples` 陣列）；`predicate_device_id` 應為清單 | 以 pydantic 模型為單一真實來源，`GET /api/meta/schema` 輸出 JSON Schema |
| 8 | Next.js 15 | 目前為 16.x（App Router）；Tailwind v4 | 前端採 Next 16.4 / React 19 / zod 4 |
| 9 | SPIRIT-AI 出處未註 | *Lancet Digit Health* 2020（非僅 Nat Med）；STARD-AI 已於 2025 正式發表（Nat Med 31(10)） | 查核表 YAML 註明出處與「請核對原表」警語 |

---

## 三、關鍵設計缺口：GB10（DGX Spark）上的 LLM 推論層

Gemini 文件完全沒有提到 **要用哪個模型、在哪裡推論**。使用者指定以 GB10 落地，這是整個系統最核心的部署決策：

- **硬體事實**：DGX Spark = NVIDIA GB10 Grace Blackwell、20 核 Arm CPU（10×Cortex-X925 + 10×Cortex-A725）、Blackwell GPU、**128 GB LPDDR5x 統一記憶體（273 GB/s）**、約 1 PFLOP NVFP4、DGX OS（Ubuntu 衍生）。**CPU 架構是 aarch64** → 所有 Docker image 都必須有 `linux/arm64` 版本（Postgres、Qdrant、Ollama、node、python 皆有；自建 image 需在 Spark 上原生 build）。
- **修正**：
  - 後端 LLM 層抽象為 `LLMClient`，預設 `LLM_PROVIDER=local` 走 **OpenAI-compatible `/v1/chat/completions`**（Ollama / NVIDIA vLLM 容器 / NIM 皆相容），結構化輸出三段式降級（`json_schema` → `json_object` → 純文字擷取），自動去除 `<think>` 推理段；可選 `anthropic`（官方 SDK，`claude-opus-5-5`，串流 + `output_config.format`）。
  - 向量嵌入同樣走 OpenAI-compatible `/v1/embeddings`（Ollama `bge-m3`，中英雙語），MCP RAG 伺服器不依賴 torch；離線時退回確定性 hashing embedder（僅靠 BM25）。
  - `docker-compose.yml` 提供 `ollama` / `vllm` 兩種 profile，GPU 以 `deploy.resources.reservations.devices` 保留；詳見 `docs/GB10_DEPLOYMENT.md`。

---

## 四、統計方法檢視

| 項目 | Gemini | 檢視 |
|---|---|---|
| 單一比例 vs 效能目標（performance goal） | 提到 Exact Binomial | ✅ 正確。實作同時提供常態近似與 **精確二項設計**（回傳臨界成功數、實際 α 與 power，並說明鋸齒現象）；co-primary（敏感度 AND 特異度）採 intersection-union，不需 α 校正 |
| Buderer 法 | 提到 | ✅ 正確（Buderer 1996，依盛行率換算總收案數） |
| MRMC 樣本數：OR 模型 | 提到 `calc_mrmc_sample_size(num_readers, delta_auc, var_components)` | ✅ 方向正確，但需明確：**必須有 pilot 變異成分**（σ²_TR、σ²_ε、Cov1–3，依 pilot 案例數縮放）。實作 Hillis 2011 的 OR F 檢定 + Hillis ddf；無 pilot 資料時僅能用「示意值」並在 SAP 大聲標示。**建議以 RJafroc / iMRMC 交叉驗證**後再用於送審 |
| 單尾 α=0.025 | 提到 | ✅ 為 FDA 慣例；輸入 schema 明確加入 `alpha_sidedness` |
| 缺漏 | — | 補上：配對設計（同一批案例有/無 AI，McNemar / Connor 1987）、AUROC（Hanley–McNeil）、兩獨立組優效/不劣效（RCT）、分層配置 |

---

## 五、其他建議（已納入）

1. **資料獨立性**（測試集不得用於訓練/調參/閾值選定）是 STARD-AI 與 TFDA 指引都要求的，輸入 schema 新增 `training_data_summary.independence_statement`。
2. 加入 **clinical_role**（replace / add-on / triage）與 **sampling_strategy / target_prevalence**，因為 FDA CADe 指引與 STARD-AI 的設計判斷都繫於此。
3. CE MDR 應引用 **MDCG 2020-1**（軟體臨床評估）；台灣應引用 **人體研究法**、**醫療器材優良臨床試驗作業規範**、**醫療器材管理法 §37 無顯著風險態樣**（食藥署 2022-02 有 AI/ML CADe 胸部 X 光初步效能評估屬無顯著風險之示例）。
4. **LangGraph 非必要**：流程是固定的五階段 + 一個閘門，用輕量 pipeline（約 150 行）即可，少一組會頻繁改版的依賴；若未來需要動態分支再引入。
5. Qdrant Hybrid search：Qdrant 只提供 IDF modifier，**BM25 的 tokenization 必須在 client 端做**；中文需 jieba 斷詞（已實作，同時支援英文）。
6. 法規 PDF 不入 git（版權與體積），以 `sources.yaml` + 一鍵 ingest 下載；SPIRIT-AI 原文、ISO 14155 需使用者自備（授權）。
7. 所有 LLM 產出附帶「AI 輔助草稿、需專業人員核對」免責聲明，並以 **[TO BE CONFIRMED]** 標記無法由輸入或證據支持的內容；統計數字只允許來自 `mcp-biostat-calc` 的輸出。

---

## 六、Gemini 文件中正確、予以保留的部分

- 核心價值主張與雙語定位、四模組輸入設計、五個 MCP 伺服器分工、Multi-agent 五階段流程、十章節輸出、三階段 MVP roadmap。
- 外部資料源：ClinicalTrials.gov API v2（已驗證 v2.0.5）、NCBI E-utilities、openFDA 510(k)、FDA CADe 臨床效能評估指引（2012/2022）、FDA PCCP 指引（2024 final）、IMDRF N41（2017）、SPIRIT-AI 15 項。
- 統計工具以 SciPy 確定性運算、杜絕 LLM 數學幻覺的原則。
