# Claude × Antigravity 協作實驗報告（2026-11-11）

## 結論
- **Skill v4 在兩組任務上都穩定省下 32–38% 的 Claude 用量，品質不變（hidden tests 全過）。**
- 無腦外包（B）反而多花 **88%** 的 Claude token；第一版 skill 也多花 79%。省 token 的關鍵不在「誰寫 code」，而在 **Claude 的 turn 數 × context 大小**，以及**等待時間不能超過 prompt cache TTL**。
- Gemini 端代價：每批 4–6 個任務約用 **2–3% 的 5h 額度、0.5–1.2% 的 weekly 額度**（3.8 Flash low）。

## 數據（Claude 端以 Sonnet subagent 量測；IET = input-equivalent tokens，cache write 1.25×、cache read 0.1×、output 5×）

### Round 1/2：T1–T6（storage / parser / query DSL / CLI / WSGI API / bug fix），50 個 hidden tests
| arm | 方法 | Claude IET | vs A | Claude output | turns | agy tokens | hidden |
|---|---|---|---|---|---|---|---|
| A | Claude 自己寫 | 115.7k | 100% | 9.5k | 5 | – | 50/50 |
| B | 無腦外包 + 讀完整 diff review | 217.0k | **188%** | 6.5k | 29 | 1.80M | 50/50 |
| C1 | skill v1（Claude 寫完整驗收測試） | 207.5k | 179% | 9.6k | 17 | 0.29M | 50/50 |
| C2 | v2（只寫 golden examples + agy audit） | 155.2k | 134% | 4.3k | 14 | 0.78M | 50/50 |
| C3 | v3（parallel worktrees + 背景不輪詢） | 130.6k | 113% | 3.3k | 7 | 1.54M | 50/50 |
| **C6** | **v4（flash-low workers）** | **78.9k** | **68%** | 3.9k | 9 | 0.99M | **50/50** |

### Round 3：T7–T10（CSV/iCal 匯入匯出含 UTF-8 折行、undo/redo 持久化、循環任務 agenda、統計報表），17 個 hidden tests
| arm | 方法 | Claude IET | vs A2 | Claude output | turns | agy tokens | hidden |
|---|---|---|---|---|---|---|---|
| A2 | Claude 自己寫 | 112.7k | 100% | 9.9k | 8 | – | 17/17 |
| C4 | v3 | 105.7k | 94% | 2.9k | 7 | 1.35M | 17/17 |
| **C5** | **v4** | **69.9k** | **62%** | 3.3k | 8 | 0.72M | **17/17** |

## 滾動修正紀錄（每版改了什麼、為什麼）
1. **v1 → v2**：v1 Claude 寫完整驗收測試，output 跟自己寫 code 一樣多（9.6k vs 9.5k）。→ 改成只寫 2–4 個 golden asserts/任務，完整測試交給 agy；加 agy 自我 audit（另開 session 對 spec 審 diff）。output 減半。
2. **v2 → v3**：發現 agy 跑 15 分鐘 → subagent prompt cache（5 分鐘 TTL）過期，恢復時整個 context 重寫（≈49k IET，單次就吃掉大半節省）；另有輪詢 turn。→ 獨立 spec 平行跑在 git worktree；背景執行後不輪詢。
3. **v3 → v4**：時間軸顯示 flash-medium 每個 spec 3–8 分鐘，但 flash-low audit 只要 ~50 秒。→ worker 預設 flash-low（失敗才升級 medium），`--then-spec` 只用於「依賴同批新建模組」的情況。總時長 2.5–4.7 分鐘，**cache 不再過期**，品質不降。

## 其他發現
- **每次 agy 呼叫固定 ~25k input tokens 開銷** → 一定要批次。
- **agy 會為了通過錯誤的測試而硬寫特例**（C1 的 query.py）。v2 起 wrapper 明令禁止並要求「測試與 spec 衝突時以 spec 為準並回報」，audit 也專查 hard-code。
- agy audit 有誤報，但 worker 能正確駁回（C4），不需要 Claude 介入。
- `delegate.py` 會把 worker 改到的受保護測試自動還原，避免「改考卷」。
- `agy -p /usage` **零成本**讀額度；model 由 role + 版本號動態挑選（Argon 7% < 門檻時 planner 自動降級 flash-high；未來 4 Flash / Carbon 會自動被選上）。

