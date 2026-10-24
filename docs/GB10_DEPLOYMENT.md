# 在 NVIDIA DGX Spark（GB10）上部署 AI-SaMD Clinical Protocol Copilot

> 目標：整套系統（前端、後端、5 個 MCP 伺服器、PostgreSQL、Qdrant、本地 LLM 與向量嵌入）全部跑在一台 DGX Spark 上，**病人資料與計畫書內容不離開機器**。

## 0. 硬體與作業系統事實（決定部署方式）

| 項目 | DGX Spark |
|---|---|
| SoC | NVIDIA GB10 Grace Blackwell |
| CPU | 20 核 Arm（10× Cortex-X925 + 10× Cortex-A725）→ **aarch64 / linux/arm64** |
| GPU | Blackwell，第 5 代 Tensor Core，約 1 PFLOP NVFP4 |
| 記憶體 | **128 GB LPDDR5x 統一記憶體**（CPU/GPU 共用，273 GB/s）—— 可載入約 200B 參數的 NVFP4 模型 |
| 儲存 | 1–4 TB NVMe（模型檔很大，先確認 `df -h /`） |
| OS | DGX OS（Ubuntu 衍生），預裝 NVIDIA 驅動、CUDA、Docker 與 NVIDIA Container Toolkit |

**推論**：所有容器都必須有 arm64 版本。本專案使用的 `postgres:16-alpine`、`qdrant/qdrant`、`ollama/ollama`、`python:3.12-slim`、`node:22-alpine`、`ghcr.io/astral-sh/uv` 皆為多架構 image；後端/MCP/前端 image 在 Spark 上原生 build（約 3–6 分鐘）。

