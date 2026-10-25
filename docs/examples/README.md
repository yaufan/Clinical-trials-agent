# 範例輸出：AI-SaMD 臨床試驗計畫書（GB10 本地模型實際產生）

這是系統在 NVIDIA DGX Spark（GB10）上，以 **Ollama `qwen3:32b`（本地推論）** 從頭到尾跑完五階段流程所產生的完整計畫書草稿，未經人工修改。

| 項目 | 內容 |
|---|---|
| 輸入 | 系統內建範例（`GET /api/meta/example`）：NeuroDetect-CT AI v2.1.0，急性顱內出血（ICH）分流 CADt，TFDA + FDA 510(k)，回溯性 standalone 研究。**器材、廠商與主持人皆為虛構，不含任何病人資料。** |
| 產生日期 | 2026-10-24 |
| 程式版本 | commit `da253d6`（此後的版本已修正匯出時章節標題重複的問題，並放寬 ClinicalTrials.gov / PubMed 檢索條件） |
| 模型 | `qwen3:32b`（思考模式關閉），嵌入 `bge-m3` |
| 總耗時 | 2 小時 34 分（GPU 與另一個 LLM 工作共用） |
| 實證 | 37 項（openFDA 20、法規條文 17）；該版本的 ClinicalTrials.gov / PubMed 查詢條件過窄而無結果 |
| 樣本數 | 陽性 62 / 陰性 77，共 139（含 10% 退件率）；依盛行率連續收案需 155 |
| 合規審查 | 第一輪 pass 29 / partial 10 / fail 5 → 修訂 6 章 → 第二輪 pass 34 / partial 9 / fail 1（ISO 14155 A.12 修訂與偏離程序） |
| 待確認標記 | 全文 46 處 `[TO BE CONFIRMED]`，多為範例輸入未提供的資訊（研究期間、Protocol ID、無 AI 時醫師的基準效能） |

檔案：
- [`example-protocol-ich-triage-qwen3-32b.md`](example-protocol-ich-triage-qwen3-32b.md)：系統匯出的 Markdown 原檔（SHA-256 `ac18a493…f269`）
- [`example-protocol-ich-triage-qwen3-32b.docx`](example-protocol-ich-triage-qwen3-32b.docx)：由同一份 Markdown 以系統的 Word 匯出器轉出

> ⚠️ 這是 **AI 輔助草稿**，用來展示系統輸出的結構與品質。內容不可直接用於任何送件；實際計畫書必須由法規、臨床與生物統計專業人員逐章覆核。
