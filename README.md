# Claude Code × Antigravity 協作：實測哪些工作該交給 Gemini、能省多少

> **TL;DR (English)** — A measured recipe for letting Claude Code delegate implementation work to Google Antigravity's
> `agy` CLI (Gemini Flash) without paying it back in review tokens. Claude writes a short spec + a few golden tests,
> a script (`delegate.py`) runs Gemini in git worktrees with an automatic test gate / retry / self-audit loop, and Claude
> reads only a ~10-line report. On backend batches this cost **62–68% of Claude-only tokens with identical hidden-test
> quality**; naive "just ask Gemini and review the diff" cost **188%**. Frontend visual design should stay with Claude.
> Everything here — skill, scripts, task suites, hidden tests, raw metrics, screenshots — is the actual experiment.

這個 repo 是一次完整實驗的成果：讓 Claude Code 把「規格清楚、可用測試驗收」的實作工作外包給 Antigravity（`agy` CLI，Gemini 3.8 Flash），
目標是**省 Claude 額度，又不因為事後審查把省下的 token 吃回去**。所有結論都有量測數據，原始資料和重現工具都在這裡。

---

## 核心結論

| 場景 | Claude 用量（vs Claude 自己寫） | 品質 | 做法 |
|---|---|---|---|
| 無腦外包（丟給 Gemini，Claude 讀完整 diff 審查） | **188%** ❌ | 相同 | 不要這樣做 |
| 後端批次（儲存層、parser、CLI、API、bug fix、匯入匯出…） | **62–68%** ✅ | hidden tests 全過 | `delegate.py --preset backend` |
| 小型前端（≲300 行） | 134–160% ❌ | Gemini 視覺盲評墊底（5.6/10） | Claude 自己寫＋設計 checklist |
| 大型前端（多 view SPA） | **91%** ✅ | 7/7、盲評與 Claude 全包持平 | 設計系統分工（見下） |
| 小改動（<40 行）/ 需要判斷 / 無法自動測試 | — | — | Claude 自己做 |

**省 token 的關鍵不是「誰寫程式」，而是 Claude 的「回合數 × context 大小」：**
- 每次工具呼叫都會重讀整個 context；Claude 自己寫的程式碼會在之後每一回合被重讀（所以節省乘數約 12×，而非 output 價格的 5×）。
- 每次 `agy` 呼叫有 ~25k token 固定開銷，一定要**批次**。
- 等待超過 prompt cache TTL（subagent 5 分鐘）會讓整個 context 重寫；主對話是 1 小時，背景執行後**結束回合、不要輪詢**即可。

**Gemini 端代價**（3.8 Flash high）：每批 4–6 個任務約 **14% 的 5 小時額度、4% 的週額度**，10–20 分鐘。

---

## 運作方式

```
Claude（規格擁有者）                          delegate.py（零 Claude token）                Gemini Flash（agy）
───────────────────                          ──────────────────────────────                ───────────────────
1. plan_split.py 判定要不要委派   ──►  額度檢查（/usage，零成本）
2. 寫 spec.md + 2–4 個 golden asserts       每個獨立 spec 開一個 git worktree，平行  ──►  實作 + 自己寫完整測試
3. 背景執行 delegate.py，結束回合           跑驗收指令；失敗 → 把錯誤回餵重試（最多 2 次）◄──
                                            還原被改動的受保護測試（防「改考卷」）
                                            另開 session 做 spec 對照稽核 → 有問題回修一次  ──►  auditor
4. 讀 ~10 行報告：ACCEPTED / 檔案 /  ◄──    合併 worktree、輸出精簡報告＋行為軌跡統計
   公開介面 / audit / worker trace
```

報告範例（真實輸出節錄）：
```
[SMAR] ACCEPTED=True attempts=2 models=['gemini-3.8-flash-low', 'gemini-3.8-flash-low']
agy tokens=243437 quota_used={'gemini-weekly': 0.0028, 'gemini-5h': 0.0098}
files=['app.py', 'schedule.py', 'scraper.py', 'storage.py', 'validation.py', 'tests/…']
public=['fetch_attendance', 'parse_attendance_html', 'validate_config', …]
worker trace: wall=246s calls=40 tests=8 polls=0 waste=0%
audit: NO_ISSUES
```

### 前端的「設計系統分工」
1. Claude 寫 `design.css`（色彩 token、明暗模式、間距/字級、所有元件 class、狀態、RWD）+ `index.html` 外殼 + **一個完整的參考頁面**。
2. Claude 寫關鍵流程的 Playwright golden tests。
3. Gemini 依 class 做其餘頁面的 markup 與全部 JS（`--preset frontend-js` 會附上 [`frontend_rules.md`](skill/agy-cowork/frontend_rules.md)：AbortController、`res.ok` 先檢查、焦點還原、`aria-live`…，這些規則來自 Opus 審查 Gemini 前端程式碼的共通問題）。
4. Claude 截圖（亮/暗/手機）一次，自己修 CSS。

