# claude-antigravity-cowork

讓 **Claude Code** 把實作工作交給 **Antigravity（`agy` CLI，Gemini）**，省下 Claude 額度，又不因為事後審查把省下的吃回去。
這是一套可直接安裝的 Claude Code skill，加上完整的實驗數據與重現工具。

> **English TL;DR** — A Claude Code skill + scripts for delegating implementation to Google Antigravity's `agy` CLI.
> Claude writes a short spec and a few golden tests; `delegate.py` runs Gemini with an automatic test gate, retries and
> self-audit; Claude reads only a ~10-line report. Measured on hidden test suites: backend batches cost **62–68%** of
> Claude-only tokens at equal quality, naive outsourcing cost **188%**. With Gemini 4 (2026-11-19) the default worker is
> the agy **Orchestrator** (Argon/Neon plans, Hydrogen executes): blind code review 8–8.5/10 vs Claude-only 5.5, at ~2–4%
> of the Gemini 5h quota per batch. A Neon-built small UI tied Claude in a blind visual review.

---

## 最新：Gemini 4（2026-11-19）

| 項目 | 3.8 Flash high（v7） | Gemini 4（v9） |
|---|---|---|
| 後端程式碼盲審（T3–T5） | 6 | **Orchestrator (Argon) 8.5**、Neon 9、Hydrogen 7（Claude 自寫 5.5） |
| 每批耗時 | 10–20 分 | Orchestrator ~9 分、Hydrogen ~5 分 |
| 每批 Gemini 5h 額度 | 14–17% | Orchestrator 2–4%、Hydrogen ~5% |
| 小型 UI 視覺盲評 | 4.5–5.6（墊底） | **Neon 8.5**，與 Claude 8 打平 |
| 自我稽核抓已知 bug | 0/2 | Hydrogen 1/2（其他仍 0/2） |