參考：NVIDIA 官方 [DGX Spark Playbooks](https://github.com/NVIDIA/dgx-spark-playbooks)（vLLM、Ollama + Open WebUI、NIM、Healthcare Agent 等）。

## 1. 前置檢查（在 Spark 上）

```bash
# Docker 可免 sudo 使用（NVIDIA playbook 的標準步驟）
docker ps >/dev/null || { sudo usermod -aG docker $USER && newgrp docker; }

# GPU 可被容器看到
docker run --rm --gpus all nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04 nvidia-smi

# 磁碟空間：模型 20–90 GB + image ~5 GB + 法規 PDF 快取
df -h /

# 如果主機已跑 Ollama（其他 playbook 留下的），先停掉以免 11434 埠衝突
sudo systemctl stop ollama 2>/dev/null || true; ss -tlnp | grep 11434 || echo "port 11434 free"
```

## 2. 選擇推論後端

| 選項 | 何時選 | LLM | 嵌入 | 備註 |
|---|---|---|---|---|
| **A. Ollama（預設，profile `ollama`）** | 最快上手、一個服務同時提供 chat 與 embeddings | `qwen3:32b`（Q4_K_M 約 20 GB，中英雙語、支援 JSON 結構化輸出）；想更強可試 `gpt-oss:120b`（MXFP4 約 65 GB）或 NVIDIA healthcare playbook 用的 Nemotron 3 Super 120B（約 86 GB） | `bge-m3`（1024 維，中英雙語） | 以 `ollama.com/library` 的實際 tag 為準；`OLLAMA_CONTEXT_LENGTH=32768` 已在 compose 設定 |
| **B. vLLM（profile `vllm`）** | 要最高吞吐 / 多人同時使用 / NVFP4 模型 | NVIDIA 官方 Spark recipe：image `nvcr.io/nvidia/vllm:26.10.pre1-py3`，模型 `nvidia/Qwen3.8-27B-NVFP4`，`--gpu-memory-utilization 0.60`（recipe 註明更高會不穩） | 仍由 Ollama 的 `bge-m3` 提供 | 需先 `hf download nvidia/Qwen3.8-27B-NVFP4`；recipe 與 digest 見 [vLLM playbook](https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/playbook-vllm) |
| **C. NVIDIA NIM** | 要 NVIDIA 支援的封裝 | 例：`nvcr.io/nim/nvidia/nemotron-3.5-lightning-30b-a3b:latest`（需 NGC API key） | Ollama `bge-m3` | OpenAI 相容埠 8000；把 `LLM_BASE_URL` 指到 NIM 即可，不需改程式 |
| **D. 雲端 Claude**（`LLM_PROVIDER=anthropic`） | 需要最高品質草稿、且輸入**不含**可識別病人資料 | `claude-opus-5-5`（官方 SDK，自適應思考、串流） | Ollama `bge-m3` | 需 `ANTHROPIC_API_KEY`；法規 RAG 與統計仍在本機 |

後端對所有本地選項一視同仁：只要是 **OpenAI-compatible `/v1/chat/completions`**，結構化輸出會自動嘗試 `response_format=json_schema → json_object → 純文字擷取`，並自動移除 Qwen3/DeepSeek 類模型的 `<think>` 段落。

### 記憶體預算（128 GB）
| 元件 | 約略佔用 |
|---|---|
| LLM（qwen3:32b Q4 + 32k KV cache） | 22–30 GB |
| bge-m3 | 1.5 GB |
| Qdrant + PostgreSQL + 6 個 Python 服務 + 前端 | < 4 GB |
| **餘裕** | 可改用 70B–120B 等級模型（例：gpt-oss:120b ≈ 65 GB、Nemotron 3 Super ≈ 86 GB） |

## 3. 安裝與啟動

```bash
git clone https://github.com/yaufan/Clinical-trials-agent.git
cd Clinical-trials-agent
cp .env.example .env
# 至少確認以下幾項：
#   LLM_PROVIDER=local
#   LLM_BASE_URL=http://ollama:11434/v1      LLM_MODEL=qwen3:32b
#   EMBEDDINGS_BASE_URL=http://ollama:11434/v1  EMBEDDINGS_MODEL=bge-m3  EMBEDDINGS_DIM=1024
#   NCBI_API_KEY=...（免費申請，PubMed 10 req/s）   OPENFDA_API_KEY=...（可選）
#   NEXT_PUBLIC_API_BASE_URL=http://<spark-ip>:8000   （瀏覽器端看到的後端位址）

# 1) 建置並啟動（Ollama profile）
docker compose --profile ollama up -d --build

# 2) 第一次：拉模型（約 20 GB + 1.2 GB，依網速 10–40 分鐘）
docker compose --profile ollama run --rm ollama-pull

# 3) 下載並索引法規文件（TFDA / FDA / IMDRF PDF → Qdrant；含 8 份查核表）
docker compose --profile ollama --profile ingest run --rm rag-ingest

# 4) 檢查
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/meta/mcp-health | python3 -m json.tool
```

打開 `http://<spark-ip>:3000` → 「新建專案」→ 「載入範例」→ 送出，即可看到五階段流程；在「實證確認」閘門勾選要保留的 predicate / 文獻並按確認。

### 使用 vLLM profile
```bash
# 先在 Spark 上下載模型（依 NVIDIA recipe）
pip install -U huggingface_hub && hf download nvidia/Qwen3.8-27B-NVFP4
# .env：LLM_BASE_URL=http://vllm:8000/v1  LLM_MODEL=local-llm  VLLM_MODEL=nvidia/Qwen3.8-27B-NVFP4
docker compose --profile vllm up -d --build
docker compose --profile vllm run --rm ollama-pull   # 仍需 bge-m3 做嵌入
```
> 以 NVIDIA recipe 的設定為準（kernel 設定、speculative decoding 等需成組使用）；`VLLM_EXTRA_ARGS` 可附加 recipe 的其餘旗標。

### 使用雲端 Claude
```bash
# .env：LLM_PROVIDER=anthropic  ANTHROPIC_API_KEY=sk-ant-...  ANTHROPIC_MODEL=claude-opus-5-5
docker compose --profile ollama up -d backend      # 嵌入仍用本地 bge-m3
```

## 4. 煙霧測試

```bash
uv sync --all-packages --group dev          # 或使用 Spark 的 python3 + pip install httpx
uv run python scripts/smoke_test.py --base-url http://localhost:8000
```
會建立範例專案、跑到實證閘門、自動確認、跑完五階段並輸出 `smoke-protocol.md`。

## 5. 開發模式（不用 Docker，Spark 或任何 Linux/macOS）

```bash
uv sync --all-packages --group dev
make test                                    # 157 個 Python 測試（含 in-process MCP 整合測試）
# 五個 MCP 伺服器 + 後端（各開一個 terminal，或用 tmux）
uv run python -m mcp_biostat_calc      --transport streamable-http --port 8101
uv run python -m mcp_clinicaltrials    --transport streamable-http --port 8102
uv run python -m mcp_openfda_predicate --transport streamable-http --port 8103
uv run python -m mcp_pubmed_evidence   --transport streamable-http --port 8104
QDRANT_URL=http://localhost:6333 uv run python -m mcp_regulatory_rag --transport streamable-http --port 8105
LLM_BASE_URL=http://localhost:11434/v1 uv run uvicorn app.main:build --factory --app-dir backend --reload
cd frontend && npm ci && npm run dev         # http://localhost:3000
```
MCP 伺服器也可用 `stdio` 模式直接掛進 Claude Desktop / Claude Code 做工具層驗證（Phase 1 的 CLI 驗證）。

## 6. 疑難排解

| 症狀 | 處理 |
|---|---|
| `docker compose up` 說 image 沒有 arm64 版本 | 確認 tag；本專案所選 image 均為多架構。若自行替換（例如其他向量庫），請選 `linux/arm64` 版本 |
| Ollama 容器看不到 GPU | `docker run --rm --gpus all ollama/ollama nvidia-smi`；確認 NVIDIA Container Toolkit 與 `deploy.resources.reservations.devices` 設定；DGX OS 預裝，但若手動重裝 Docker 需重新 `nvidia-ctk runtime configure` |
| 11434 埠被占用 | 主機上的 Ollama（systemd）與容器衝突：`sudo systemctl disable --now ollama` 或改 compose 的對外埠 |
| 第一個請求很慢 / 超時 | 模型載入需 30–120 秒；`LLM_TIMEOUT_SECONDS` 預設 600；Ollama 的 `OLLAMA_KEEP_ALIVE=24h` 已設定避免卸載 |
| 結構化輸出一直解析失敗 | 換支援 JSON schema 的模型（Qwen3 系列、gpt-oss、Nemotron 3.x 皆可）；後端會自動降級到 `json_object` 與文字擷取，並在 `warnings` 顯示 |
| PubMed 查詢 429 | 設定 `NCBI_API_KEY`（10 req/s）；伺服器內建 token-bucket 限速 |
| accessdata.fda.gov 回 404 | 不是每個 K-number 都有摘要 PDF（特別是 2000 年以前與 De Novo 以外）；程式已帶瀏覽器 UA |
| Qdrant 索引為空 | 跑 `rag-ingest`；`GET /api/meta/mcp-health` 與 RAG 工具 `list_indexed_documents` 可查 |
| 想換嵌入模型 | 同時改 `EMBEDDINGS_MODEL` 與 `EMBEDDINGS_DIM`，並以 `--recreate` 重新 ingest（collection 維度固定） |

## 7. 安全與法規提醒

- 系統輸出為 **AI 輔助草稿**；所有統計數字皆由 `mcp-biostat-calc` 確定性計算，但 **MRMC 樣本數請以 RJafroc / iMRMC 交叉驗證**，並由生統人員覆核後才可用於 IRB / TFDA / FDA 送件。
- 法規指引全文（TFDA、FDA、IMDRF）會下載到 Spark 本機的 `corpus` volume，不進 git；SPIRIT-AI 原文與 ISO 14155 需自備授權版本後加到 `sources.yaml`。
- 若改用雲端 LLM（選項 D），請確認輸入不含可識別個資，且符合院內資訊安全與個資法規範。


## 8. 實際部署紀錄 — gx10-01（2026-10-24）

第一次在真機部署由 Claude Code 在機器上執行，以下是實際遇到的狀況與對應設定，之後重佈或換機器可直接照用。

**機器**：gx10-01，GB10，aarch64，121 GB 可用統一記憶體（其他工作已用約 35 GB），磁碟剩 1.8 TB，Docker 29、compose v5、uv 已安裝，區網 IP 192.168.0.209。

**既有服務與因應**
| 狀況 | 處理 |
|---|---|
| 127.0.0.1:8000 已被容器 `qwen38-q8`（llama.cpp，模型 `qwen3.8-27b-q8`，單 slot、約 4.5 tok/s）占用，且有本機程序整天在用 | 不重用它（會互相排隊）。改啟動 compose 的 Ollama 拉 `qwen3:32b`。override 另留了一個 socat `llm-relay`（172.17.0.1:8020 → 127.0.0.1:8000），要切回重用模式只需改 `.env` 的 `LLM_BASE_URL` |
| 後端對外埠 8000 衝突 | `docker-compose.override.yml` 把 backend 映射到 **8010**；`.env` 的 `NEXT_PUBLIC_API_BASE_URL=http://192.168.0.209:8010`，`CORS_ORIGINS` 加入 `http://192.168.0.209:3000`，重新 build frontend |
| 本機既有的 `postgres:16-alpine` tag 其實是 amd64 層（exec format error） | `docker pull --platform linux/arm64 postgres:16-alpine` 重新拉正確架構即可（當時改用本機自建 tag `aisamd-postgres:16-alpine-arm64`） |
| Ollama 偵測到 CUDA GB10 | `bge-m3` 以 `docker compose --profile ollama exec ollama ollama pull bge-m3` 單獨拉，避免 `ollama-pull` 一併拉 chat 模型 |

**結果**：11 個容器運作中，`/api/health` ok，五個 MCP 全部 ok，法規 ingest 成功（TFDA 11、FDA CADe 38、PCCP 201、AI 生命週期草案 258、IMDRF 70 個 chunk，加 92 項查核表，共 670 points），網頁 http://192.168.0.209:3000 可用。

**端對端執行時間（qwen3:32b，與另一個 LLM 工作共用 GPU 時）**：法規解析約 160 s、檢索到閘門約 400–500 s、生物統計約 400 s、十章節撰寫約 42 分鐘（每章 3–11 分鐘、兩路並行；GPU 被共用時單次拉長到 13–26 分鐘）、審查每批 2–4 分鐘、約 10 批。整份約 1.5–2.5 小時。

**第一版 LLM 層在真機上踩到的坑（已於程式修正）**
1. Qwen3 的 thinking 會先吃掉輸出 token 預算：`max_tokens` 用完時 content 為空、只剩 reasoning，造成「no JSON object found」而整個 run 失敗。→ 後端現在把 `finish_reason=length` 或「只有 reasoning 沒有答案」視為截斷，自動以兩倍預算重試到 `LLM_MAX_TOKENS_CAP`。
2. 雙語輸出比 6000 token 長而被截斷。→ 長輸出改用 `LLM_SECTION_MAX_TOKENS`（預設 12000）。
3. 單一章節失敗會讓整個 run 失敗。→ 現在改成該章放入佔位內容並記 warning，其餘流程照跑；修訂失敗則保留原文。
4. 建議在 Ollama 關閉 Qwen3 的思考模式（速度約快一倍、不浪費預算）：`.env` 設 `LLM_EXTRA_BODY={"reasoning_effort":"none"}`（Ollama ≥ 0.40 實測有效）；vLLM 用 `{"chat_template_kwargs":{"enable_thinking":false}}`。

**建議的 gx10-01 `.env`（LLM 部分）**
```bash
LLM_PROVIDER=local
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=qwen3:32b            # 與其他 GPU 工作搶資源時可改 qwen3:14b
LLM_EXTRA_BODY={"reasoning_effort":"none"}
LLM_SECTION_MAX_TOKENS=12000
LLM_MAX_TOKENS_CAP=24000
LLM_TIMEOUT_SECONDS=3600            # GPU 與其他工作共用時單次章節呼叫可能超過 30 分鐘
EMBEDDINGS_BASE_URL=http://ollama:11434/v1
EMBEDDINGS_MODEL=bge-m3
EMBEDDINGS_DIM=1024
NEXT_PUBLIC_API_BASE_URL=http://192.168.0.209:8010
CORS_ORIGINS=http://localhost:3000,http://192.168.0.209:3000
```
改完 `.env` 後：`docker compose --profile ollama up -d --build backend frontend`（frontend 因為烤進 API 位址需重 build）。
