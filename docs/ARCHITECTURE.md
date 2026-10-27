# 系統架構 | System Architecture

> AI-SaMD Clinical Protocol Copilot 的架構說明，中英對照。
> Architecture of the AI-SaMD Clinical Protocol Copilot, in Traditional Chinese and English.

**目錄 Contents**
1. [設計原則 Design principles](#1-設計原則--design-principles)
2. [元件 Components](#2-元件--components)
3. [執行流程與狀態機 Pipeline & state machine](#3-執行流程與狀態機--pipeline--state-machine)
4. [一次執行的時序 Sequence of a run](#4-一次執行的時序--sequence-of-a-run)
5. [資料流與信任邊界 Data flow & trust boundaries](#5-資料流與信任邊界--data-flow--trust-boundaries)
6. [GB10 部署拓撲 Deployment topology on the GB10](#6-gb10-部署拓撲--deployment-topology-on-the-gb10)
7. [LLM 層 LLM layer](#7-llm-層--llm-layer)
8. [確定性與生成式的分工 Deterministic vs. generative work](#8-確定性與生成式的分工--deterministic-vs-generative-work)
9. [資料模型與 API Data model & API](#9-資料模型與-api--data-model--api)
10. [技術選型 Technology stack](#10-技術選型--technology-stack)
11. [設計取捨 Design trade-offs](#11-設計取捨--design-trade-offs)
12. [實測效能 Measured performance](#12-實測效能--measured-performance)

---

## 1. 設計原則 | Design principles

| 原則 Principle | 說明 Meaning |
|---|---|
| **數字不靠模型 Numbers never come from the model** | 樣本數、信賴區間、MRMC 檢定力全部由 `mcp-biostat-calc` 確定性計算；LLM 只負責把結果寫成文字。<br/>Sample sizes, CIs and MRMC power are computed deterministically by `mcp-biostat-calc`; the LLM only turns results into prose. |
| **引用必須可追溯 Every citation is traceable** | 章節只能引用檢索到的 K 編號、NCT 編號、PMID 與法規條文；無法支持的內容標記 `[TO BE CONFIRMED]`。<br/>Sections may only cite retrieved K-numbers, NCT IDs, PMIDs and guidance clauses; unsupported content is marked `[TO BE CONFIRMED]`. |
| **人在迴圈中 Human in the loop** | 實證檢索後強制暫停，由使用者確認採用哪些證據，才進入統計與撰寫。<br/>The run stops after evidence retrieval until a person confirms which evidence to use. |
| **資料留在本機 Local-first** | 模型、資料庫、向量庫都在 GB10；只有公開關鍵字會送去查外部資料庫。<br/>Model, database and vector store run on the GB10; only public keywords leave the machine. |
| **工具與推理分離 Tools separate from reasoning** | MCP 伺服器不呼叫 LLM、不執行模型產生的指令；流程由後端程式決定，不讓模型自由選工具。<br/>MCP servers never call an LLM or run model-generated commands; the backend decides the workflow, the model does not pick tools freely. |
| **部分失敗不拖垮全局 Partial failure stays partial** | 外部來源失敗、單章撰寫失敗、修訂失敗都記為警示並繼續，整個執行不會因一處失敗而中止。<br/>A failed source, section or revision becomes a warning and the run continues. |

---

## 2. 元件 | Components

```mermaid
flowchart LR
    subgraph Browser["瀏覽器 Browser"]
        U["使用者 User"]
    end
    subgraph FE["前端容器 frontend · Next.js 16"]
        PAGES["頁面 Pages<br/>精靈 · 工作區 · 編輯器<br/>wizard · workspace · editor"]
        PROXY["同源代理 Same-origin proxy<br/>/backend/api/* → backend<br/>附加 API 金鑰 adds API key"]
    end
    subgraph BE["後端容器 backend · FastAPI"]
        API["REST + SSE API"]
        RM["執行管理 RunManager<br/>背景任務 · 事件廣播<br/>background tasks · event fan-out"]
        PIPE["流程 Pipeline<br/>五個代理 five agents"]
        LLMC["LLM 客戶端 LLM client"]
        MCPC["MCP 客戶端 MCP client"]
        EXP["匯出 Exporters<br/>Markdown · .docx"]
    end
    subgraph TOOLS["MCP 伺服器 MCP servers"]
        T1["biostat-calc"]
        T2["clinicaltrials"]
        T3["openfda-predicate"]
        T4["pubmed-evidence"]
        T5["regulatory-rag"]
    end
    PG[("PostgreSQL")]
    QD[("Qdrant")]
    OL[("Ollama / vLLM")]
    EXT[["外部公開 API External public APIs<br/>ClinicalTrials.gov · openFDA · accessdata.fda.gov · NCBI"]]

    U --> PAGES --> PROXY --> API
    API --> RM --> PIPE
    PIPE --> LLMC --> OL
    PIPE --> MCPC --> T1 & T2 & T3 & T4 & T5
    API --> EXP
    RM --> PG
    T5 --> QD
    T5 -. 嵌入 embeddings .-> OL
    T2 & T3 & T4 --> EXT
```

| 元件 Component | 位置 Location | 職責 Responsibility |
|---|---|---|
| 前端頁面 Frontend pages | `frontend/app`, `frontend/components` | 四步驟精靈（zod 驗證，與後端 pydantic 對應）、執行工作區（進度、即時事件、實證確認）、編輯器、SAP / 審查 / 匯出分頁。<br/>Four-step wizard (zod mirrors the backend pydantic schema), run workspace (progress, live events, evidence confirmation), editor, SAP / audit / export tabs. |
| 同源代理 Same-origin proxy | `frontend/app/backend/[...path]/route.ts` | 只轉送 `/api/*`，逐段檢查路徑，伺服器端附加 `X-API-Key`，串流回傳（SSE 與下載不中斷）。<br/>Forwards only `/api/*`, validates each path segment, adds `X-API-Key` server-side, streams responses (SSE and downloads pass through). |
| API 層 API layer | `backend/app/api/routes.py`, `backend/app/main.py` | 專案、執行、事件（SSE）、實證確認、章節編輯、取消、匯出；可選的 API 金鑰中介層。<br/>Projects, runs, events (SSE), evidence confirmation, section edits, cancel, export; optional API-key middleware. |
| 執行管理 RunManager | `backend/app/api/manager.py` | 以背景任務跑流程，每個執行有自己的 MCP 管理器（工具呼叫計數獨立），事件存入資料庫並廣播給 SSE 訂閱者。<br/>Runs the pipeline as background tasks; each run gets its own MCP manager (per-run tool counts); events are persisted and fanned out to SSE subscribers. |
| 流程與代理 Pipeline & agents | `backend/app/agents/` | `triage` → `harvester` → 人工閘門 → `biostat` → `writer` → `auditor`（含修訂迴圈）。<br/>`triage` → `harvester` → human gate → `biostat` → `writer` → `auditor` (with revision loop). |
| LLM 客戶端 LLM client | `backend/app/llm/` | 本地 OpenAI 相容（Ollama / vLLM / NIM）、Anthropic SDK、測試用假模型；結構化輸出與截斷處理。<br/>Local OpenAI-compatible (Ollama / vLLM / NIM), Anthropic SDK, a fake model for tests; structured output and truncation handling. |
| MCP 客戶端 MCP client | `backend/app/mcp_client/` | 官方 `mcp` 2.x `Client`，以 streamable HTTP 連線；測試時可直接掛載伺服器於同一行程。<br/>Official `mcp` 2.x `Client` over streamable HTTP; servers can be mounted in-process for tests. |
| 匯出 Exporters | `backend/app/exporters/` | 組合摘要表、十章節、附錄（計算紀錄、實證清單、審查結果）、參考文獻；轉 Word。<br/>Assembles synopsis table, ten sections, appendices (computations, evidence register, audit), references; converts to Word. |
| MCP 伺服器 MCP servers | `mcp-servers/*` | 五個獨立 Python 套件，各自有測試；見 README 的工具一覽。<br/>Five independent Python packages with their own tests; see the tool catalogue in the README. |

---

## 3. 執行流程與狀態機 | Pipeline & state machine

```mermaid
stateDiagram-v2
    [*] --> created
    created --> triage : 建立執行 start run
    triage --> harvest
    harvest --> awaiting_evidence_confirmation
    awaiting_evidence_confirmation --> biostat : 使用者確認實證 user confirms evidence
    biostat --> write
    write --> audit
    audit --> audit : 未達項目退回修訂（最多 2 輪）<br/>revise failed items (max 2 rounds)
    audit --> completed
    triage --> failed
    harvest --> failed
    biostat --> failed
    write --> failed
    audit --> failed
    created --> cancelled : 取消 cancel
    triage --> cancelled
    harvest --> cancelled
    awaiting_evidence_confirmation --> cancelled
    biostat --> cancelled
    write --> cancelled
    audit --> cancelled
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

| 階段 Stage | 輸入 Input | 輸出（存入 `RunState`）Output (stored in `RunState`) |
|---|---|---|
| `triage` | `ProtocolInput` | `TriageDecision`：研究型態、法規路徑、風險評估、適用查核表（主要 / 輔助 / 結構）<br/>Study archetype, pathways, risk assessment, applicable checklists (primary / supporting / structural) |
| `harvest` | 疾病、模態、產品代碼、predicate 編號<br/>Disease, modality, product code, predicate numbers | `EvidenceMatrix`：實證項目、基準矩陣、基準效能、缺口警示<br/>Evidence items, benchmark rows, baseline performance, gaps |
| `awaiting_evidence_confirmation` | 使用者的 `EvidenceConfirmation`<br/>User's `EvidenceConfirmation` | 勾選結果、備註、基準值覆寫<br/>Accepted items, notes, baseline overrides |
| `biostat` | 統計假設 + 已確認的基準值<br/>Statistical assumptions + confirmed baselines | `StatisticalAnalysisPlan`：每筆計算的輸入輸出、最終樣本數、分層配置、SAP 敘述<br/>Every computation's inputs/outputs, final sample size, allocation, SAP narrative |
| `write` | 以上全部 + 法規條文檢索<br/>All of the above + guidance retrieval | 十個 `DraftSection`（含引用與待確認事項）<br/>Ten `DraftSection`s with citations and open questions |
| `audit` | 十章節 + 適用查核表<br/>Ten sections + applicable checklists | `AuditReport`（逐項 pass / partial / fail / N/A 與修訂需求）<br/>Item-level pass / partial / fail / N/A and revision requests |

**韌性 Resilience**：外部來源失敗只記警示；撰寫失敗的章節以標記佔位；修訂失敗保留原文；SAP 敘述與基準矩陣合成失敗時改用確定性骨架。執行狀態每個階段都寫入資料庫，閘門可跨重啟續跑。
A failed source only adds a warning; a failed section becomes a flagged placeholder; a failed revision keeps the previous text; the SAP narrative and benchmark synthesis fall back to deterministic skeletons. State is persisted after every stage, so the gate survives a restart.

---

## 4. 一次執行的時序 | Sequence of a run

```mermaid
sequenceDiagram
    autonumber
    actor U as 使用者 User
    participant F as 前端代理 Frontend proxy
    participant B as 後端 Backend
    participant M as MCP 伺服器 MCP servers
    participant L as 本地 LLM Local LLM
    participant X as 外部公開 API Public APIs

    U->>F: 建立專案並執行 create project + run
    F->>B: POST /api/projects, /runs（附金鑰 with key）
    B-->>U: SSE 事件串流 event stream
    B->>M: select_checklists, retrieve_guideline_clauses
    B->>L: 法規路徑解析 triage narrative
    par 平行檢索 parallel harvest
        B->>M: search_samd_trials
        M->>X: ClinicalTrials.gov
    and
        B->>M: summarize_predicate_benchmarks
        M->>X: openFDA + 510(k) PDF
    and
        B->>M: search_baseline_performance
        M->>X: PubMed
    end
    B->>L: 合成基準矩陣 benchmark synthesis
    B-->>U: hitl_required（流程暫停 run pauses）
    U->>F: 勾選實證並確認 confirm evidence
    F->>B: POST /confirm-evidence
    B->>M: calc_standalone_sample_size, calc_buderer, allocate_strata
    B->>L: SAP 敘述 SAP narrative
    loop 十章節（並行 3 路）ten sections, 3 in parallel
        B->>M: retrieve_guideline_clauses
        B->>L: 撰寫章節 draft section
    end
    loop 審查最多 2 輪 audit, up to 2 rounds
        B->>M: get_checklist, prescreen_checklist_coverage
        B->>L: 逐項判定 item judgement
        B->>L: 修訂未達章節 revise failed sections
    end
    B-->>U: completed
    U->>F: 匯出 export .md / .docx
```

---

## 5. 資料流與信任邊界 | Data flow & trust boundaries

```mermaid
flowchart LR
    subgraph LAN["受控網段 Controlled LAN"]
        USER["使用者瀏覽器<br/>User browser"]
    end
    subgraph BOX["GB10 主機（信任區）GB10 host (trusted zone)"]
        FE["前端 :3000<br/>唯一對外 only exposed port"]
        BE["後端 backend<br/>127.0.0.1"]
        DB[("PostgreSQL<br/>不對外 not published")]
        VEC[("Qdrant<br/>127.0.0.1")]
        LLM[("Ollama / vLLM<br/>127.0.0.1")]
        MCPS["MCP 伺服器<br/>僅容器網路 compose network only"]
    end
    subgraph NET["網際網路 Internet（不受信任 untrusted）"]
        PUB["ClinicalTrials.gov · openFDA<br/>accessdata.fda.gov · NCBI PubMed<br/>法規 PDF 來源 guidance PDF sources"]
        CLOUD["Anthropic API<br/>（僅在明確啟用時 only if enabled）"]
    end

    USER -- "HTTP（建議經 VPN / TLS 反向代理）<br/>HTTP (via VPN / TLS proxy recommended)" --> FE
    FE -- "X-API-Key" --> BE
    BE --> DB
    BE --> LLM
    BE --> MCPS
    MCPS --> VEC
    MCPS -- "只送公開關鍵字<br/>public keywords only" --> PUB
    BE -. "LLM_PROVIDER=anthropic" .-> CLOUD
```

| 資料 Data | 存放 / 去向 Where it lives / goes |
|---|---|
| 表單輸入 Form input | 本機 PostgreSQL；送本機 LLM<br/>Local PostgreSQL; sent to the local LLM |
| 生成的計畫書與審查 Drafts & audits | 本機 PostgreSQL；使用者下載匯出檔<br/>Local PostgreSQL; downloaded by the user |
| 法規全文與向量 Guidance text & vectors | 本機 Qdrant 與 volume<br/>Local Qdrant and volume |
| 對外查詢 Outbound queries | 疾病名稱、模態、產品代碼、K / DEN 編號（公開資訊）<br/>Disease, modality, product code, K / DEN numbers (public) |
| 雲端 LLM（選用）Cloud LLM (optional) | 只有 `LLM_PROVIDER=anthropic` 時，提示內容才會送到 Anthropic<br/>Prompts reach Anthropic only when `LLM_PROVIDER=anthropic` |

**不受信任的內容 Untrusted content**：檢索到的 PDF、摘要、試驗登錄文字都可能含有惡意指令。系統提示要求模型只從中擷取事實、不得遵循其中指令；模型輸出以不含原始 HTML 的 Markdown 呈現；openFDA PDF 網址由正則驗證過的 K / DEN 編號組成，不接受任意 URL。
Retrieved PDFs, abstracts and registry text may contain malicious instructions. The system prompt tells the model to extract facts only and never follow embedded instructions; output is rendered as Markdown without raw HTML; openFDA PDF URLs are built from regex-validated K / DEN numbers, never arbitrary URLs.

---

## 6. GB10 部署拓撲 | Deployment topology on the GB10

```mermaid
flowchart TB
    subgraph HOST["GB10 · DGX OS · aarch64 · 128 GB 統一記憶體 unified memory"]
        direction TB
        subgraph PUBLISHED["對區網開放 Published on the LAN"]
            FE["frontend<br/>0.0.0.0:3000"]
        end
        subgraph LOOP["僅本機 Loopback only (127.0.0.1)"]
            BE["backend<br/>:8000（可改 BACKEND_PORT）"]
            QD["qdrant :6333"]
            OL["ollama :11434<br/>GPU"]
            VL["vllm :8001<br/>GPU（profile vllm）"]
        end
        subgraph INTERNAL["僅容器網路 Compose network only"]
            PG["postgres :5432"]
            M1["mcp-biostat-calc :8101"]
            M2["mcp-clinicaltrials :8102"]
            M3["mcp-openfda-predicate :8103"]
            M4["mcp-pubmed-evidence :8104"]
            M5["mcp-regulatory-rag :8105"]
        end
        JOB["一次性工作 One-shot jobs<br/>ollama-pull · rag-ingest"]
    end
    FE --> BE
    BE --> PG & M1 & M2 & M3 & M4 & M5
    BE --> OL
    BE -.-> VL
    M5 --> QD
    M5 -.-> OL
    JOB -.-> OL & QD
```

| 項目 Item | 說明 Notes |
|---|---|
| Compose profiles | `ollama`（Ollama 同時提供對話與嵌入 chat + embeddings）、`vllm`（vLLM 提供對話，Ollama 只做嵌入 vLLM for chat, Ollama for embeddings only）、`ingest`（一次性法規匯入 one-shot ingestion） |
| 映像 Images | 自建 Python 映像供後端與五個 MCP 伺服器共用；前端為 Next.js standalone；全部支援 `linux/arm64`，在 GB10 原生建置<br/>One shared Python image for the backend and five MCP servers; Next.js standalone frontend; all `linux/arm64`, built natively on the GB10 |
| 持久化 Volumes | `pgdata`（專案與計畫書 projects & drafts）、`qdrant`（索引，可重建 index, rebuildable）、`corpus`（PDF 快取 PDF cache）、`ollama` / `hf-cache`（模型檔 model files） |
| 埠設定 Port settings | `FRONTEND_PORT` / `BACKEND_PORT` / `QDRANT_PORT` / `OLLAMA_PORT` / `VLLM_PORT` 與 `BACKEND_BIND` / `FRONTEND_BIND` 皆在 `.env` 設定<br/>All set in `.env` |
| 記憶體預算 Memory budget | qwen3:32b + 32k context 約 22–30 GB；bge-m3 約 1.5 GB；其餘服務 < 4 GB<br/>qwen3:32b with 32k context ≈ 22–30 GB; bge-m3 ≈ 1.5 GB; everything else < 4 GB |

---

## 7. LLM 層 | LLM layer

```mermaid
flowchart LR
    A["代理呼叫 ask_json(schema)<br/>Agent call"] --> B{"供應商 Provider"}
    B -- local --> C["OpenAI 相容 /v1/chat/completions<br/>Ollama · vLLM · NIM"]
    B -- anthropic --> D["Anthropic SDK<br/>串流 streaming · output_config.format"]
    B -- fake --> E["假模型（測試）<br/>Fake LLM (tests)"]
    C --> F{"結構化輸出模式<br/>Structured output mode"}
    F --> F1["json_schema"] --> F2["json_object"] --> F3["純文字擷取 text extraction"]
    C --> G{"截斷？ Truncated?<br/>finish_reason=length<br/>或只有推理 or reasoning only"}
    G -- 是 yes --> H["預算加倍重試<br/>retry with 2× budget<br/>（上限 LLM_MAX_TOKENS_CAP）"]
    A --> V{"pydantic 驗證<br/>validation"}
    V -- 失敗 fail --> R["附錯誤訊息修復一次<br/>one repair round with errors"]
```

| 設定 Setting | 預設 Default | 用途 Purpose |
|---|---|---|
| `LLM_PROVIDER` | `local` | `local` / `anthropic` / `fake` |
| `LLM_BASE_URL`, `LLM_MODEL` | `http://ollama:11434/v1`, `qwen3:32b` | 本地端點與模型<br/>Local endpoint and model |
| `LLM_EXTRA_BODY` | 空 empty | 合併進每個請求的 JSON，例如 `{"reasoning_effort":"none"}` 關閉 Qwen3 思考模式<br/>JSON merged into every request, e.g. turn Qwen3 thinking off |
| `LLM_MAX_TOKENS` / `LLM_SECTION_MAX_TOKENS` / `LLM_MAX_TOKENS_CAP` | 8192 / 12000 / 24000 | 一般呼叫 / 長輸出呼叫 / 截斷重試上限<br/>Short calls / long-output calls / retry ceiling |
| `LLM_TIMEOUT_SECONDS` | 3600 | GPU 與其他工作共用時單次章節呼叫可能超過 30 分鐘<br/>A section call can exceed 30 min on a shared GPU |
| `EMBEDDINGS_*` | `bge-m3`, 1024 維 dims | 法規 RAG 的向量嵌入；未設定時退回確定性雜湊嵌入（主要靠 BM25）<br/>Embeddings for the guidance RAG; falls back to hashing (BM25-led) if unset |

---

## 8. 確定性與生成式的分工 | Deterministic vs. generative work

| 工作 Task | 由誰做 Done by | 理由 Why |
|---|---|---|
| 樣本數、信賴區間、MRMC 檢定力、分層配置<br/>Sample size, CIs, MRMC power, allocation | `mcp-biostat-calc`（SciPy） | 必須可重現、可稽核<br/>Must be reproducible and auditable |
| 查核表選擇、條文檢索、涵蓋度預篩<br/>Checklist selection, clause retrieval, coverage pre-screen | `mcp-regulatory-rag` | 規則明確、結果可解釋<br/>Explicit rules, explainable results |
| 試驗、predicate、文獻檢索與數值擷取<br/>Trial, predicate and literature retrieval and metric extraction | 三個檢索 MCP 伺服器<br/>Three retrieval MCP servers | 來源可追溯<br/>Traceable sources |
| 風險評估敘述、基準矩陣合成<br/>Risk narrative, benchmark synthesis | LLM（結構化 JSON） | 需要跨來源的判讀<br/>Needs cross-source judgement |
| 十章節撰寫、修訂<br/>Section drafting and revision | LLM | 需要專業寫作<br/>Needs expert writing |
| 查核表逐項判定<br/>Checklist item judgement | LLM（以預篩結果聚焦）<br/>LLM, focused by the pre-screen | 需要理解語意是否「真的」涵蓋<br/>Needs to judge whether content truly covers an item |

---

## 9. 資料模型與 API | Data model & API

**資料表 Tables**（SQLAlchemy，PostgreSQL / 測試用 SQLite）

| 資料表 Table | 內容 Content |
|---|---|
| `projects` | 專案名稱與完整 `ProtocolInput`（JSON）<br/>Name and the full `ProtocolInput` (JSON) |
| `runs` | 執行階段與完整 `RunState`（JSON：triage、evidence、sap、sections、audits、計數、警示）<br/>Stage and the full `RunState` (JSON: triage, evidence, SAP, sections, audits, counters, warnings) |
| `run_events` | 每個事件（階段開始 / 完成、進度、工具呼叫、人工確認、錯誤）<br/>Every event (stage start / end, progress, tool call, HITL, error) |

**API 端點 Endpoints**（前綴 prefix `/api`；設定 `API_KEY` 時除 `/health` 外都需金鑰 key required except `/health` when `API_KEY` is set）

| 方法與路徑 Method & path | 用途 Purpose |
|---|---|
| `GET /health` | 健康檢查 health check |
| `GET /meta/schema`, `/meta/example`, `/meta/config`, `/meta/mcp-health` | 輸入合約、範例、設定、MCP 狀態<br/>Input contract, example, config, MCP status |
| `POST /projects` · `GET /projects` · `GET/PUT /projects/{id}` | 專案管理 project management |
| `POST /projects/{id}/runs` · `GET /projects/{id}/runs` · `GET /runs/{id}` | 啟動與查詢執行 start and read runs |
| `GET /runs/{id}/events` | SSE 即時事件 live events |
| `GET /runs/{id}/events/history` | 已存事件 persisted events |
| `POST /runs/{id}/confirm-evidence` | 人工確認實證並續跑 confirm evidence and resume |
| `PUT /runs/{id}/sections/{key}` | 編輯章節 edit a section |
| `POST /runs/{id}/cancel` | 取消執行 cancel |
| `GET /runs/{id}/export.md`, `/export.docx` | 匯出 export |

---

## 10. 技術選型 | Technology stack

| 層 Layer | 技術 Technology |
|---|---|
| 前端 Frontend | Next.js 16.4 (App Router, standalone) · React 19.3 · TypeScript · Tailwind CSS 4.3 · react-hook-form + zod 4 · react-markdown |
| 後端 Backend | Python 3.12+ · FastAPI · pydantic 2 · SQLAlchemy 2 (async) · sse-starlette · python-docx · uv workspace |
| 工具協定 Tool protocol | Model Context Protocol, official `mcp` Python SDK 2.x (`MCPServer`, streamable HTTP) |
| 統計 Statistics | SciPy · NumPy |
| 檢索 Retrieval | Qdrant 1.15（dense + sparse, RRF fusion）· bge-m3 · BM25 with jieba |
| 推論 Inference | Ollama · NVIDIA vLLM container · NVIDIA NIM · Anthropic API（選用 optional） |
| 資料庫 Database | PostgreSQL 16 |
| 部署 Deployment | Docker Compose（linux/arm64）on NVIDIA DGX Spark / GB10 |

---

## 11. 設計取捨 | Design trade-offs

| 決策 Decision | 取捨 Trade-off |
|---|---|
| 固定流程而非讓模型自由呼叫工具<br/>Fixed pipeline instead of free tool-calling | 可預測、可稽核、本地中型模型也能穩定完成；代價是彈性較低，新增步驟要改程式。<br/>Predictable, auditable and reliable with mid-size local models; less flexible, new steps need code. |
| 不用 LangGraph<br/>No LangGraph | 五階段加一個閘門，自寫約 150 行的流程就足夠，少一個常改版的依賴；需要動態分支時再引入。<br/>Five stages and one gate fit in ~150 lines; one less fast-moving dependency; can be added if dynamic branching is needed. |
| 執行狀態整包存 JSON<br/>Whole run state stored as JSON | 結構可隨版本演進、讀寫簡單；代價是跨執行的查詢較不方便。<br/>Schema can evolve, simple reads and writes; cross-run queries are less convenient. |
| 前端同源代理而非直接開放後端<br/>Same-origin proxy instead of exposing the backend | 只開一個埠、金鑰不進瀏覽器；多一跳轉發。<br/>One exposed port, key stays server-side; one extra hop. |
| 單一共用 API 金鑰<br/>Single shared API key | 部署簡單；尚無個人帳號與專案權限，多人使用需在前面加 SSO 反向代理。<br/>Simple to deploy; no per-user accounts or project permissions yet, put an SSO reverse proxy in front for multi-user use. |
| 本地 32B 模型<br/>Local 32B model | 資料不出機器、無使用費；一份完整計畫書約 1–2.5 小時。<br/>Data stays on the box, no usage fees; one full protocol takes about 1–2.5 hours. |

---

## 12. 實測效能 | Measured performance

GB10 上以 `qwen3:32b`（Ollama，思考模式關閉）完整跑一份範例，GPU 與另一個 LLM 工作共用：
One full example run on the GB10 with `qwen3:32b` (Ollama, thinking off), GPU shared with another LLM workload:

| 階段 Stage | 耗時 Time |
|---|---|
| 法規路徑解析 Triage | 1 分鐘 min |
| 實證檢索至閘門 Harvest to gate | 3.5 分鐘 min |
| 生物統計 Biostatistics | 5 分鐘 min |
| 十章節撰寫 Writing (10 sections) | 56 分鐘 min |
| 審查第一輪 Audit round 1 | 12.5 分鐘 min（pass 29 / partial 10 / fail 5） |
| 修訂 6 章 Revise 6 sections | 63 分鐘 min |
| 審查第二輪 Audit round 2 | 12 分鐘 min（pass 34 / partial 9 / fail 1） |
| **合計 Total** | **2 小時 34 分 2 h 34 min** |

GPU 獨占時估計可在一小時內完成。完整輸出見 [`docs/examples/`](examples/)。
With the GPU to itself the run is expected to finish within about an hour. The full output is in [`docs/examples/`](examples/).