---

## 安裝與使用

需求：Claude Code、已登入的 Antigravity `agy` CLI、Python 3.10+、git。

```bash
git clone https://github.com/jasonxp516/claude-antigravity-cowork
cp -r claude-antigravity-cowork/skill/agy-cowork ~/.claude/skills/
cat claude-antigravity-cowork/skill/CLAUDE.md.example >> ~/.claude/CLAUDE.md   # 讓 Claude 每次自動先判斷分工
python3 ~/.claude/skills/agy-cowork/tools/agy_quota.py                          # 確認 agy 可用、看額度（不耗額度）
```

之後在任何專案中，Claude 會先跑分工判斷：
```bash
python3 ~/.claude/skills/agy-cowork/tools/plan_split.py \
  '[{"name":"parser","kind":"backend","lines":120,"testable":true},
    {"name":"tests backfill","kind":"tests","lines":220,"testable":true},
    {"name":"auth check","kind":"bugfix","lines":25,"judgment":true}]'
```
```
AGY    parser                       backend            120 lines  offloadable ≈ 20k IET
AGY    tests backfill               tests              220 lines  offloadable ≈ 48k IET
CLAUDE auth check                   bugfix              25 lines  needs design/security judgment
BATCH: delegate 2 item(s) in ONE delegate.py call (--parallel for independent ones); expected Claude saving ≈ 33k IET
```
再委派：
```bash
python3 ~/.claude/skills/agy-cowork/tools/delegate.py --preset backend --workdir . \
  --spec specs/a.md --spec specs/b.md --accept "python -m pytest -q tests" --tag mybatch > .delegate_report.txt 2>&1
```
退出碼：`0` 通過、`1` 未通過、`3` agy 額度用完（換帳號）、`4` agy 錯誤。

**模型不寫死**：`config/model_policy.json` 以「角色 → 模型家族 + effort」描述，執行時讀 `agy models` 與 `/usage` 挑最新可用版本；
planner 角色（Argon/Carbon/Pro）額度不足時自動降級。新模型（例如 4 Flash）上線會自動被選上。

### 分工模型（`plan_split.py`）
```
Claude 節省（IET）≈ 12 × 被卸載的 output tokens − 35k（每批固定成本：讀 skill、寫 golden tests、讀報告、多出的回合）
被卸載的 output ≈ 行數 × 每行 token（後端 20、前端 34）× 可卸載比例（後端 0.7、前端邏輯 0.25、視覺 0）
```
驗算：後端 470 行 預測 +44k / 實測 +37–43k；大型 UI 分工 +13k / +16k；小 UI 預測為負 / 實測 −55k。
實用門檻：**同一批可卸載的後端程式 ≳ 300 行才值得委派**。

---

## 怎麼驗證的

- **測試專案**：自建 Python 任務管理專案（`experiment/testbed`），12 個任務規格（`experiment/tasks/T1–T10, F1, F2`），
  每個任務都有 **Gemini 和 Claude 都看不到的 hidden tests**（共 67 個後端 + 12 個 Playwright）用來量品質。
- **對照組**：每種做法由一個 **Sonnet subagent** 在隔離的工作目錄執行同一批任務（A = Claude 自己寫、B = 無腦外包、C1–C7 = 各版 skill、
  FA/FG/FH = 小前端、LA/LH/LS = 大前端、H6/H7 = Flash effort A/B）。
- **Claude 成本**：從 subagent transcript 精確計算，單位 IET（input-equivalent tokens）= input + 1.25×cache_write + 0.1×cache_read + 5×output
  （依 API 相對價格加權；`experiment/tools/claude_usage.py`）。
- **Gemini 成本**：每次呼叫前後讀 `agy /usage` 的剩餘比例（零成本），加上每次呼叫回傳的 token。
- **前端品質**：Playwright 截圖（桌面/手機/明暗），由 **Opus 盲評**（不知道哪張是誰做的；同一組評兩次以估計評審變異 ±0.7）。
- **程式品質（hidden tests 打平時）**：由 Sonnet **盲審**兩份實作，要求列出可重現的 bug。
- **Gemini 行為**：從 agy 本機 SQLite 軌跡（`~/.gemini/antigravity-cli/conversations/*.db`）統計工具呼叫（`agy_trace.py`），
  發現前端任務有 51–58% 的呼叫在輪詢背景測試 → 加入「同步執行」規則後降到 0%。
- **真實專案驗證**：在一個真實 Flask 專案上走完整流程（Gemini 後端重構＋28 個測試、Claude 同時做前端），結果直接合併成 PR。