## 前端實驗（F1：vanilla SPA，任務清單/新增/篩選/切換/刪除/深色模式/行動版；5 個 Playwright 功能測試 + Opus 盲評截圖）
| arm | 方法 | Claude IET | vs FA | 功能 | Opus 盲評 #1 | Opus 盲評 #2 |
|---|---|---|---|---|---|---|
| FA | Claude 自己寫 | 94.6k | 100% | 5/5 | 7.7（第 1） | 7.0（第 3） |
| FG | 全交給 Gemini（v4） | 126.4k | 134% | 5/5 | **5.6（最後）** | **5.6（最後）** |
| FH | 混合：Claude HTML/CSS、Gemini JS | 151.1k | 160% | 5/5 | 7.0 | 7.4 |
| FH2 | 混合 v5：+設計 checklist +frontend_rules | 150.3k | 159% | 5/5 | – | **7.9（第 1）** |

- Gemini 單獨做前端兩次盲評都墊底（行動版排版崩、深色模式原生控制項刺眼、層級弱）。**視覺設計不能交給 Gemini。**
- Opus code review：Gemini JS 的共通問題（沒 AbortController、先 `res.json()` 再檢查 `res.ok`、重繪後焦點遺失、無 `aria-live`、可重複送出）可用規則預防 → `frontend_rules.md`；版面/層級/文案/狀態設計需要 Claude 判斷 → 設計 checklist。
- 小型 UI（約 300 行）前端 JS 很短，委派省不到錢；混合版品質最好但花 ~1.6× Claude token。**政策：小 UI Claude 自寫 + checklist；大型、互動邏輯多的 UI 才用混合（此情境的節省尚未量測）。**
- 盲評者本身有約 ±0.7 分的變異（FA 兩次 7.7 / 7.0）。

## 第二階段研究（行為觀測、決策紀錄、大型前端、分工模型）

### 行為軌跡（`tools/agy_trace.py`）
- Antigravity 不在本機保存 Gemini 的思考內容，但每個工具呼叫都存在 `~/.gemini/antigravity-cli/conversations/*.db`。
- 發現：前端任務中 Gemini 把測試丟背景後狂輪詢狀態，浪費率 51–58%（單 session 155 次呼叫中 90 次輪詢）。
- 修正：wrapper 要求同步執行（WaitMsBeforeAsync=300000）；之後多數 run 輪詢歸零（LH 0%、C7 0%，LS 仍 46% → 規則遵循不完全，持續由 trace 監看）。
- 每次 delegate 報告現在附一行 `worker trace`（呼叫數/測試數/輪詢/浪費率）。

### 決策紀錄（DECISIONS.md）實驗 — 結論：例行工作不值得
- Opus 對照程式碼後：紀錄是「事前計畫」而非事後紀錄、有不實內容（不存在的 router.js、宣稱不用預設值但程式有 `|| 2`）、且漏掉真正的 bug。
- 真正的 bug 源自 Claude 的交接文件與模板互相矛盾 → 改成 Claude 端「交接自我檢查」+ worker 端「與 spec 衝突時以 spec 為準並回報」+ 完工前 grep 自查。
- 行為軌跡比自述更有價值；決策紀錄只留給刻意的調教 session。

### 大型前端（F2：5 個 view 的 SPA，7 個 Playwright 隱藏測試，Opus 盲評 9 張截圖）
| arm | 分工 | Claude IET | vs LA | 功能 | 盲評 |
|---|---|---|---|---|---|
| LA | Claude 全包 + 設計 checklist | 187.9k | 100% | 7/7 | 6.9 |
| LH | Claude 全部 HTML+CSS，Gemini JS | 202.2k | 108% | 6/7（交接矛盾） | 7.4 |
| **LS** | **Claude 設計系統 CSS + 外殼 + 1 個參考 view；Gemini 其餘 view + 全部 JS** | **171.6k** | **91%** | **7/7** | **7.3** |
→ 大型 UI 採「設計系統分工」：唯一同時省錢且品質不降的做法（盲評差異在評審 ±0.7 變異內）。

### 分工模型（`tools/plan_split.py`，未來直接呼叫、不必重新推理）
- 擬合：Claude 節省 ≈ 12 × 被卸載的 output tokens − 35k（12× 而非 5×，因為自己寫的程式碼之後每回合都會被重讀）。
- 每行 output：後端 ≈ 20 tokens、前端 ≈ 34 tokens；可卸載比例：後端 0.7、前端邏輯 0.25、視覺設計 0。
- 驗算：後端 470 行 預測 +44k / 實測 +37–43k；大型 UI 分工 +13k / +16k；小 UI 為負值 / 實測 −55k。
- 結論：**單批可卸載的後端程式 ≳ 300 行才委派**；<40 行、無法自動測試、需要判斷、視覺設計 → Claude。

