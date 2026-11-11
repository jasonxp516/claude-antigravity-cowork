# 量測與驗證方法

## 測試專案與任務
- `experiment/testbed/`：自建的 Python 任務管理套件 `evtrack`，起始狀態含資料模型與一個刻意埋的 bug。
- `experiment/tasks/`：12 個任務，每個有 `spec.md` 和 **hidden tests**（實作者和指揮者都看不到）：

| 任務 | 內容 | hidden tests |
|---|---|---|
| T1–T6 | JSON 儲存層、快速輸入 parser、查詢 DSL、CLI、WSGI JSON API、循環規則 bug fix | 50 |
| T7–T10 | CSV/iCal 匯入匯出（含 UTF-8 折行）、undo/redo 持久化、循環任務 agenda、統計報表 | 17 |
| F1 | 單頁任務清單 UI | 5（Playwright） |
| F2 | 5 個頁面的 SPA | 7（Playwright） |

## 對照組（arm）
- 每個 arm 是一個 **Claude Sonnet 子代理**，在 `runs/<arm>/` 獨立的 git 工作目錄中完成同一批任務，提示只說明工作目錄、要讀哪一版 SKILL.md、要做哪些 spec。
- arm 不得讀取 `tasks/` 或其他 arm 的目錄。
- 基準組（A、A2、FA、LA）是 Claude 自己寫；其他組依各版 skill 執行。

## Claude 成本
- 從子代理的 transcript（JSONL）逐則訊息加總 `usage`（依 message id 去重），計算：

  **IET = input + 1.25 × cache_creation + 0.1 × cache_read + 5 × output**

  權重依 API 相對價格，代表「等效 input token」。工具：`experiment/tools/claude_usage.py`。
- 同時記錄回合數，並逐回合檢查快取是命中還是重寫（用來發現等待造成的快取失效）。

## Gemini 成本
- 每次委派前後呼叫 `agy -p "/usage"`（不耗額度）取得各額度桶的剩餘比例，差值即該批用量（`agy_quota.py`）。
- 同時記錄 agy 每次呼叫回傳的 token 用量與耗時（`data/runs.jsonl`）。

## 品質
| 面向 | 方法 |
|---|---|
| 功能正確 | hidden tests（`experiment/tools/eval_arm.py`） |
| hidden tests 打平時的程式品質 | Sonnet 盲審兩份實作，標為 X / Y，要求逐任務評分並列出**可重現**的 bug |
| 前端視覺 | Playwright 截圖（桌面／手機／亮暗），Opus 盲評打分；同一組評兩次估計評審變異（約 ±0.7） |
| 前端程式 | Opus code review Gemini 的 JS，整理共通問題 → `frontend_rules.md` |

盲評對照表在 `data/blind_map*.json`，截圖在 `data/screenshots/`。

## 觀察 Gemini 行為
- agy 把每個對話存在 `~/.gemini/antigravity-cli/conversations/<id>.db`（SQLite）。思考內容不在本機，但工具呼叫（指令、讀寫檔、輪詢）都在。
- `agy_trace.py` 把工具呼叫分類並計算空轉比例；`delegate.py` 每份報告附一行統計。

## 重現

```bash
cd experiment
python3 -m venv .venv && .venv/bin/pip install pytest playwright && .venv/bin/playwright install chromium

# 1. 建立 arm 工作目錄：從 testbed 複製並 git init，把 tasks/Tn/spec.md 放進 specs/
# 2. 啟動一個 Claude 子代理（建議 Sonnet），提示：工作目錄、要遵循的 skill_versions/SKILL_vN.md、要完成的 specs
# 3. 計分
.venv/bin/python tools/eval_arm.py runs/<arm> --tasks=T1,T2,T3
.venv/bin/python tools/claude_usage.py <子代理 transcript.jsonl>
.venv/bin/python tools/report.py <arms.json>          # 產生對照表
```
前端截圖：`tools/shoot_front.py`（F1）、`tools/shoot_f2.py`（F2）。

## 已知限制
- 每個 arm 只跑 1–2 次，小樣本；主要結論在兩組不同任務上重現。
- 任務屬中小型；在大型真實專案中，主對話 context 更大，理論上委派更划算，但未直接量測。
- 量測都在 Sonnet 子代理（5 分鐘快取）中進行；主對話（1 小時快取）的等待懲罰更小。
- 只測過 Gemini 3.8 Flash。