v9 預設：後端用 Orchestrator（依額度挑 Argon / Neon 當規劃者，Hydrogen high 執行），沒額度時退回 Hydrogen high 平行；稽核用 Hydrogen high；小 UI 可試用 Neon（`designer`）先做、Claude 只看截圖。
詳見 [RESULTS.md §10](docs/RESULTS.md#10-gemini-42026-11-19)，截圖在 [`data/screenshots/compare_gemini4/`](data/screenshots/compare_gemini4/)。

![F1 小型前端：五組並排（桌面亮色）](data/screenshots/compare_gemini4/1_desktop_light.png)

## 結果一覽（Claude 端用量，3.8 Flash 時期量測）

| 場景 | Claude 用量（自己寫 = 100%） | 品質 | 建議 |
|---|---|---|---|
| 後端批次（儲存層、parser、CLI、API、匯入匯出…，≳300 行） | **62–68%** | hidden tests 全過 | ✅ 委派 |
| 大型前端（多頁 SPA），用「設計系統分工」 | **91%** | 功能 7/7，視覺盲評持平 | ✅ 分工 |
| 無腦外包（丟給 Gemini，Claude 讀完整 diff 審查） | 188% | 相同 | ❌ |
| 小型前端（≲300 行） | 134–160% | 3.8 Flash 獨做視覺墊底；Gemini 4 Neon 與 Claude 打平 | Claude 自己寫，或試 Neon＋只看截圖 |
| 小改動（<40 行）、需要設計或安全判斷、無法自動測試 | — | — | ❌ Claude 自己寫 |

- Claude 端百分比是在 Sonnet 子代理、Flash low 下量到的；v9 的 Claude 流程相同，預期不變，但未重新量測。
- Gemini 端代價（v9）：每批約 **2–5% 的 5 小時額度**，5–10 分鐘。
- 數據細節見 [docs/RESULTS.md](docs/RESULTS.md)，量測方法見 [docs/METHODOLOGY.md](docs/METHODOLOGY.md)。

## 為什麼這樣能省

Claude 的花費主要是 **回合數 × context 大小**，而不是「誰寫程式」：
1. 每次工具呼叫都重讀整個 context；Claude 自己寫的程式碼之後每一回合都會被重讀。
2. 所以 Claude 只寫「合約」（短規格 + 2–4 個 golden asserts），實作、完整測試、重試、自我稽核全由程式和 Gemini 完成，Claude 只讀精簡報告。
3. 每次 `agy` 呼叫有 ~25k token 固定開銷 → 一定要批次；批次太小（後端 <~300 行）就不划算。Orchestrator 把整批放進同一個 session，進一步省掉每個規格各自的開銷。

## 快速開始

需求：Claude Code、已登入的 `agy` CLI、Python 3.10+、git。

```bash
git clone https://github.com/jasonxp516/claude-antigravity-cowork
cp -r claude-antigravity-cowork/skill/agy-cowork ~/.claude/skills/
cat claude-antigravity-cowork/skill/CLAUDE.md.example >> ~/.claude/CLAUDE.md
python3 ~/.claude/skills/agy-cowork/tools/agy_quota.py      # 確認 agy 可用並查看額度（不耗額度）
```

裝好後不用特別下指令：Claude 遇到實作工作時會先跑分工判斷，值得委派才委派。手動使用方式見 [docs/USAGE.md](docs/USAGE.md)。

## 運作流程

```
Claude                                delegate.py（不耗 Claude token）              Gemini Flash
──────                                ────────────────────────────                  ────────────
1 plan_split.py：要不要委派？
2 寫 spec + golden tests
3 背景執行 delegate.py，結束回合 ──►  檢查額度 → 每個獨立 spec 一個 git worktree ──►  實作＋寫完整測試
                                      跑驗收指令；失敗就把錯誤回餵重試         ◄──
                                      還原被改的受保護測試；另開 session 稽核 ──►  稽核 / 修正
4 讀 ~10 行報告                 ◄──   合併、輸出報告（通過與否、檔案、介面、行為統計）
```

後端 preset 預設由 Orchestrator 在單一 session 執行整批（不開 worktree）；加 `--fast` 改為 Hydrogen high 平行 worktree（約 5 分鐘，適合子代理）。
大型前端採 **設計系統分工**：Claude 寫 `design.css`、頁面外殼和一個完整參考頁，Gemini 依樣做其餘頁面和全部 JS，最後 Claude 截圖檢查。

## 文件

| 文件 | 內容 |
|---|---|
| [docs/USAGE.md](docs/USAGE.md) | 指令、參數、preset、前端分工步驟、模型選擇、額度與退出碼 |
| [docs/RESULTS.md](docs/RESULTS.md) | 全部實驗結果，依主題整理 |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | 怎麼量、怎麼驗證、如何重現 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | skill v1–v9 每版改了什麼、為什麼 |
| [docs/lab-notebook.md](docs/lab-notebook.md) | 原始實驗筆記（依時間順序，未整理） |

## 限制

- 每個對照組只跑 1–2 次，屬小樣本；主要結論（後端 62–68%）在兩組不同任務上重現。
- Gemini 4 的比較每組只跑一次、盲審只評一次（評審變異約 ±0.7）。
- 模型由設定檔依「家族名稱」動態挑選，不寫死 id。新家族（如 Carbon）只要加進 `model_policy.json` 的偏好清單；建議用 `experiment/` 的工具重跑比較。
- 自我稽核仍會漏 bug（Hydrogen 抓到 1/2，其他 0/2）；重要模組仍值得讓 Claude 抽查一次。
- 在 Claude **子代理**中等超過 5 分鐘會多付一次快取失效（~30k）；子代理請加 `--fast`，或從主對話委派。

## Repo 結構

```
skill/agy-cowork/         可安裝的 skill：SKILL.md、frontend_rules.md、tools/、config/
skill/CLAUDE.md.example   全域規則範例（讓 Claude 自動判斷分工）
docs/                     使用說明、結果、方法、版本紀錄
experiment/               重現用：測試專案、12 個任務與 hidden tests、量測工具、各版 skill
data/                     原始數據：每次委派紀錄、額度紀錄、對照組數據、盲評對照表、截圖
```

授權：MIT