### v6 驗證（C7，T7–T10）
- 17/17、worker 浪費 0%、Claude 80%；扣除 subagent 回報機制造成的 3 個多餘回合（≈19k，主對話不會發生）≈ 70k，與 v4 的 62% 相當。
- v6 新增：`--preset backend|frontend-js`（一個參數帶入最佳設定）、`plan_split.py`、交接自我檢查、spec 衝突規則、完工 grep 自查、trace 統計。

## 限制與誠實說明
- 每個 arm 只跑一次（n=1）；v4 在兩組不同任務上都重現（62%、68%），但仍屬小樣本。
- 量測用 Sonnet subagent（5 分鐘 cache TTL）。在主對話（1 小時 TTL）中使用時，長等待的懲罰較小，但 turn 數原則不變。
- 任務是中小型（Claude 自寫約 10k output tokens）。**在真實大型開發中，主對話 context 很大，Claude 自己寫 code 會持續膨脹 context，委派的節省理論上會更大**——這點本實驗未直接量測。
- 小於 ~40 行或需要設計判斷的工作，自己寫仍然較省。

## 產出
- 工具：`tools/agy_quota.py`、`agy_models.py`、`delegate.py`、`claude_usage.py`、`eval_arm.py`、`report.py`
- Skill：`.claude/skills/agy-cowork/SKILL.md`（v4），歷代版本在 `skill_versions/`
- 已安裝為全域：`~/.claude/skills/agy-cowork/`（v6，含 `frontend_rules.md`、`plan_split.py`、`agy_trace.py`）＋ `~/.claude/CLAUDE.md` 規則；`dist/agy-cowork/` 為同版備份
- 前端截圖：`metrics/shots/<arm>/`；盲評對照表：`metrics/blind_map*.json`
- 原始數據：`metrics/runs.jsonl`、`metrics/quota.jsonl`、`metrics/report_rows*.json`

## 第三階段：真實專案驗證（作者的私人 Flask 專案：學生出缺席監控儀表板；新帳號只有 3.8 Flash）
- 流程照 v6：`plan_split.py` 判定後端 4 項（~470 行）委派、安全判斷與前端視覺歸 Claude → 1 次 `delegate.py --preset backend`。
- agy：flash-low、2 次嘗試、246 秒、40 次工具呼叫、**輪詢 0%**、audit NO_ISSUES；用掉 weekly 0.28% / 5h 0.98%。
- Claude 端：寫 spec（~60 行）+ golden tests（7 個）→ 只讀報告 + 抽查無法測試的 Playwright 段（~30 行）→ 合併 28/28 通過。
- 前端由 Claude 自寫並截圖驗證，抓到 2 個既有 bug（未定義 `showError` 導致不導向設定頁、錯誤橫幅被 flex 擠到左側）。
- 觀察：與真實專案協作時，worktree 隔離讓 Claude 能**同時**做前端、agy 做後端，等待時間被重疊掉。真實程式碼上的 delegate 成果品質足以直接合併。

## 第四階段：Flash effort A/B（low vs high，同樣的 pre-delegate commit 重跑）
| 批次 | effort | hidden | 耗時（平行最長 + 循序） | agy 5h 額度 | 盲審（Sonnet，不知道哪個是哪個） |
|---|---|---|---|---|---|
| T1–T6 | low (C6) | 50/50 | 1.5 + 3.2 分 | 2.9% | 6.5 |
| T1–T6 | high (H6) | 50/50 | 9 + 11 分 | 15.2% | **8.3** |
| T7–T10 | low (C7) | 17/17 | 2.6 + 0.8 分 | 2.9% | 7 |
| T7–T10 | high (H7) | 17/17 | 12.4 + 1.1 分 | 13.6% | **8** |
- low 的實際 bug（hidden tests 沒抓到、審查者重現）：CLI 以 `-` 開頭的參數失敗、PATCH 可存入錯誤型別、`update(due=str)` 造成 500、limit=0 切片錯誤、tag 大小寫重複計數。
- high 也有 bug（`splitlines()` 吃掉 U+2028 等字元），但數量和嚴重度較低；自寫測試多 ~70%。
- 結論 → v7：preset 預設 **flash-high**（auditor 也 high）。Claude token 不變（只讀報告），代價是時間和 agy 額度，主對話等待不花 Claude token。
- 注意：low 與 high 的 agy audit 都回 NO_ISSUES → agy 自我審查抓不到這類 bug；重要模組仍值得一次 Claude/Sonnet 盲審抽查。