### 滾動修正紀錄（每版 Claude 成本 vs 自己寫）
| 版本 | 改了什麼（為什麼） | Claude 成本 |
|---|---|---|
| v1 | Claude 寫完整驗收測試 → output 跟自己寫一樣多 | 179% |
| v2 | 只寫 2–4 個 golden asserts，完整測試交給 Gemini；加 agy 自我稽核 | 134% |
| v3 | 發現 agy 跑 15 分鐘讓 subagent cache 過期 → 獨立 spec 平行 worktree、背景不輪詢 | 113% / 94% |
| v4 | flash-low worker 讓總時長 <5 分鐘，cache 不再過期 | **68% / 62%** |
| v5 | 前端：Opus 審查 → `frontend_rules.md` + 設計 checklist | — |
| v6 | `--preset`、`plan_split.py`、交接自我檢查、spec 衝突規則、行為軌跡 | 62–70% |
| v7 | Flash effort A/B：high 盲審 8.3 vs 6.5、8 vs 7（low 有 tests 抓不到的真 bug）→ 預設 high | Claude 不變；agy 額度 ~5× |
| (v8) | 子代理快取保溫：實測多花 22%，**未採用** | 172.7k vs 142.1k |

### Flash low vs high（v7 的依據）
| 批次 | effort | hidden | 耗時 | agy 5h 額度 | 盲審 |
|---|---|---|---|---|---|
| T1–T6 | low | 50/50 | ~5 分 | 2.9% | 6.5 |
| T1–T6 | high | 50/50 | ~20 分 | 15.2% | **8.3** |
| T7–T10 | low | 17/17 | ~3.5 分 | 2.9% | 7 |
| T7–T10 | high | 17/17 | ~13.5 分 | 13.6% | **8** |

> 在 subagent 裡（5 分鐘 cache）長等待會花 Claude token，那是 v4 選 low 的原因；在主對話（1 小時 cache）等待幾乎免費，所以 v7 改回 high。

### 子代理快取保溫（keep-alive）— 測過，不採用
子代理的快取只有 5 分鐘，等 high 跑 20 分鐘必定過期一次。試過每 ≤4.5 分鐘喚醒子代理一次（`experiment/tools/wait_delegate.py`）讓快取保溫：

| 等待方式 | Claude IET | 回合 | hidden |
|---|---|---|---|
| 每 ≤4.5 分鐘喚醒 | 172.7k | 20 | 17/17 |
| 閒置等通知（失效一次） | **142.1k** | 11 | 17/17 |

快取失效只會發生**一次**（且系統提示仍命中，代價 ≈ 31k），保溫卻是每 4 分鐘付一次（≈ 5–6k），等待一長就反超；
加上 harness 會把超過 ~3 分鐘的指令自動轉背景，喚醒節奏不穩定。→ 子代理盡早委派、或直接從主對話（1 小時快取）委派即可。

完整數據、各輪表格、決策紀錄實驗、限制說明：[`docs/REPORT.md`](docs/REPORT.md)。

---

## 已知限制（誠實說明）
- 每個對照組只跑 1–2 次（小樣本）；v4 的節省在兩組不同任務上重現（62%、68%）。
- 任務是中小型；真實大型開發中 Claude 的 context 更大，理論上委派節省更多，但未直接量測。
- agy 自我稽核在 low/high 都回報 NO_ISSUES，卻有審查者找得到的 bug → **重要模組仍值得一次 Claude 盲審抽查**。
- Gemini 的思考內容不會存在本機，只能觀察工具呼叫；讓它寫「決策紀錄」實測不可靠（事前計畫、內容不實），不建議例行使用。
- 只測過 Gemini 3.8 Flash（Argon 額度不足）；新模型需重跑 A/B（工具都在 `experiment/`）。

## Repo 結構
```
skill/agy-cowork/        可直接安裝的 Claude Code skill（SKILL.md、frontend_rules.md、tools/、config/）
skill/CLAUDE.md.example  全域規則範例
experiment/tools/        量測工具：claude_usage.py、eval_arm.py、report.py、agy_trace.py、shoot_*.py、agy_raw.py…
experiment/tasks/        12 個任務規格 + hidden tests
experiment/testbed/      測試專案的起始狀態
experiment/skill_versions/  v1–v7 的 SKILL.md 與 delegate.py
data/                    原始數據：runs.jsonl（每次委派）、quota.jsonl、arms*.json、盲評對照表、截圖
docs/REPORT.md           完整實驗報告
```

## 重現
```bash
cd experiment && python3 -m venv .venv && .venv/bin/pip install pytest playwright && .venv/bin/playwright install chromium
# 建一個 arm：從 testbed 複製、放入 tasks/Tn/spec.md 與 golden tests，交給 Claude（或 subagent）依 SKILL.md 執行
.venv/bin/python tools/eval_arm.py runs/<arm> --tasks=T1,T2   # hidden tests 計分
.venv/bin/python tools/claude_usage.py <transcript.jsonl>      # Claude 端 IET
```

授權：MIT
